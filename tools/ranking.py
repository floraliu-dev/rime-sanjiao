"""Candidate ranking: which character is shown first when codes collide.

About 12% of codes map to more than one character. RIME orders those
candidates by a numeric weight (higher first). The weight here combines two
signals, in priority order:

1. Layer, from most to least common:
     0  Big5 level-1 常用字 (0xA440-0xC67E, 5,401 characters)
     1  Big5 level-2 次常用字 (0xC940-0xF9D5, 7,652 characters)
     2  everything else in the Basic Multilingual Plane
        (symbols, CJK Extension A, characters outside Big5)
     3  supplementary planes (CJK Extension B and later, U+20000+)
   Layer 3 characters are rare and some fonts cannot display them, so they
   always come last.
2. Original order in the .cin file, which keeps the upstream author's
   ordering inside a layer.

The same layering is used by SanJiaoIM, the MIT-licensed macOS
implementation of this input method.
"""

from __future__ import annotations

from enum import IntEnum

from tools.cin import Entry


class Layer(IntEnum):
    BIG5_LEVEL1 = 0
    BIG5_LEVEL2 = 1
    OTHER_BMP = 2
    SUPPLEMENTARY = 3


_BIG5_LEVEL1 = range(0xA440, 0xC67E + 1)
_BIG5_LEVEL2 = range(0xC940, 0xF9D5 + 1)

# Weight = LAYER_STEP * (number of layers - layer) - ordinal.
# LAYER_STEP must exceed any ordinal so layers never interleave.
LAYER_STEP = 100_000


def layer_of(text: str) -> Layer:
    if ord(text) > 0xFFFF:
        return Layer.SUPPLEMENTARY
    try:
        encoded = text.encode("big5")
    except UnicodeEncodeError:
        return Layer.OTHER_BMP
    value = int.from_bytes(encoded, "big")
    if value in _BIG5_LEVEL1:
        return Layer.BIG5_LEVEL1
    if value in _BIG5_LEVEL2:
        return Layer.BIG5_LEVEL2
    return Layer.OTHER_BMP


def weight_of(entry: Entry) -> int:
    if entry.ordinal >= LAYER_STEP:
        raise ValueError(f"ordinal {entry.ordinal} exceeds LAYER_STEP {LAYER_STEP}")
    return LAYER_STEP * (len(Layer) - layer_of(entry.text)) - entry.ordinal
