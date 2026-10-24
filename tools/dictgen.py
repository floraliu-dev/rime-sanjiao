"""Generate rime/sanjiao.dict.yaml from the parsed .cin table."""

from __future__ import annotations

from tools.cin import CinTable, Entry
from tools.ranking import Layer, layer_of, weight_of

DICT_NAME = "sanjiao"


def visible_entries(table: CinTable, displayable: set[str]) -> list[Entry]:
    """Entries iPhone can display: everything except CJK Extension B+
    characters missing from `displayable` (data/ios-supplementary.txt),
    which would show as a box with a question mark."""
    return [e for e in table.entries
            if layer_of(e.text) != Layer.SUPPLEMENTARY or e.text in displayable]


def render_dict(table: CinTable, displayable: set[str], *, version: str, source_note: str) -> str:
    """Return the full text of sanjiao.dict.yaml.

    The output is deterministic (same input -> byte-identical output), so the
    committed file can be checked for drift in tests and CI.
    """
    header = f"""\
# Rime dictionary
# encoding: utf-8
#
# 三角編號輸入法 碼表
#
# 本檔由 build.py 自動產生，請勿手動修改。
# 要調整內容，請改 data/3corner.cin 或 tools/ 下的程式後重新執行 python build.py。
#
# {source_note}
# 已移除 iPhone 字型顯示不出來的罕用字（擴充 B 區以後），清單見 data/ios-supplementary.txt。
# 編碼規則：胡立人、張源渭、黃克東（美國王安電腦公司）
# 授權：碼表為 Public Domain（見 THIRD_PARTY_NOTICES.md）
#
# 欄位：字<Tab>6 位數編碼<Tab>排序權重（數字越大越前面，見 tools/ranking.py）

---
name: {DICT_NAME}
version: "{version}"
sort: by_weight
use_preset_vocabulary: false
max_phrase_length: 1
columns:
  - text
  - code
  - weight
...

"""
    lines = [f"{e.text}\t{e.code}\t{weight_of(e)}" for e in visible_entries(table, displayable)]
    return header + "\n".join(lines) + "\n"
