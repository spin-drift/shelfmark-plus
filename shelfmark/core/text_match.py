"""Shared text-normalization + fuzzy token-matching helpers for book matching."""

from __future__ import annotations

import re

DEFAULT_TITLE_MATCH_THRESHOLD = 0.85

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "and",
        "or",
        "to",
        "in",
        "on",
        "for",
        "with",
        "is",
        "by",
    }
)


def tokens(text: str | None) -> list[str]:
    """Lowercase alphanumeric tokens from arbitrary text."""
    if not text:
        return []
    return [tok for tok in re.split(r"[^a-z0-9]+", text.lower()) if tok]


def significant_tokens(text: str | None) -> list[str]:
    """Tokens with stopwords and 1-char noise removed."""
    return [tok for tok in tokens(text) if len(tok) >= 2 and tok not in STOPWORDS]


def author_surname(author: str | None) -> str | None:
    """Return the most distinctive author token (the surname), or None."""
    value = author or ""
    if "," in value:
        value = value.split(",")[0]
    toks = significant_tokens(value)
    return toks[-1] if toks else None


def title_tokens_match(
    title: str | None,
    haystack_tokens: set[str],
    threshold: float = DEFAULT_TITLE_MATCH_THRESHOLD,
) -> bool:
    """True when enough significant title tokens appear in `haystack_tokens`."""
    title_toks = significant_tokens(title)
    if not title_toks:
        return False
    present = sum(1 for tok in title_toks if tok in haystack_tokens)
    return (present / len(title_toks)) >= threshold


def normalize_isbn(value: object) -> str:
    """Normalize an ISBN to comparable form (digits + trailing X, uppercased)."""
    if not value:
        return ""
    return re.sub(r"[^0-9xX]", "", str(value)).upper()


# ---- Title variant generation ----

# Square-bracket content anywhere in the string: [Dramatized Adaptation], [Unabridged]
# Stripped first so downstream patterns see a cleaner string.
_RE_SQUARE_BRACKETS = re.compile(r"\s*\[[^\]]+\]")

# "(N of M)" part indicator — strips the parens AND everything that follows.
# Handles mid-string positions like "(1 of 2) [Adaptation] Series Name 2".
# Applied before _RE_PAREN_SERIES so it catches the common "Title (1 of 2) Series X" pattern.
_RE_PART_OF_M = re.compile(r"\s*\(\d+\s+of\s+\d+\).*$")

# Trailing parenthetical with series/volume/part markers.
# Use #\s*\d for hash-number patterns since # is not a word character and \b won't match around it.
_RE_PAREN_SERIES = re.compile(
    r"\s*\([^)]*(?:\b(?:book|vol\.?|volume|part)\b|#\s*\d)[^)]*\)\s*$",
    re.IGNORECASE,
)

# Bare hash-number suffix without parens: "#13", "# 5"
_RE_BARE_NUMBER = re.compile(r"\s+#\s*\d+\s*$")

# Bare volume suffix without a separator: "Book 9", "Volume 2", "Part III" at end of string.
# Lookbehind ensures the preceding character is alphanumeric so we don't eat a separator
# that belongs to a different pattern (e.g. ", Book 1" should be handled by _RE_VOLUME_SUFFIX).
_RE_BARE_VOLUME = re.compile(
    r"(?<=[a-zA-Z0-9])\s+(?:book|vol\.?|volume|part)\s+\S+\s*$",
    re.IGNORECASE,
)

# Comma/hyphen/colon volume suffix with explicit separator: ", Book 3", "- Volume II", ": Part 1 of 3"
_RE_VOLUME_SUFFIX = re.compile(
    r"\s*[,\-:]\s*(?:book|vol\.?|volume|part)\s+\S+(?:\s+of\s+\S+)?\s*$",
    re.IGNORECASE,
)

# Genre/marketing descriptor after colon: ": A Novel", ": A Gripping Thriller", ": A Dual Biography"
_RE_GENRE_SUBTITLE = re.compile(
    r"\s*:\s*(?:a|an)\s+(?:\w+\s+)?(?:novel|novella|memoir|thriller|mystery|romance|"
    r"adventure|epic|saga|chronicle|fantasy|story|tale|biography|autobiography|"
    r"collection|anthology)\s*$",
    re.IGNORECASE,
)

# Edition/reprint subtitle: ": 25th Anniversary Edition", ": Revised Edition", ": Illustrated Edition"
_RE_EDITION_SUBTITLE = re.compile(
    r"\s*:\s+(?:(?:\w+\s+)*)?(?:anniversary|revised|expanded|updated|illustrated|"
    r"deluxe|collector'?s?|special|complete|uncut|definitive|enhanced|restored|"
    r"original|critical)\s+edition\s*$",
    re.IGNORECASE,
)

# Long subtitle after colon — only fires when subtitle side has ≥4 words.
# This conservatively avoids stripping "Mistborn: The Final Empire" (3 words).
_RE_LONG_COLON_SUBTITLE = re.compile(r"\s*:\s+(?:\S+\s+){3}\S.*$")

# Em/en-dash subtitle separator
_RE_DASH_SUBTITLE = re.compile(r"\s*[–—]\s+.+$")

# Applied in order. _RE_SQUARE_BRACKETS runs first since stripping [..] may
# expose other patterns. _RE_LONG_COLON_SUBTITLE runs before _RE_VOLUME_SUFFIX
# so a title like "Shadows of Sparta: A Long Subtitle, Book 1" strips all the
# way to "Shadows of Sparta" in one pass rather than just removing ", Book 1".
_TITLE_STRIP_PATTERNS = (
    _RE_SQUARE_BRACKETS,
    _RE_PART_OF_M,
    _RE_PAREN_SERIES,
    _RE_BARE_NUMBER,
    _RE_BARE_VOLUME,
    _RE_LONG_COLON_SUBTITLE,
    _RE_GENRE_SUBTITLE,
    _RE_EDITION_SUBTITLE,
    _RE_VOLUME_SUFFIX,
    _RE_DASH_SUBTITLE,
)


def _strip_one_pass(text: str) -> str:
    """Apply the first matching strip pattern and return the cleaned string."""
    for pattern in _TITLE_STRIP_PATTERNS:
        candidate = pattern.sub("", text).strip()
        if candidate and candidate.lower() != text.lower() and len(candidate) >= 2:
            return candidate
    return text


def generate_title_search_variants(title: str) -> list[str]:
    """Return ordered search candidates from a book title.

    Applies strip patterns iteratively until stable, then returns
    ``[short_form, original]`` if anything was removed, else ``[original]``.
    The short form is tried first since indexers store the clean title.
    """
    if not title:
        return []
    original = " ".join(title.split())

    current = original
    for _ in range(6):
        nxt = _strip_one_pass(current)
        if nxt == current:
            break
        current = nxt

    if not significant_tokens(current) or current.lower() == original.lower():
        return [original]
    return [current, original]
