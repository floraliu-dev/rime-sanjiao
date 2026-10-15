"""End-to-end behaviour in the real RIME engine (librime).

The release zip is unpacked into a fresh RIME user folder, deployed, and
driven key by key, the same way 倉輸入法 drives the engine on an iPhone.

Needs librime: run `python -m tools.fetch_librime` once (Windows/macOS), or
set RIME_DIST to a librime "dist" folder. Skipped when librime is missing.
"""

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path

from tests import ROOT

import build
from tools.fetch_librime import dist_dir
from tools.rime_harness import Rime, find_library

RIME_DIST = Path(os.environ.get("RIME_DIST") or dist_dir())
HAVE_RIME = find_library(RIME_DIST).exists()

# A stand-in for the frontend's shared data: a default.yaml with one other
# schema already in schema_list, to prove our patch appends instead of
# replacing the user's list.
DEFAULT_YAML = """\
config_version: "test"
schema_list:
  - schema: other
menu:
  page_size: 5
"""
OTHER_SCHEMA = """\
schema:
  schema_id: other
  name: Other
  version: "1"
engine:
  processors: [express_editor]
  segmentors: [fallback_segmentor]
  translators: [echo_translator]
"""


def make_rime_dirs(base: Path, zip_suffix: str, extra_user_files: dict[str, str] | None = None):
    shared, user, logs = base / "shared", base / "user", base / "logs"
    for d in (shared, user, logs):
        d.mkdir()
    (shared / "default.yaml").write_text(DEFAULT_YAML, encoding="utf-8")
    (shared / "other.schema.yaml").write_text(OTHER_SCHEMA, encoding="utf-8")
    zips = build.package(build.read_version(), dist=base / "dist")
    (zip_path,) = [p for p in zips if p.name.endswith(zip_suffix)]
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(user)
    for name, content in (extra_user_files or {}).items():
        (user / name).write_text(content, encoding="utf-8")
    return shared, user, logs


def error_logs(logs: Path) -> str:
    return "".join(p.read_text(errors="replace") for p in logs.glob("*.ERROR.*"))


@unittest.skipUnless(HAVE_RIME, f"librime not found in {RIME_DIST}; run `python -m tools.fetch_librime`")
class Behaviour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        shared, user, cls.logs = make_rime_dirs(Path(cls.tmp.name), "-hamster.zip")
        cls.rime = Rime(RIME_DIST)
        cls.rime.start(shared, user, cls.logs)
        cls.s = cls.rime.session("sanjiao")

    @classmethod
    def tearDownClass(cls):
        cls.s.close()
        cls.rime.finalize()
        cls.tmp.cleanup()

    def setUp(self):
        self.s.reset()

    def typed(self, keys):
        self.s.reset()
        self.s.type(keys)
        return self.s

    # -- deployment ----------------------------------------------------------

    def test_engine_version(self):
        self.assertEqual(self.rime.get_version().decode(), "1.17.0")

    def test_schema_appended_to_existing_list(self):
        self.assertEqual(self.rime.schema_ids(), ["other", "sanjiao"])

    def test_no_errors_logged(self):
        self.assertEqual(error_logs(self.logs), "")

    # -- looking up characters -------------------------------------------------

    def test_full_code(self):
        self.assertEqual(self.typed("101010").texts(), ["三"])
        self.assertEqual(self.typed("305354").texts(), ["我"])

    def test_leading_zeros(self):
        self.assertEqual(self.typed("000010").texts()[0], "═")

    def test_ideographic_space(self):
        self.assertEqual(self.typed("000000").texts()[0], "　")

    def test_trailing_zeros_may_be_omitted(self):
        # 101000 二, typed as 10100 / 1010 / 101; 100000 一, typed as 1.
        for keys in ("10100", "1010", "101"):
            with self.subTest(keys=keys):
                self.assertEqual(self.typed(keys).texts()[0], "二")
        self.assertEqual(self.typed("1").texts()[0], "一")
        self.assertEqual(self.typed("10101").texts()[0], "三")  # 101010

    def test_completion_while_typing(self):
        cands = self.typed("101").candidates(20)
        self.assertEqual(cands[0].text, "二")  # exact match first, no comment
        self.assertEqual(cands[0].comment, "")
        completions = {c.text: c.comment for c in cands[1:]}
        self.assertEqual(completions.get("三"), "~010")  # remaining digits shown

    def test_candidate_order(self):
        self.assertEqual(self.typed("331120").texts(), ["汗", "汙", "涆", "滒", "泟", "𣵼"])
        self.assertEqual(self.typed("018660").texts()[0], "高")

    def test_fixed_order_does_not_learn(self):
        self.typed("331120")
        self.s.pick(3)
        self.assertEqual(self.s.committed, "滒")
        self.assertEqual(self.typed("331120").texts()[0], "汗")

    def test_invalid_code_has_no_candidates(self):
        self.assertEqual(self.typed("999999").texts(), [])

    # -- committing ------------------------------------------------------------

    def test_space_commits_first_candidate(self):
        s = self.typed("101010{space}")
        self.assertEqual((s.committed, s.input), ("三", ""))
        self.assertEqual(self.typed("10{space}").committed, "一")

    def test_tap_candidate(self):
        self.typed("331120")
        self.s.pick(1)
        self.assertEqual((self.s.committed, self.s.input), ("汙", ""))

    def test_continuous_typing_commits_at_seventh_digit(self):
        s = self.typed("1010103")
        self.assertEqual((s.committed, s.input), ("三", "3"))
        s = self.typed("101010305354{space}")
        self.assertEqual(s.committed, "三我")

    def test_space_with_invalid_code_keeps_it(self):
        s = self.typed("999999{space}")
        self.assertEqual((s.committed, s.input), ("", "999999"))
        s.type("{BackSpace}")
        self.assertEqual(s.input, "99999")

    def test_space_with_nothing_typed_is_passed_to_the_app(self):
        # Not handled by RIME, so the app inserts a normal space.
        self.s.reset()
        self.assertFalse(self.s.press("space"))

    def test_enter_commits_digits(self):
        s = self.typed("2026{Return}")
        self.assertEqual((s.committed, s.input), ("2026", ""))

    def test_escape_and_backspace(self):
        s = self.typed("101010{Escape}")
        self.assertEqual((s.committed, s.input), ("", ""))
        s = self.typed("1{BackSpace}")
        self.assertEqual(s.input, "")

    # -- punctuation -------------------------------------------------------------

    def test_punctuation_alone(self):
        expected = {",": "，", ".": "。", "?": "？", "!": "！", ":": "：", ";": "；",
                    "\\": "、", "[": "「", "]": "」"}
        for key, out in expected.items():
            with self.subTest(key=key):
                self.assertEqual(self.typed(key).committed, out)

    def test_punctuation_commits_pending_character(self):
        self.assertEqual(self.typed("101010,").committed, "三，")
        self.assertEqual(self.typed("101010\\").committed, "三、")


