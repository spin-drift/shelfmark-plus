"""Group audio files from a flat directory into per-book buckets."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# "Title [ID] - 01 - Chapter Name" → "Title [ID]"
_CHAPTER_PATTERN = re.compile(r"^(.*?)\s+-\s+\d+\s+-\s+.+$")
# "Title - Part 01" or "Title - 01" at end of string
_PART_PATTERN = re.compile(r"^(.*?)\s+-\s+(?:Part\s*)?\d+\s*$", re.IGNORECASE)


def _book_prefix(stem: str) -> str:
    """Strip chapter/part suffix to get the book identity key."""
    m = _CHAPTER_PATTERN.match(stem)
    if m:
        return m.group(1).strip()
    m = _PART_PATTERN.match(stem)
    if m:
        return m.group(1).strip()
    return stem


def group_book_files(files: list[Path]) -> dict[str, list[Path]]:
    """Group a flat list of audio files into per-book buckets.

    Returns a dict mapping book-prefix → [files].
    A group with >1 file is a multi-part book (chapters).
    A group with 1 file is a standalone book.
    Single-group results mean all files belong to one book — callers
    should fall through to existing part-numbering logic unchanged.
    """
    groups: dict[str, list[Path]] = {}
    for f in files:
        key = _book_prefix(f.stem)
        groups.setdefault(key, []).append(f)
    return groups
