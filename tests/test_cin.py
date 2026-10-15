"""The .cin parser: strict on malformed input, faithful on the real table."""

import tempfile
import unittest
from pathlib import Path

from tests import ROOT
from tools.cin import CinError, parse_cin

HEADER = "%cname 測試\n%selkey 1234567890\n"


def parse_text(text: str, *, raw: bytes | None = None):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.cin"
        path.write_bytes(raw if raw is not None else text.encode("utf-8"))
        return parse_cin(path)


class MalformedInput(unittest.TestCase):
    def assertRejects(self, text: str, fragment: str, *, raw: bytes | None = None):
        with self.assertRaises(CinError) as ctx:
            parse_text(text, raw=raw)
        self.assertIn(fragment, str(ctx.exception))

    def test_minimal_valid_table(self):
        t = parse_text(HEADER + "%chardef begin\n101010 三\n%chardef end\n")
        self.assertEqual(t.cname, "測試")
        self.assertEqual(t.selkey, "1234567890")
        self.assertEqual([(e.code, e.text, e.ordinal) for e in t.entries], [("101010", "三", 0)])

    def test_code_too_short(self):
        self.assertRejects(HEADER + "%chardef begin\n10101 三\n%chardef end\n", "not 6 digits")

    def test_code_not_digits(self):
        self.assertRejects(HEADER + "%chardef begin\n10101a 三\n%chardef end\n", "not 6 digits")

    def test_more_than_one_character(self):
        self.assertRejects(HEADER + "%chardef begin\n101010 三角\n%chardef end\n", "one character")

    def test_missing_separator(self):
        self.assertRejects(HEADER + "%chardef begin\n101010\n%chardef end\n", "no space")

    def test_duplicate_entry(self):
        self.assertRejects(HEADER + "%chardef begin\n101010 三\n101010 三\n%chardef end\n", "duplicate entry")

    def test_missing_end(self):
        self.assertRejects(HEADER + "%chardef begin\n101010 三\n", "missing")

    def test_content_after_end(self):
        self.assertRejects(HEADER + "%chardef begin\n101010 三\n%chardef end\n999999 x\n", "after %chardef end")

    def test_empty_chardef(self):
        self.assertRejects(HEADER + "%chardef begin\n%chardef end\n", "empty")

    def test_crlf(self):
        self.assertRejects("", "carriage return", raw=b"%chardef begin\r\n101010 x\r\n%chardef end\r\n")

    def test_bom(self):
        self.assertRejects("", "BOM", raw=b"\xef\xbb\xbf%chardef begin\n101010 x\n%chardef end\n")

    def test_whitespace_character_is_kept(self):
        # The real table maps 000000 to U+3000 IDEOGRAPHIC SPACE.
        t = parse_text(HEADER + "%chardef begin\n000000 　\n%chardef end\n")
        self.assertEqual(t.entries[0].text, "　")


class RealTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = parse_cin(ROOT / "data" / "3corner.cin")
        cls.codes = {}
        for e in cls.table.entries:
            cls.codes.setdefault(e.code, []).append(e.text)

    def test_size(self):
        self.assertEqual(len(self.table.entries), 32_889)
        self.assertEqual(len(self.codes), 28_880)

    def test_metadata(self):
        self.assertEqual(self.table.cname, "三角編號")
        self.assertEqual(self.table.selkey, "1234567890")

    def test_known_characters(self):
        expected = {"三": "101010", "我": "305354", "你": "227290", "一": "100000", "二": "101000"}
        for char, code in expected.items():
            with self.subTest(char=char):
                self.assertIn(char, self.codes[code])

    def test_leading_zeros_preserved(self):
        self.assertIn("═", self.codes["000010"])
        self.assertIn("　", self.codes["000000"])

    def test_original_order_kept(self):
        ordinals = [e.ordinal for e in self.table.entries]
        self.assertEqual(ordinals, list(range(len(ordinals))))
        # Raw file order. (The dictionary re-ranks it; see test_dict.py.)
        self.assertEqual(self.codes["331120"], ["汗", "汙", "泟", "涆", "滒", "𣵼"])


if __name__ == "__main__":
    unittest.main()
