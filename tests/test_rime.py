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
# schema already in schema_list, to prove our patch puts sanjiao first without
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

    def test_schema_prepended_to_existing_list(self):
        self.assertEqual(self.rime.schema_ids(), ["sanjiao", "other"])

    def test_no_errors_logged(self):
        self.assertEqual(error_logs(self.logs), "")

    # -- looking up characters -------------------------------------------------

    def test_unique_full_code_commits_itself(self):
        for keys, char in (("101010", "三"), ("305354", "我"), ("495472", "李"), ("442958", "蓁")):
            with self.subTest(keys=keys):
                s = self.typed(keys)
                self.assertEqual((s.committed, s.input), (char, ""))
        self.assertEqual(self.typed("101010305354").committed, "三我")

    def test_several_candidates_wait_for_a_choice(self):
        s = self.typed("140400")
        self.assertEqual((s.committed, s.input, s.texts()), ("", "140400", ["玟", "玫"]))
        s.pick(1)
        self.assertEqual(s.committed, "玫")

    def test_leading_zeros(self):
        self.assertEqual(self.typed("000010").committed, "═")

    def test_ideographic_space(self):
        self.assertEqual(self.typed("000000").committed, "　")

    def test_trailing_zeros_may_be_omitted(self):
        # 101000 二, typed as 10100 / 1010 / 101; 100000 一, typed as 1.
        for keys in ("10100", "1010", "101"):
            with self.subTest(keys=keys):
                self.assertEqual(self.typed(keys).texts()[0], "二")
        self.assertEqual(self.typed("1").texts()[0], "一")
        self.assertEqual(self.typed("10101").texts()[0], "三")  # 101010
        self.assertEqual(self.typed("26").texts()[0], "月")  # 260000

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

    def test_invalid_code_is_cleared(self):
        # 44295 has candidates (蓁 is 442958); no code starts with 442956.
        self.assertEqual(self.typed("44295").input, "44295")
        s = self.typed("442956")
        self.assertEqual((s.input, s.texts(), s.committed), ("", [], ""))
        self.assertEqual(self.typed("4429568").input, "8")  # next digit starts afresh

    # -- committing ------------------------------------------------------------

    def test_space_commits_first_candidate(self):
        s = self.typed("10101{space}")
        self.assertEqual((s.committed, s.input), ("三", ""))
        self.assertEqual(self.typed("10{space}").committed, "一")

    def test_enter_commits_first_candidate(self):
        # "|" is the touch keyboard's 換行 key; Return is a physical Enter.
        for enter in ("|", "{Return}"):
            with self.subTest(enter=enter):
                s = self.typed("26" + enter)
                self.assertEqual((s.committed, s.input), ("月", ""))
                self.assertEqual(self.typed("140400" + enter).committed, "玟")

    def test_enter_key_alone_is_a_newline(self):
        self.assertEqual(self.typed("|").committed, "\n")

    def test_tap_candidate(self):
        self.typed("331120")
        self.s.pick(1)
        self.assertEqual((self.s.committed, self.s.input), ("汙", ""))

    def test_continuous_typing_commits_at_seventh_digit(self):
        s = self.typed("1404001")
        self.assertEqual((s.committed, s.input), ("玟", "1"))

    def test_space_with_nothing_typed_is_passed_to_the_app(self):
        # Not handled by RIME, so the app inserts a normal space.
        self.s.reset()
        self.assertFalse(self.s.press("space"))

    def test_enter_with_nothing_typed_is_passed_to_the_app(self):
        self.s.reset()
        self.assertFalse(self.s.press("Return"))

    def test_escape_and_backspace(self):
        s = self.typed("10101{Escape}")
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
        self.assertEqual(self.typed("10101,").committed, "三，")
        self.assertEqual(self.typed("140400\\").committed, "玟、")


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
        # No default.custom.yaml: the user adds sanjiao to schema_list themselves,
        # with the snippet from docs/install-iphone.md.
        out = self.run_scenario("-schema-only.zip", {
            "default.custom.yaml": "patch:\n  schema_list/@before 0:\n    schema: sanjiao\n",
        }, """
            s.type("101010")
            print(s.committed)
        """)
        self.assertEqual(out.strip(), "三")

    def test_customize_enable_learning(self):
        # The patch documented in docs/customize.md.
        patch = (ROOT / "docs" / "examples" / "sanjiao.custom.yaml").read_text(encoding="utf-8")
        out = self.run_scenario("-hamster.zip", {"sanjiao.custom.yaml": patch}, """
            s.type("331120"); s.pick(3)
            s.reset(); s.type("331120")
            print(s.texts()[0])
        """)
        self.assertEqual(out.strip(), "滒")

    def test_customize_turn_off_auto_select(self):
        # Also documented in docs/customize.md.
        out = self.run_scenario("-hamster.zip", {
            "sanjiao.custom.yaml": "patch:\n  speller/auto_select: false\n",
        }, """
            s.type("101010"); print(repr(s.committed), repr(s.input))
        """)
        self.assertEqual(out.strip(), "'' '101010'")  # waits for a choice


if __name__ == "__main__":
    unittest.main()
