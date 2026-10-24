"""The generated RIME dictionary and its candidate ranking."""

import unittest

from tests import ROOT
from tools.cin import parse_cin
from tools.dictgen import visible_entries
from tools.fontcover import read_supplementary
from tools.ranking import Layer, layer_of, weight_of

DICT_PATH = ROOT / "rime" / "sanjiao.dict.yaml"


def read_dict_rows():
    text = DICT_PATH.read_text(encoding="utf-8")
    header, sep, body = text.partition("\n...\n")
    assert sep, "dictionary header terminator '...' not found"
    rows = []
    for line in body.split("\n"):
        if not line:
            continue
        char, code, weight = line.split("\t")
        rows.append((char, code, int(weight)))
    return header, rows


class Layers(unittest.TestCase):
    def test_layer_examples(self):
        cases = {
            "三": Layer.BIG5_LEVEL1,
            "齊": Layer.BIG5_LEVEL1,
            "撉": Layer.BIG5_LEVEL2,
            "亠": Layer.OTHER_BMP,  # in Unicode basic block, not in Big5
            "═": Layer.OTHER_BMP,  # symbol (Big5 ETEN extension)
            "　": Layer.OTHER_BMP,  # Big5 symbol area, not a hanzi
            "㽫": Layer.OTHER_BMP,  # CJK Extension A
            "𣵼": Layer.SUPPLEMENTARY,  # CJK Extension B
        }
        for char, layer in cases.items():
            with self.subTest(char=char):
                self.assertEqual(layer_of(char), layer)


class GeneratedDictionary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header, cls.rows = read_dict_rows()
        cls.table = parse_cin(ROOT / "data" / "3corner.cin")
        cls.entries = visible_entries(cls.table, read_supplementary())

    def candidates(self, code):
        """Candidates for a code in the order RIME shows them (by weight)."""
        matches = [(w, c) for c, k, w in self.rows if k == code]
        return [c for w, c in sorted(matches, reverse=True)]

    def test_header(self):
        self.assertIn("name: sanjiao", self.header)
        self.assertIn("sort: by_weight", self.header)
        self.assertIn("use_preset_vocabulary: false", self.header)
        self.assertIn("columns:\n  - text\n  - code\n  - weight", self.header)

    def test_every_visible_entry_present_once(self):
        self.assertEqual(len(self.rows), len(self.entries))
        self.assertEqual(
            {(c, k) for c, k, _ in self.rows},
            {(e.text, e.code) for e in self.entries},
        )

    def test_undisplayable_rare_characters_removed(self):
        chars = {c for c, _, _ in self.rows}
        self.assertNotIn("𢘍", chars)  # 559300, Extension B, not in PingFang
        self.assertIn("𠢹", chars)  # 024744, Extension B, in PingFang
        self.assertIn("㢙", chars)  # Extension A: PingFang has all of it
        supplementary = {c for c in chars if layer_of(c) == Layer.SUPPLEMENTARY}
        self.assertEqual(supplementary, read_supplementary())

    def test_codes_are_six_digit_strings(self):
        for char, code, _ in self.rows:
            self.assertRegex(code, r"^[0-9]{6}$", msg=char)
        self.assertIn(("═", "000010"), {(c, k) for c, k, _ in self.rows})

    def test_weights_positive_and_unique_per_code(self):
        seen = {}
        for char, code, weight in self.rows:
            self.assertGreater(weight, 0)
            self.assertNotIn((code, weight), seen, msg=f"{char} ties with {seen.get((code, weight))}")
            seen[(code, weight)] = char

    def test_weights_match_ranking_module(self):
        expected = {(e.text, e.code): weight_of(e) for e in self.entries}
        for char, code, weight in self.rows:
            self.assertEqual(weight, expected[(char, code)])

    def test_common_characters_rank_first(self):
        # In the .cin file a rare character comes first for these codes.
        self.assertEqual(self.candidates("018660")[0], "高")
        self.assertEqual(self.candidates("010000")[0], "齊")
        self.assertEqual(self.candidates("012000"), ["劑", "市", "巿"])

    def test_layer_order_never_inverted(self):
        by_code = {}
        for e in self.entries:
            by_code.setdefault(e.code, []).append(e.text)
        for code in by_code:
            layers = [layer_of(c) for c in self.candidates(code)]
            self.assertEqual(layers, sorted(layers), msg=code)

    def test_layer_first_then_original_order(self):
        # .cin order is 汗 汙 泟 涆 滒 𣵼. 泟 is not in Big5 at all, so it
        # moves after the level-2 characters 涆 滒. Extension B 𣵼 would come
        # last, but iPhone cannot display it, so it is left out.
        L = Layer
        self.assertEqual([layer_of(c) for c in "汗汙涆滒泟𣵼"],
                         [L.BIG5_LEVEL1, L.BIG5_LEVEL1, L.BIG5_LEVEL2, L.BIG5_LEVEL2,
                          L.OTHER_BMP, L.SUPPLEMENTARY])
        self.assertEqual(self.candidates("331120"), ["汗", "汙", "涆", "滒", "泟"])
        # .cin order 㢙 勵 𠢹: Extension B characters that iPhone can display stay, last.
        self.assertEqual(self.candidates("024744"), ["勵", "㢙", "𠢹"])

    def test_unix_newlines_only(self):
        self.assertNotIn(b"\r", DICT_PATH.read_bytes())


if __name__ == "__main__":
    unittest.main()
