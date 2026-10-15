"""Drive the real RIME engine (librime) from Python, for integration tests.

This loads librime's shared library with ctypes, deploys the schema into a
temporary folder, and lets a test press keys and read back the candidates
and committed text, the same way 倉輸入法 or 鼠鬚管 talk to the engine.

Only the handful of API calls the tests need are wrapped.
"""

from __future__ import annotations

import ctypes as C
import os
import platform
from dataclasses import dataclass
from pathlib import Path

Bool = C.c_int
SessionId = C.c_size_t  # uintptr_t

# Field order of struct rime_api_t in rime_api.h (librime 1.17.0).
_API_FIELDS = (
    "setup set_notification_handler initialize finalize start_maintenance "
    "is_maintenance_mode join_maintenance_thread deployer_initialize prebuild "
    "deploy deploy_schema deploy_config_file sync_user_data create_session "
    "find_session destroy_session cleanup_stale_sessions cleanup_all_sessions "
    "process_key commit_composition clear_composition get_commit free_commit "
    "get_context free_context get_status free_status set_option get_option "
    "set_property get_property get_schema_list free_schema_list "
    "get_current_schema select_schema schema_open config_open config_close "
    "config_get_bool config_get_int config_get_double config_get_string "
    "config_get_cstring config_update_signature config_begin_map config_next "
    "config_end simulate_key_sequence register_module find_module run_task "
    "get_shared_data_dir get_user_data_dir get_sync_dir get_user_id "
    "get_user_data_sync_dir config_init config_load_string config_set_bool "
    "config_set_int config_set_double config_set_string config_get_item "
    "config_set_item config_clear config_create_list config_create_map "
    "config_list_size config_begin_list get_input get_caret_pos "
    "select_candidate get_version set_caret_pos "
    "select_candidate_on_current_page candidate_list_begin candidate_list_next "
    "candidate_list_end"
).split()


class _Api(C.Structure):
    _fields_ = [("data_size", C.c_int)] + [(name, C.c_void_p) for name in _API_FIELDS]


class _Traits(C.Structure):
    _fields_ = [
        ("data_size", C.c_int),
        ("shared_data_dir", C.c_char_p),
        ("user_data_dir", C.c_char_p),
        ("distribution_name", C.c_char_p),
        ("distribution_code_name", C.c_char_p),
        ("distribution_version", C.c_char_p),
        ("app_name", C.c_char_p),
        ("modules", C.c_void_p),
        ("min_log_level", C.c_int),
        ("log_dir", C.c_char_p),
        ("prebuilt_data_dir", C.c_char_p),
        ("staging_dir", C.c_char_p),
    ]


class _Commit(C.Structure):
    _fields_ = [("data_size", C.c_int), ("text", C.c_char_p)]


class _Candidate(C.Structure):
    _fields_ = [("text", C.c_char_p), ("comment", C.c_char_p), ("reserved", C.c_void_p)]


class _CandidateIter(C.Structure):
    _fields_ = [("ptr", C.c_void_p), ("index", C.c_int), ("candidate", _Candidate)]


class _SchemaItem(C.Structure):
    _fields_ = [("schema_id", C.c_char_p), ("name", C.c_char_p), ("reserved", C.c_void_p)]


class _SchemaList(C.Structure):
    _fields_ = [("size", C.c_size_t), ("list", C.POINTER(_SchemaItem))]


def _init_struct(s: C.Structure) -> None:
    # RIME_STRUCT_INIT: data_size = sizeof(Type) - sizeof(data_size)
    s.data_size = C.sizeof(s) - C.sizeof(C.c_int)


# X11 keysyms for the non-printable keys the tests press.
KEYSYMS = {
    "space": 0x20,
    "Return": 0xFF0D,
    "BackSpace": 0xFF08,
    "Escape": 0xFF1B,
    "Page_Down": 0xFF56,
    "Page_Up": 0xFF55,
}


@dataclass
class Candidate:
    text: str
    comment: str


def find_library(dist: Path) -> Path:
    system = platform.system()
    if system == "Windows":
        return dist / "lib" / "rime.dll"
    if system == "Darwin":
        return dist / "lib" / "librime.1.dylib"
    return dist / "lib" / "librime.so.1"


