"""Build every generated file of rime-sanjiao.

Usage:
    python build.py            regenerate generated files
    python build.py --check    fail if any generated file is out of date
    python build.py --package  regenerate, then build the zip files in dist/

Generated files (never edit these by hand):
    rime/sanjiao.dict.yaml               from data/3corner.cin
    hamster/hamster.custom.yaml          keyboard

Hand-written files:
    rime/sanjiao.schema.yaml, rime/default.custom.yaml, tools/keyboard.py
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

if sys.version_info < (3, 10):
    raise SystemExit(
        f"需要 Python 3.10 以上，目前是 {sys.version.split()[0]}。"
        "macOS 內建的 python3 太舊，請從 https://www.python.org/downloads/ 安裝新版。"
    )

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from tools.cin import parse_cin, sha256_of  # noqa: E402
from tools.dictgen import render_dict  # noqa: E402
from tools.keyboard import render_hamster_custom  # noqa: E402

CIN_PATH = ROOT / "data" / "3corner.cin"
EXPECTED_SHA256 = "d5fa9e4f9cc21ed82020aec6dbba5f20a9629d5bc88f36d6bbfff1752581e019"
UPSTREAM_NOTE = (
    "來源：chinese-opendesktop/cin-tables 3corner.cin "
    "@ c19338255f2aac07b3e5eca4f4a8e8df30c2586b"
)

SCHEMA_PATH = ROOT / "rime" / "sanjiao.schema.yaml"
DEFAULT_CUSTOM_PATH = ROOT / "rime" / "default.custom.yaml"
DICT_PATH = ROOT / "rime" / "sanjiao.dict.yaml"
HAMSTER_PATH = ROOT / "hamster" / "hamster.custom.yaml"
DIST = ROOT / "dist"


def zip_date(data: bytes) -> tuple[int, int, int, int, int, int]:
    """A timestamp derived from the file's content.

    The same content always gets the same date, so zips are byte-identical.
    Changed content gets a different date, which matters: RIME rebuilds a
    schema only when a source file's modification time differs from the one
    it recorded, so a fixed date made 倉輸入法 keep the old schema after an
    update (found on a device on 2026-10-24).
    """
    seconds = int.from_bytes(hashlib.sha256(data).digest()[:4], "big") % (20 * 365 * 86400)  # 2000–2019: never in the future
    return (datetime(2000, 1, 1) + timedelta(seconds=seconds - seconds % 2)).timetuple()[:6]


def read_version() -> str:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"VERSION is not x.y.z: {version!r}")
    return version


def schema_version() -> str:
    text = SCHEMA_PATH.read_text(encoding="utf-8")
    match = re.search(r'^  version: "([^"]+)"$', text, re.MULTILINE)
    if not match:
        raise SystemExit("cannot find schema/version in sanjiao.schema.yaml")
    return match.group(1)


def generated_files(version: str) -> dict[Path, str]:
    actual = sha256_of(CIN_PATH)
    if actual != EXPECTED_SHA256:
        raise SystemExit(
            f"data/3corner.cin SHA-256 mismatch:\n  expected {EXPECTED_SHA256}\n  actual   {actual}\n"
            "If the code table was updated on purpose, follow data/SOURCE.md."
        )
    table = parse_cin(CIN_PATH)
    return {
        DICT_PATH: render_dict(table, version=version, source_note=UPSTREAM_NOTE),
        HAMSTER_PATH: render_hamster_custom(version=version),
    }


def write_zip(path: Path, members: dict[str, Path]) -> None:
    """Write a flat zip (no folders inside), as 倉輸入法 requires."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, src in sorted(members.items()):
            data = src.read_bytes()
            info = zipfile.ZipInfo(name, date_time=zip_date(data))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)


def package(dist: Path = DIST) -> list[Path]:
    schema_files = {
        "sanjiao.schema.yaml": SCHEMA_PATH,
        "sanjiao.dict.yaml": DICT_PATH,
    }
    # No version in the file names, so releases/latest/download/<name>
    # always points at the newest release. The version is inside the
    # schema (schema/version) and on the release tag.
    outputs = {
        # Everything a new 倉輸入法 user needs, in one import.
        dist / "rime-sanjiao-hamster.zip": {
            **schema_files,
            "default.custom.yaml": DEFAULT_CUSTOM_PATH,
            "hamster.custom.yaml": HAMSTER_PATH,
        },
        # Only the schema, for people who manage their own RIME config
        # (any RIME frontend: 倉, 鼠鬚管, 小狼毫, 中州韻 ...).
        dist / "rime-sanjiao-schema-only.zip": schema_files,
    }
    for path, members in outputs.items():
        write_zip(path, members)
    return list(outputs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="only verify generated files are up to date")
    mode.add_argument("--package", action="store_true", help="also build the zip files in dist/")
    args = parser.parse_args()

    version = read_version()
    if schema_version() != version:
        raise SystemExit(f"schema version {schema_version()!r} != VERSION {version!r}")

    stale = []
    for path, content in generated_files(version).items():
        rel = path.relative_to(ROOT).as_posix()
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            print(f"up to date  {rel}")
            continue
        if args.check:
            stale.append(rel)
            print(f"OUT OF DATE {rel}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        # newline="\n": identical bytes on Windows, macOS and Linux.
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print(f"wrote       {rel}")

    if stale:
        print("\nRun `python build.py` and commit the result.", file=sys.stderr)
        return 1
    if args.package:
        for path in package():
            print(f"packaged    {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
