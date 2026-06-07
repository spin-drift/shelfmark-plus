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

# Trailing parenthetical containing series/volume markers: "(Dune Chronicles, #1)", "(Book 3)"
# Use #\s*\d for hash-number patterns since # is not a word character and \b won't match around it.
_RE_PAREN_SERIES = re.compile(
    r"\s*\([^)]*(?:\b(?:book|vol\.?|volume|part)\b|#\s*\d)[^)]*\)\s*$",
    re.IGNORECASE,
)

# Comma/hyphen/colon volume suffix: ", Book 3", "- Volume II", ": Part 1"
_RE_VOLUME_SUFFIX = re.compile(
    r"\s*[,\-:]\s*(?:book|vol\.?|volume|part)\s+\S+\s*$",
    re.IGNORECASE,
)

# Genre/marketing descriptor after colon: ": A Novel", ": A Gripping Thriller"
_RE_GENRE_SUBTITLE = re.compile(
    r"\s*:\s*(?:a|an)\s+(?:\w+\s+)?(?:novel|novella|memoir|thriller|mystery|romance|"
    r"adventure|epic|saga|chronicle|fantasy|story|tale)\s*$",
    re.IGNORECASE,
)

# Long subtitle after colon — only fires when subtitle side has ≥4 words.
# This conservatively avoids stripping "Mistborn: The Final Empire" (3 words).
_RE_LONG_COLON_SUBTITLE = re.compile(r"\s*:\s+(?:\S+\s+){3}\S.*$")

# Em/en-dash subtitle separator
_RE_DASH_SUBTITLE = re.compile(r"\s*[–—]\s+.+$")

_TITLE_STRIP_PATTERNS = (
    _RE_PAREN_SERIES,
    _RE_VOLUME_SUFFIX,
    _RE_GENRE_SUBTITLE,
    _RE_LONG_COLON_SUBTITLE,
    _RE_DASH_SUBTITLE,
)


def generate_title_search_variants(title: str) -> list[str]:
    """Return ordered search candidates from a book title.

    Returns ``[short_form, original]`` when a strippable suffix is detected,
    or ``[original]`` when nothing meaningful can be removed. The short form
    is tried first since indexers store the clean title, not the full subtitle.
    """
    if not title:
        return []
    original = " ".join(title.split())
    for pattern in _TITLE_STRIP_PATTERNS:
        candidate = pattern.sub("", original).strip()
        if (
            candidate
            and candidate.lower() != original.lower()
            and len(candidate) >= 2
            and significant_tokens(candidate)
        ):
            return [candidate, original]
    return [original]
