"""The 三角編號 touch keyboard for 倉輸入法 (Hamster), defined once.

Hamster has used two YAML syntaxes for custom keyboards:

* "wiki"   - the format in the official wiki page 自定义布局 (Hamster 2.2.0+):
             action: { character: { char: "1" } }
* "legacy" - the format parsed by the last open-source release (2.1.x):
             action: character(1)

Which one the current App Store build accepts must be confirmed on a real
device (see docs/device-test.md). Both are generated from the single LAYOUT
below so they can never drift apart.

Layout (portrait), 5 equal-width columns:

    符號   1   2   3   ⌫        ⌫ swipe up: clear the code being typed
    ABC    4   5   6   ，       ， swipe up: ；
    🌐     7   8   9   。       。 swipe up: ：
    ？     、  0   空格 換行     ？ swipe up: ！   、 swipe up: 「  down: 」

Design notes:
* Digits sit in the familiar phone-pad grid, with 0 under 8.
* Punctuation keys send ASCII through RIME, so the schema's punctuator turns
  "," into "，" and first commits whatever is being typed.
* 🌐 (nextKeyboard) is always present: iPhones with a Home button have no
  system globe key under the keyboard.
"""

from __future__ import annotations

from dataclasses import dataclass, field

KEYBOARD_NAME = "三角編號"


# ---- semantic actions -------------------------------------------------------


@dataclass(frozen=True)
class Char:
    """An ASCII key sent to RIME (digits, and punctuation the schema maps)."""

    char: str


@dataclass(frozen=True)
class Simple:
    """backspace / enter / space / nextKeyboard."""

    name: str


@dataclass(frozen=True)
class SwitchKeyboard:
    """alphabetic / classifySymbolic / ..."""

    keyboard_type: str


@dataclass(frozen=True)
class Shortcut:
    """A Hamster shortcut command. Names are Hamster's own (Simplified)."""

    command: str


Action = Char | Simple | SwitchKeyboard | Shortcut


@dataclass(frozen=True)
class Swipe:
    direction: str  # up / down / left / right
    action: Action
    label: str


@dataclass(frozen=True)
class Key:
    action: Action
    label: str | None = None  # None: let Hamster draw its default label/icon
    swipes: tuple[Swipe, ...] = field(default_factory=tuple)


def _digit(d: str) -> Key:
    return Key(Char(d))


def _punct(char: str, label: str, *swipes: Swipe) -> Key:
    return Key(Char(char), label, swipes)


BACKSPACE = Key(
    Simple("backspace"),
    swipes=(Swipe("up", Shortcut("#重输"), "清除"),),
)

LAYOUT: tuple[tuple[Key, ...], ...] = (
    (Key(SwitchKeyboard("classifySymbolic"), "符號"), _digit("1"), _digit("2"), _digit("3"), BACKSPACE),
    (Key(SwitchKeyboard("alphabetic"), "ABC"), _digit("4"), _digit("5"), _digit("6"),
     _punct(",", "，", Swipe("up", Char(";"), "；"))),
    (Key(Simple("nextKeyboard")), _digit("7"), _digit("8"), _digit("9"),
     _punct(".", "。", Swipe("up", Char(":"), "："))),
    (_punct("?", "？", Swipe("up", Char("!"), "！")),
     _punct("\\", "、", Swipe("up", Char("["), "「"), Swipe("down", Char("]"), "」")),
     _digit("0"),
     Key(Simple("space"), "空格"),
     Key(Simple("enter"))),
)

# Every ASCII character the keyboard sends to RIME. The schema's punctuator
# must define each non-digit one; tests/test_keyboard.py checks this.
def ascii_sent_to_rime() -> set[str]:
    sent: set[str] = set()
    for row in LAYOUT:
        for key in row:
            for action in (key.action, *(s.action for s in key.swipes)):
                if isinstance(action, Char):
                    sent.add(action.char)
    return sent


# ---- rendering --------------------------------------------------------------

FORMATS = ("wiki", "legacy")