@unittest.skipUnless(HAVE_RIME, f"librime not found in {RIME_DIST}")
class OtherPackages(unittest.TestCase):
    """Each configuration runs in its own process: librime is a singleton."""

    def run_scenario(self, zip_suffix, extra_user_files, body):
        with tempfile.TemporaryDirectory() as tmp:
            shared, user, logs = make_rime_dirs(Path(tmp), zip_suffix, extra_user_files)
            script = textwrap.dedent(f"""\
                import sys
                sys.path.insert(0, {str(ROOT)!r})
                from pathlib import Path
                from tools.rime_harness import Rime
                rime = Rime(Path({str(RIME_DIST)!r}))
                rime.start(Path({str(shared)!r}), Path({str(user)!r}), Path({str(logs)!r}))
                s = rime.session("sanjiao")
            """) + textwrap.dedent(body)
            result = subprocess.run([sys.executable, "-X", "utf8", "-c", script],
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(error_logs(logs), "")
            return result.stdout

    def test_schema_only_zip(self):
        # No default.custom.yaml: the user adds sanjiao to schema_list herself.
        out = self.run_scenario("-schema-only.zip", {
            "default.custom.yaml": "patch:\n  schema_list/+:\n    - schema: sanjiao\n",
        }, """
            s.type("101010")
            print(s.texts())
        """)
        self.assertEqual(out.strip(), "['三']")

    def test_customize_enable_learning(self):
        # The patch documented in docs/customize.md.
        patch = (ROOT / "docs" / "examples" / "sanjiao.custom.yaml").read_text(encoding="utf-8")
        out = self.run_scenario("-hamster.zip", {"sanjiao.custom.yaml": patch}, """
            s.type("331120"); s.pick(3)
            s.reset(); s.type("331120")
            print(s.texts()[0])
        """)
        self.assertEqual(out.strip(), "滒")

    def test_customize_auto_select(self):
        # Also documented in docs/customize.md.
        out = self.run_scenario("-hamster.zip", {
            "sanjiao.custom.yaml": "patch:\n  speller/auto_select: true\n",
        }, """
            s.type("101010"); print(repr(s.committed), repr(s.input))
            s.reset(); s.type("331120"); print(repr(s.committed), repr(s.input))
        """)
        unique, several = out.strip().split("\n")
        self.assertEqual(unique, "'三' ''")  # one candidate: sent at once
        self.assertEqual(several, "'' '331120'")  # six candidates: waits


if __name__ == "__main__":
    unittest.main()
