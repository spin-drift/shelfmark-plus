import pytest

from shelfmark.core.text_match import (
    DEFAULT_TITLE_MATCH_THRESHOLD,
    author_surname,
    normalize_isbn,
    significant_tokens,
    title_tokens_match,
    tokens,
)


class TestTokens:
    def test_basic_split(self):
        assert tokens("Hello World") == ["hello", "world"]

    def test_strips_punctuation(self):
        assert tokens("it's a test!") == ["it", "s", "a", "test"]

    def test_none_returns_empty(self):
        assert tokens(None) == []

    def test_empty_string_returns_empty(self):
        assert tokens("") == []

    def test_numbers_preserved(self):
        assert "2001" in tokens("2001: A Space Odyssey")


class TestSignificantTokens:
    def test_removes_stopwords(self):
        result = significant_tokens("The Lord of the Rings")
        assert "the" not in result
        assert "of" not in result
        assert "lord" in result
        assert "rings" in result

    def test_removes_single_char_tokens(self):
        result = significant_tokens("A Brief History")
        assert "a" not in result
        assert "brief" in result

    def test_none_returns_empty(self):
        assert significant_tokens(None) == []


class TestAuthorSurname:
    def test_last_first_format(self):
        assert author_surname("Shelley, Mary") == "shelley"

    def test_first_last_format(self):
        assert author_surname("Mary Shelley") == "shelley"

    def test_single_name(self):
        assert author_surname("Homer") == "homer"

    def test_none_returns_none(self):
        assert author_surname(None) is None

    def test_empty_returns_none(self):
        assert author_surname("") is None


class TestTitleTokensMatch:
    def test_exact_match(self):
        haystack = set(significant_tokens("Frankenstein or The Modern Prometheus"))
        assert title_tokens_match("Frankenstein", haystack) is True

    def test_no_match(self):
        haystack = set(significant_tokens("Moby Dick"))
        assert title_tokens_match("Frankenstein", haystack) is False

    def test_partial_match_above_threshold(self):
        haystack = set(["lord", "rings", "fellowship"])
        assert title_tokens_match("Lord of the Rings", haystack, threshold=0.5) is True

    def test_partial_match_below_threshold(self):
        haystack = set(["lord"])
        assert title_tokens_match("Lord of the Rings", haystack, threshold=0.85) is False

    def test_empty_title_returns_false(self):
        assert title_tokens_match("", {"anything"}) is False

    def test_none_title_returns_false(self):
        assert title_tokens_match(None, {"anything"}) is False

    def test_default_threshold(self):
        assert DEFAULT_TITLE_MATCH_THRESHOLD == 0.85


class TestNormalizeIsbn:
    def test_strips_hyphens(self):
        assert normalize_isbn("978-0-06-112008-4") == "9780061120084"

    def test_uppercases_x(self):
        assert normalize_isbn("0-306-40615-x") == "030640615X"

    def test_already_clean(self):
        assert normalize_isbn("9780061120084") == "9780061120084"

    def test_none_returns_empty(self):
        assert normalize_isbn(None) == ""

    def test_empty_returns_empty(self):
        assert normalize_isbn("") == ""