def _q(value: str) -> str:
    """YAML double-quoted scalar."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _action(action: Action, fmt: str) -> str:
    if fmt == "wiki":
        if isinstance(action, Char):
            return f"{{ character: {{ char: {_q(action.char)} }} }}"
        if isinstance(action, Simple):
            return action.name
        if isinstance(action, SwitchKeyboard):
            return f"{{ keyboardType: {action.keyboard_type} }}"
        if isinstance(action, Shortcut):
            return f"{{ shortcutCommand: {_q(action.command)} }}"
    elif fmt == "legacy":
        # The legacy parser reads everything between the first "(" and the
        # last ")" verbatim, so no escaping happens inside the parentheses.
        if isinstance(action, Char):
            return _q(f"character({action.char})")
        if isinstance(action, Simple):
            return action.name
        if isinstance(action, SwitchKeyboard):
            return _q(f"keyboardType({action.keyboard_type})")
        if isinstance(action, Shortcut):
            return _q(f"shortCommand({action.command})")
    raise ValueError(f"cannot render {action!r} as {fmt}")


def render_keyboard(fmt: str, base: int = 4) -> str:
    """Render the keyboard as one item of Hamster's `keyboards:` list.

    `base` is the column of the leading "- ". Each nested level is indented
    so that a mapping's keys line up with the first key after its "- ".
    """
    if fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt!r}")
    sp = " "
    item = sp * base            # "- name:"
    kb = sp * (base + 2)        # keyboard fields
    row_item = sp * (base + 4)  # "- keys:"
    key_item = sp * (base + 8)  # "- action:"
    i4 = sp * (base + 10)       # key fields
    out = [
        f"{item}- name: {_q(KEYBOARD_NAME)}",
        f"{kb}isPrimary: true",
        f"{kb}rows:",
    ]
    for row in LAYOUT:
        out.append(f"{row_item}- keys:")
        for key in row:
            out.append(f"{key_item}- action: {_action(key.action, fmt)}")
            if key.action == Simple("space"):
                # Space takes a {loadingText, text} label; loadingText shows
                # briefly when the keyboard appears.
                out.append(f"{i4}label: {{ loadingText: {_q(KEYBOARD_NAME)}, text: {_q(key.label or '')} }}")
            elif key.label is not None:
                out.append(f"{i4}label: {_q(key.label)}")
            if isinstance(key.action, Char):
                out.append(f"{i4}processByRIME: true")
            if key.swipes:
                out.append(f"{i4}swipe:")
                for s in key.swipes:
                    out.append(f"{i4}  - direction: {s.direction}")
                    out.append(f"{i4}    action: {_action(s.action, fmt)}")
                    out.append(f"{i4}    label: {_q(s.label)}")
                    out.append(f"{i4}    display: true")
                    # Swipes default to bypassing RIME; route them through it
                    # so punctuation is converted and pending input committed.
                    if isinstance(s.action, Char):
                        out.append(f"{i4}    processByRIME: true")
    return "\n".join(out) + "\n"


def use_keyboard_type(fmt: str) -> str:
    """Value for keyboard/useKeyboardType that selects this keyboard.

    The wiki format names a custom keyboard directly; the legacy parser
    expects custom(<name>).
    """
    if fmt == "wiki":
        return KEYBOARD_NAME
    if fmt == "legacy":
        return f"custom({KEYBOARD_NAME})"
    raise ValueError(f"unknown format {fmt!r}")


def render_hamster_custom(fmt: str, *, version: str) -> str:
    """Return the full text of hamster.custom.yaml for the given format."""
    return f"""\
# 倉輸入法（Hamster）設定補丁：三角編號鍵盤
#
# 本檔由 build.py 自動產生，請勿手動修改；鍵盤配置定義在 tools/keyboard.py。
# 版本：{version}　鍵盤語法：{fmt}
#
# 注意：
# 1. 匯入後會取代手機上原有的 hamster.custom.yaml（如果有的話）。
# 2. keyboards 清單會整個取代倉內建的自訂鍵盤範例（例如倉頡、大千注音），
#    內建的中文 26 鍵、九宮格、英文鍵盤不受影響。
# 3. useKeyboardType 只在你沒有從倉的設定畫面手動選過鍵盤時生效；
#    如果鍵盤沒有變，請到「鍵盤設定 → 鍵盤布局」手動選「{KEYBOARD_NAME}」。

patch:
  keyboard:
    useKeyboardType: {_q(use_keyboard_type(fmt))}
  keyboards:
{render_keyboard(fmt)}"""
