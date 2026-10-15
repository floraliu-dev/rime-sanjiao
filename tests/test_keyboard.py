"""The 倉輸入法 keyboard: layout rules and both YAML syntaxes."""

import re
import unittest

from tests import ROOT
from tools.keyboard import (
    KEYBOARD_NAME,
    LAYOUT,
    Char,
    Shortcut,
    Simple,
    SwitchKeyboard,
    ascii_sent_to_rime,
    render_hamster_custom,
)

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

HAMSTER_PATHS = {
    "wiki": ROOT / "hamster" / "hamster.custom.yaml",
    "legacy": ROOT / "hamster" / "legacy" / "hamster.custom.yaml",
}

# Hamster's documented vocabularies (wiki page 自定义布局).
SIMPLE_ACTIONS = {"backspace", "enter", "shift", "tab", "space", "nextKeyboard", "none"}
KEYBOARD_TYPES = {"alphabetic", "classifySymbolic", "chinese", "chineseNineGrid", "numericNineGrid"}
SHORTCUTS = {"#重输", "#简繁切换", "#中英切换", "#行首", "#行尾", "#次选上屏", "#三选上屏",
             "#上个输入方案", "#换行", "#RimeSwitcher", "#左移", "#右移", "#关闭键盘",
             "#左手模式", "#右手模式", "#方案切换"}


def all_actions():
    for row in LAYOUT:
        for key in row:
            yield key.action
            for swipe in key.swipes:
                yield swipe.action


class Layout(unittest.TestCase):
    def test_grid_shape(self):
        self.assertEqual([len(row) for row in LAYOUT], [5, 5, 5, 5])

    def test_each_digit_exactly_once(self):
        digits = [a.char for row in LAYOUT for k in row for a in [k.action]
                  if isinstance(a, Char) and a.char.isdigit()]
        self.assertEqual(sorted(digits), list("0123456789"))

    def test_phone_pad_positions(self):
        grid = [[k.action.char if isinstance(k.action, Char) else None for k in row] for row in LAYOUT]
        self.assertEqual([r[1:4] for r in grid[:3]], [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]])
        self.assertEqual(grid[3][2], "0")  # 0 under 8

    def test_essential_keys_present(self):
        actions = set(all_actions())
        for needed in (Simple("backspace"), Simple("space"), Simple("enter"), Simple("nextKeyboard"),
                       SwitchKeyboard("alphabetic"), SwitchKeyboard("classifySymbolic")):
            with self.subTest(needed=needed):
                self.assertIn(needed, actions)

    def test_vocabulary(self):
        for action in all_actions():
            with self.subTest(action=action):
                if isinstance(action, Simple):
                    self.assertIn(action.name, SIMPLE_ACTIONS)
                elif isinstance(action, SwitchKeyboard):
                    self.assertIn(action.keyboard_type, KEYBOARD_TYPES)
                elif isinstance(action, Shortcut):
                    self.assertIn(action.command, SHORTCUTS)
                elif isinstance(action, Char):
                    self.assertEqual(len(action.char), 1)
                    self.assertTrue(action.char.isascii() and action.char.isprintable())

    def test_swipes_are_labelled(self):
        for row in LAYOUT:
            for key in row:
                for s in key.swipes:
                    self.assertIn(s.direction, {"up", "down", "left", "right"})
                    self.assertTrue(s.label)

    def test_schema_maps_every_punctuation_key(self):
        schema = (ROOT / "rime" / "sanjiao.schema.yaml").read_text(encoding="utf-8")
        for char in sorted(ascii_sent_to_rime() - set("0123456789")):
            quoted = '"\\\\"' if char == "\\" else f'"{char}"'
            with self.subTest(char=char):
                self.assertIn(f"    {quoted}: ", schema)


@unittest.skipIf(yaml is None, "PyYAML not installed (pip install -r requirements-dev.txt)")
class RenderedYaml(unittest.TestCase):
    def load(self, fmt):
        return yaml.safe_load(HAMSTER_PATHS[fmt].read_text(encoding="utf-8"))

    def test_files_match_generator(self):
        for fmt, path in HAMSTER_PATHS.items():
            with self.subTest(fmt=fmt):
                version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
                self.assertEqual(path.read_text(encoding="utf-8"), render_hamster_custom(fmt, version=version))

    def test_structure(self):
        for fmt in HAMSTER_PATHS:
            with self.subTest(fmt=fmt):
                patch = self.load(fmt)["patch"]
                self.assertEqual(set(patch), {"keyboard", "keyboards"})
                self.assertEqual(set(patch["keyboard"]), {"useKeyboardType"})
                (kb,) = patch["keyboards"]
                self.assertEqual(kb["name"], KEYBOARD_NAME)
                self.assertIs(kb["isPrimary"], True)
                self.assertEqual([len(r["keys"]) for r in kb["rows"]], [5, 5, 5, 5])

    def test_wiki_syntax(self):
        patch = self.load("wiki")["patch"]
        self.assertEqual(patch["keyboard"]["useKeyboardType"], KEYBOARD_NAME)
        for row in patch["keyboards"][0]["rows"]:
            for key in row["keys"]:
                for action in [key["action"]] + [s["action"] for s in key.get("swipe", [])]:
                    if isinstance(action, str):
                        self.assertIn(action, SIMPLE_ACTIONS)
                    else:
                        (kind,) = action
                        self.assertIn(kind, {"character", "keyboardType", "shortcutCommand"})
                        if kind == "character":
                            self.assertEqual(set(action[kind]), {"char"})
                            self.assertEqual(len(action[kind]["char"]), 1)

    def test_legacy_syntax(self):
        # Mirrors String.attributeParse() in Hamster 2.1.x: name(value), with
        # the value taken verbatim between the first "(" and the last ")".
        pattern = re.compile(r"^(character|keyboardType|shortCommand)\((.+)\)$")
        patch = self.load("legacy")["patch"]
        self.assertEqual(patch["keyboard"]["useKeyboardType"], f"custom({KEYBOARD_NAME})")
        for row in patch["keyboards"][0]["rows"]:
            for key in row["keys"]:
                for action in [key["action"]] + [s["action"] for s in key.get("swipe", [])]:
                    with self.subTest(action=action):
                        self.assertIsInstance(action, str)
                        if action not in SIMPLE_ACTIONS:
                            m = pattern.match(action)
                            self.assertIsNotNone(m)
                            if m.group(1) == "character":
                                self.assertEqual(len(m.group(2)), 1)

    def test_rime_keys_marked_for_rime(self):
        # Keys and swipes that send characters must go through RIME, or the
        # punctuator never sees them. Swipes default to bypassing RIME.
        for fmt in HAMSTER_PATHS:
            for row in self.load(fmt)["patch"]["keyboards"][0]["rows"]:
                for item in row["keys"] + [s for k in row["keys"] for s in k.get("swipe", [])]:
                    action = item["action"]
                    sends_char = (isinstance(action, dict) and "character" in action) or (
                        isinstance(action, str) and action.startswith("character("))
                    if sends_char:
                        self.assertIs(item.get("processByRIME"), True, msg=f"{fmt}: {action}")


if __name__ == "__main__":
    unittest.main()
