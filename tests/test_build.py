"""Build reproducibility and the release zip files."""

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from tests import ROOT

sys.path.insert(0, str(ROOT))
import build  # noqa: E402


class Build(unittest.TestCase):
    def test_generated_files_up_to_date(self):
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "build.py"), "--check"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_versions_agree(self):
        version = build.read_version()
        self.assertEqual(build.schema_version(), version)
        self.assertIn(f'version: "{version}"', build.DICT_PATH.read_text(encoding="utf-8"))
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## {version}", changelog)

    def test_source_table_is_pinned(self):
        from tools.cin import sha256_of
        self.assertEqual(sha256_of(build.CIN_PATH), build.EXPECTED_SHA256)
        self.assertIn(build.EXPECTED_SHA256, (ROOT / "data" / "SOURCE.md").read_text(encoding="utf-8"))


class Packages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.paths = build.package(dist=Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def names(self, suffix):
        (path,) = [p for p in self.paths if p.name.endswith(suffix)]
        with zipfile.ZipFile(path) as zf:
            return sorted(zf.namelist())

    def test_contents(self):
        full = ["default.custom.yaml", "hamster.custom.yaml", "sanjiao.dict.yaml", "sanjiao.schema.yaml"]
        self.assertEqual(self.names("-hamster.zip"), full)
        self.assertEqual(self.names("-schema-only.zip"), ["sanjiao.dict.yaml", "sanjiao.schema.yaml"])

    def test_fixed_names(self):
        # install-iphone.md links releases/latest/download/<name>; keep names stable.
        self.assertEqual(sorted(p.name for p in self.paths),
                         ["rime-sanjiao-hamster.zip", "rime-sanjiao-schema-only.zip"])

    def test_flat_no_folders(self):
        # 倉輸入法 requires the files at the zip root, with no folder.
        for path in self.paths:
            with zipfile.ZipFile(path) as zf:
                for name in zf.namelist():
                    self.assertNotIn("/", name, msg=f"{path.name}: {name}")

    def test_hamster_zip_uses_keyboard(self):
        (path,) = [p for p in self.paths if p.name.endswith("-hamster.zip")]
        with zipfile.ZipFile(path) as zf:
            self.assertEqual(zf.read("hamster.custom.yaml"), build.HAMSTER_PATH.read_bytes())

    def test_reproducible(self):
        with tempfile.TemporaryDirectory() as other:
            again = build.package(dist=Path(other))
            for a, b in zip(self.paths, again):
                self.assertEqual(a.read_bytes(), b.read_bytes(), msg=a.name)

    def test_changed_content_gets_a_new_date(self):
        # RIME rebuilds only when a file's modification time changes.
        self.assertEqual(build.zip_date(b"a"), build.zip_date(b"a"))
        self.assertNotEqual(build.zip_date(b"a"), build.zip_date(b"b"))


if __name__ == "__main__":
    unittest.main()
