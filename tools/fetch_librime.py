"""Download the official librime build used by the integration tests.

Usage:
    python -m tools.fetch_librime

The archive comes from the official release page of rime/librime on GitHub,
is checked against a pinned SHA-256, and is unpacked into .cache/librime/
(ignored by git). Nothing is installed on the system: the tests load the
library directly from that folder.

Supported: Windows x64 and macOS (universal).
"""

from __future__ import annotations

import hashlib
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "librime"

VERSION = "1.17.0"
COMMIT = "33e7814"
ARCHIVES = {
    "Windows": (
        f"rime-{COMMIT}-Windows-msvc-x64.7z",
        "7478c7caa4ff6b37de86daba1f7ce4a994a4f5ba24872a820fb2b3a9b01fed15",
    ),
    "Darwin": (
        f"rime-{COMMIT}-macOS-universal.tar.bz2",
        "11d8dc663c6ec06d5ccb6111ba664a9e7b631b703ac6acd07cffbac664021850",
    ),
}


def dist_dir() -> Path:
    return CACHE / VERSION / "dist"


def fetch() -> Path:
    system = platform.system()
    if system not in ARCHIVES:
        raise SystemExit(f"no prebuilt librime for {system}; set RIME_DIST to a librime dist folder")
    name, expected = ARCHIVES[system]
    target = CACHE / VERSION
    if (target / "dist").is_dir():
        return target / "dist"

    target.mkdir(parents=True, exist_ok=True)
    archive = target / name
    url = f"https://github.com/rime/librime/releases/download/{VERSION}/{name}"
    print(f"downloading {url}")
    with urllib.request.urlopen(url) as resp, archive.open("wb") as out:
        shutil.copyfileobj(resp, out)

    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != expected:
        archive.unlink()
        raise SystemExit(f"SHA-256 mismatch for {name}:\n  expected {expected}\n  actual   {actual}")

    if name.endswith(".7z"):
        # Windows 10+ ships bsdtar (libarchive), which can read 7z.
        tar_exe = Path(r"C:\Windows\System32\tar.exe")
        subprocess.run([str(tar_exe), "-xf", str(archive), "-C", str(target)], check=True)
    else:
        with tarfile.open(archive, "r:bz2") as tf:
            tf.extractall(target, filter="data")
    archive.unlink()
    print(f"librime {VERSION} ready in {target / 'dist'}")
    return target / "dist"


if __name__ == "__main__":
    fetch()
    sys.exit(0)
