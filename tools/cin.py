"""Strict parser for the .cin code table format.

A .cin file is a plain-text table used by many Chinese input-method
frameworks. The parts this project relies on look like:

    %cname 三角編號
    %selkey 1234567890
    %chardef begin
    000010 ═
    101010 三
    %chardef end

Every line inside %chardef is "<code><space><character>". The parser keeps
codes as strings (never integers) so leading zeros survive, and it keeps the
original line order because that order is part of the candidate ranking.

The parser is deliberately strict: anything unexpected raises CinError instead
of being skipped, so a changed or corrupted upstream file can never slip into
a release unnoticed.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

CODE_LENGTH = 6
_CODE_RE = re.compile(rf"[0-9]{{{CODE_LENGTH}}}")


class CinError(ValueError):
    """Raised when the .cin file does not match the expected structure."""


@dataclass(frozen=True)
class Entry:
    code: str  # exactly CODE_LENGTH ASCII digits, leading zeros preserved
    text: str  # exactly one Unicode code point
    ordinal: int  # 0-based position inside %chardef (original order)


@dataclass(frozen=True)
class CinTable:
    cname: str
    selkey: str
    entries: tuple[Entry, ...]


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_cin(path: Path) -> CinTable:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise CinError("unexpected UTF-8 BOM")
    if b"\r" in raw:
        raise CinError("unexpected carriage return (CRLF line endings)")
    lines = raw.decode("utf-8").split("\n")

    directives: dict[str, str] = {}
    begin = end = None
    for i, line in enumerate(lines):
        if line == "%chardef begin":
            if begin is not None:
                raise CinError(f"line {i + 1}: duplicate %chardef begin")
            begin = i
        elif line == "%chardef end":
            if end is not None:
                raise CinError(f"line {i + 1}: duplicate %chardef end")
            end = i
        elif begin is None and line.startswith("%") and " " in line:
            key, value = line[1:].split(" ", 1)
            directives[key] = value
    if begin is None or end is None or end < begin:
        raise CinError("missing or misordered %chardef begin/end")

    entries: list[Entry] = []
    seen: set[tuple[str, str]] = set()
    for i in range(begin + 1, end):
        line = lines[i]
        lineno = i + 1
        # Split on the first space only: the character itself may be a
        # whitespace code point (the table maps 000000 to U+3000).
        code, sep, text = line.partition(" ")
        if not sep:
            raise CinError(f"line {lineno}: no space separator: {line!r}")
        if not _CODE_RE.fullmatch(code):
            raise CinError(f"line {lineno}: code is not {CODE_LENGTH} digits: {code!r}")
        if len(text) != 1:
            raise CinError(f"line {lineno}: expected one character, got {text!r}")
        if (code, text) in seen:
            raise CinError(f"line {lineno}: duplicate entry {code} {text!r}")
        seen.add((code, text))
        entries.append(Entry(code=code, text=text, ordinal=len(entries)))

    trailing = [line for line in lines[end + 1 :] if line.strip()]
    if trailing:
        raise CinError(f"unexpected content after %chardef end: {trailing[0]!r}")
    if not entries:
        raise CinError("%chardef section is empty")

    return CinTable(
        cname=directives.get("cname", ""),
        selkey=directives.get("selkey", ""),
        entries=tuple(entries),
    )
