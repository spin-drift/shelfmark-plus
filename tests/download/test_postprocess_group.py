from pathlib import Path

import pytest

from shelfmark.download.postprocess.group import _book_prefix, group_book_files


class TestBookPrefix:
    def test_chapter_pattern(self):
        # "Title [ID] - 01 - Chapter Name" → "Title [ID]"
        stem = "Bound: Millennial Mage, Book 4 [B0CGB1BNJP] - 01 - Chapter 1"
        assert _book_prefix(stem) == "Bound: Millennial Mage, Book 4 [B0CGB1BNJP]"

    def test_chapter_pattern_large_number(self):
        stem = "Some Title - 33 - To listen to the next book"
        assert _book_prefix(stem) == "Some Title"

    def test_part_pattern_with_word(self):
        stem = "The Name of the Wind - Part 02"
        assert _book_prefix(stem) == "The Name of the Wind"

    def test_part_pattern_number_only(self):
        stem = "Dune - 03"
        assert _book_prefix(stem) == "Dune"

    def test_part_pattern_case_insensitive(self):
        stem = "Mistborn - PART 01"
        assert _book_prefix(stem) == "Mistborn"

    def test_standalone_no_pattern(self):
        # No chapter/part suffix — stem is its own key
        stem = "Binding_Millennial_Mage"
        assert _book_prefix(stem) == "Binding_Millennial_Mage"

    def test_standalone_with_underscored_dashes(self):
        # "2023_-_Book_6_-_Fused_{Tess_Irondale}" has _-_ not " - " so no match
        stem = "2023_-_Book_6_-_Fused_{Tess_Irondale}"
        assert _book_prefix(stem) == stem

    def test_empty_string(self):
        assert _book_prefix("") == ""


class TestGroupBookFiles:
    def _paths(self, *names: str) -> list[Path]:
        return [Path(f"/fake/{n}") for n in names]

    def test_single_group_chapters(self):
        files = self._paths(
            "Book Title - 01 - Chapter 1.m4b",
            "Book Title - 02 - Chapter 2.m4b",
            "Book Title - 03 - Chapter 3.m4b",
        )
        groups = group_book_files(files)
        assert len(groups) == 1
        assert "Book Title" in groups
        assert len(groups["Book Title"]) == 3

    def test_multiple_groups_mixed(self):
        files = self._paths(
            "Bound Millennial Mage Book 4 - 01 - Chapter 1.m4b",
            "Bound Millennial Mage Book 4 - 02 - Chapter 2.m4b",
            "Bound Millennial Mage Book 4 - 33 - Last Chapter.m4b",
            "Binding_Millennial_Mage.m4b",
            "2023_Book_6_Fused.m4b",
        )
        groups = group_book_files(files)
        assert len(groups) == 3
        assert len(groups["Bound Millennial Mage Book 4"]) == 3
        assert len(groups["Binding_Millennial_Mage"]) == 1
        assert len(groups["2023_Book_6_Fused"]) == 1

    def test_single_file(self):
        files = self._paths("Standalone Book.m4b")
        groups = group_book_files(files)
        assert len(groups) == 1

    def test_empty_list(self):
        groups = group_book_files([])
        assert groups == {}

    def test_all_standalone(self):
        files = self._paths("Book A.m4b", "Book B.m4b", "Book C.m4b")
        groups = group_book_files(files)
        assert len(groups) == 3
        for g in groups.values():
            assert len(g) == 1

    def test_preserves_insertion_order(self):
        files = self._paths(
            "Alpha - 01 - Intro.m4b",
            "Alpha - 02 - End.m4b",
            "Beta.m4b",
        )
        groups = group_book_files(files)
        keys = list(groups.keys())
        assert keys[0] == "Alpha"
        assert keys[1] == "Beta"