class Rime:
    """One RIME engine per process (librime keeps global state)."""

    def __init__(self, dist: Path) -> None:
        lib_path = find_library(dist)
        if not lib_path.exists():
            raise FileNotFoundError(lib_path)
        if hasattr(os, "add_dll_directory"):
            self._dll_dir = os.add_dll_directory(str(lib_path.parent))
        self._lib = C.CDLL(str(lib_path))
        self._lib.rime_get_api.restype = C.POINTER(_Api)
        self._api = self._lib.rime_get_api().contents
        f = self._fn
        self.setup = f("setup", None, C.POINTER(_Traits))
        self.initialize = f("initialize", None, C.POINTER(_Traits))
        self.finalize = f("finalize", None)
        self.start_maintenance = f("start_maintenance", Bool, Bool)
        self.join_maintenance_thread = f("join_maintenance_thread", None)
        self.create_session = f("create_session", SessionId)
        self.destroy_session = f("destroy_session", Bool, SessionId)
        self.process_key = f("process_key", Bool, SessionId, C.c_int, C.c_int)
        self.clear_composition = f("clear_composition", None, SessionId)
        self.get_commit = f("get_commit", Bool, SessionId, C.POINTER(_Commit))
        self.free_commit = f("free_commit", Bool, C.POINTER(_Commit))
        self.select_schema = f("select_schema", Bool, SessionId, C.c_char_p)
        self.get_schema_list = f("get_schema_list", Bool, C.POINTER(_SchemaList))
        self.free_schema_list = f("free_schema_list", None, C.POINTER(_SchemaList))
        self.get_input = f("get_input", C.c_char_p, SessionId)
        self.select_candidate = f("select_candidate", Bool, SessionId, C.c_size_t)
        self.get_version = f("get_version", C.c_char_p)
        self.candidate_list_begin = f("candidate_list_begin", Bool, SessionId, C.POINTER(_CandidateIter))
        self.candidate_list_next = f("candidate_list_next", Bool, C.POINTER(_CandidateIter))
        self.candidate_list_end = f("candidate_list_end", None, C.POINTER(_CandidateIter))
        self._traits: _Traits | None = None
        self._keep: list[bytes] = []

    def _fn(self, name: str, restype, *argtypes):
        addr = getattr(self._api, name)
        if not addr:
            raise RuntimeError(f"librime does not provide {name}")
        return C.CFUNCTYPE(restype, *argtypes)(addr)

    def _b(self, value: str) -> bytes:
        data = value.encode("utf-8")
        self._keep.append(data)  # keep alive while librime holds the pointer
        return data

    def start(self, shared_dir: Path, user_dir: Path, log_dir: Path) -> None:
        """Set up, deploy (compile schemas and dictionaries) and wait."""
        t = _Traits()
        _init_struct(t)
        t.shared_data_dir = self._b(str(shared_dir))
        t.user_data_dir = self._b(str(user_dir))
        t.distribution_name = self._b("rime-sanjiao tests")
        t.distribution_code_name = self._b("rime-sanjiao-tests")
        t.distribution_version = self._b("0")
        t.app_name = self._b("rime.sanjiao_tests")
        t.min_log_level = 2  # errors only
        t.log_dir = self._b(str(log_dir))
        self._traits = t
        self.setup(C.byref(t))
        self.initialize(C.byref(t))
        if self.start_maintenance(1):
            self.join_maintenance_thread()

    def schema_ids(self) -> list[str]:
        sl = _SchemaList()
        if not self.get_schema_list(C.byref(sl)):
            return []
        try:
            return [sl.list[i].schema_id.decode() for i in range(sl.size)]
        finally:
            self.free_schema_list(C.byref(sl))

    def session(self, schema_id: str) -> "Session":
        sid = self.create_session()
        if not sid:
            raise RuntimeError("create_session failed")
        if not self.select_schema(sid, schema_id.encode()):
            raise RuntimeError(f"select_schema({schema_id}) failed")
        return Session(self, sid)


class Session:
    def __init__(self, rime: Rime, sid: int) -> None:
        self.rime = rime
        self.sid = sid
        self.committed = ""

    def close(self) -> None:
        self.rime.destroy_session(self.sid)

    def _collect_commit(self) -> None:
        c = _Commit()
        _init_struct(c)
        if self.rime.get_commit(self.sid, C.byref(c)):
            self.committed += c.text.decode("utf-8")
            self.rime.free_commit(C.byref(c))

    def press(self, key: str) -> bool:
        """Press one key: a single ASCII character, or a KEYSYMS name."""
        code = KEYSYMS[key] if key in KEYSYMS else ord(key)
        handled = bool(self.rime.process_key(self.sid, code, 0))
        self._collect_commit()
        return handled

    def type(self, keys: str) -> None:
        """Type ASCII characters one by one; {name} presses a named key."""
        i = 0
        while i < len(keys):
            if keys[i] == "{":
                end = keys.index("}", i)
                self.press(keys[i + 1 : end])
                i = end + 1
            else:
                self.press(keys[i])
                i += 1

    def pick(self, index: int) -> None:
        """Tap the candidate at `index` (0-based), like touching it on screen."""
        if not self.rime.select_candidate(self.sid, index):
            raise IndexError(index)
        self._collect_commit()

    @property
    def input(self) -> str:
        raw = self.rime.get_input(self.sid)
        return raw.decode("utf-8") if raw else ""

    def candidates(self, limit: int = 50) -> list[Candidate]:
        it = _CandidateIter()
        out: list[Candidate] = []
        if not self.rime.candidate_list_begin(self.sid, C.byref(it)):
            return out
        try:
            while len(out) < limit and self.rime.candidate_list_next(C.byref(it)):
                cand = it.candidate
                out.append(
                    Candidate(
                        text=cand.text.decode("utf-8") if cand.text else "",
                        comment=cand.comment.decode("utf-8") if cand.comment else "",
                    )
                )
        finally:
            self.rime.candidate_list_end(C.byref(it))
        return out

    def texts(self, limit: int = 50) -> list[str]:
        return [c.text for c in self.candidates(limit)]

    def reset(self) -> None:
        self.rime.clear_composition(self.sid)
        self.committed = ""
