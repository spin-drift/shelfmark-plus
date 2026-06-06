"""Integration tests for multi-book flat-folder grouping via transfer_book_files.

Covers the real-world case from the screenshot: a torrent drops a flat mix of
chapter-level M4Bs (one book split into 33 files) and standalone M4Bs (other
books) into one directory. ABS needs one subfolder per book, not a flat pile.
"""

from pathlib import Path

import pytest

from shelfmark.core.models import DownloadTask
from shelfmark.download.postprocess.transfer import transfer_book_files


def _task(**kwargs) -> DownloadTask:
    defaults = dict(
        task_id="group-test",
        source="direct_download",
        title="Millennial Mage",
        author="Tess Irondale",
        format="m4b",
        content_type="audiobook",
    )
    return DownloadTask(**{**defaults, **kwargs})


def _write(path: Path, files: list[str]) -> list[Path]:
    paths = []
    for name in files:
        f = path / name
        f.write_bytes(b"audio")
        paths.append(f)
    return paths


class TestMultiBookFlatFolder:
    """Files from the screenshot: 33 chapter M4Bs + 2 standalone M4Bs."""

    def _chapter_files(self, directory: Path, count: int = 33) -> list[Path]:
        return _write(
            directory,
            [
                f"Bound Millennial Mage Book 4 [B0CGB1BNJP] - {i:02d} - Chapter {i}.m4b"
                for i in range(1, count + 1)
            ],
        )

    def _standalone_files(self, directory: Path) -> list[Path]:
        return _write(
            directory,
            [
                "Binding_Millennial_Mage.m4b",
                "2023_Book_6_Fused.m4b",
            ],
        )

    def test_chapter_files_land_in_shared_subfolder(self, tmp_path: Path, monkeypatch):
        """33 chapter files must all go into ONE subfolder, not scatter."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        chapter_files = self._chapter_files(source, count=33)
        standalone_files = self._standalone_files(source)
        all_files = chapter_files + standalone_files

        monkeypatch.setattr(
            "shelfmark.download.postprocess.transfer.get_template",
            lambda *, is_audiobook, organization_mode: "{Author}/{Title}",
        )

        final_paths, error, _ = transfer_book_files(
            all_files,
            destination=dest,
            task=_task(),
            use_hardlink=False,
            is_torrent=False,
            organization_mode="organize",
        )

        assert error is None

        # All 33 chapter files must share a single parent folder
        chapter_parents = {
            p.parent
            for p in final_paths
            if "Bound Millennial Mage" in str(p) or "Chapter" in p.name
        }
        assert len(chapter_parents) == 1, (
            f"Chapter files scattered across multiple folders: {chapter_parents}"
        )

    def test_standalone_files_each_get_own_subfolder(self, tmp_path: Path, monkeypatch):
        """Each standalone M4B must land in its own top-level subfolder under dest."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        chapter_files = self._chapter_files(source, count=5)
        standalone_files = self._standalone_files(source)
        all_files = chapter_files + standalone_files

        monkeypatch.setattr(
            "shelfmark.download.postprocess.transfer.get_template",
            lambda *, is_audiobook, organization_mode: "{Author}/{Title}",
        )

        final_paths, error, _ = transfer_book_files(
            all_files,
            destination=dest,
            task=_task(),
            use_hardlink=False,
            is_torrent=False,
            organization_mode="organize",
        )

        assert error is None

        # After grouping, dest contains one top-level subfolder per book group.
        # 5 chapter files → 1 group subfolder; 2 standalone files → 2 group subfolders = 3 total.
        top_level_dirs = [p for p in dest.iterdir() if p.is_dir()]
        assert len(top_level_dirs) == 3, (
            f"Expected 3 top-level book subfolders, got: {[d.name for d in top_level_dirs]}"
        )

    def test_total_output_count_matches_input(self, tmp_path: Path, monkeypatch):
        """No files should be lost or duplicated during grouping."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        all_files = self._chapter_files(source, count=10) + self._standalone_files(source)

        monkeypatch.setattr(
            "shelfmark.download.postprocess.transfer.get_template",
            lambda *, is_audiobook, organization_mode: "{Author}/{Title}",
        )

        final_paths, error, _ = transfer_book_files(
            all_files,
            destination=dest,
            task=_task(),
            use_hardlink=False,
            is_torrent=False,
            organization_mode="organize",
        )

        assert error is None
        assert len(final_paths) == len(all_files)

    def test_no_splitting_when_all_files_are_standalone(self, tmp_path: Path, monkeypatch):
        """Files with no chapter pattern → fall through to existing part-numbering, no splitting."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        # Names with no " - NN - " or " - Part NN" pattern
        files = _write(source, ["Part 01.mp3", "Part 02.mp3", "Part 03.mp3"])

        monkeypatch.setattr(
            "shelfmark.download.postprocess.transfer.get_template",
            lambda *, is_audiobook, organization_mode: "{Author}/{Title}",
        )

        final_paths, error, _ = transfer_book_files(
            files,
            destination=dest,
            task=_task(title="Project Hail Mary", author="Andy Weir"),
            use_hardlink=False,
            is_torrent=False,
            organization_mode="organize",
        )

        assert error is None
        assert len(final_paths) == 3
        # All should share the same parent (treated as one book)
        assert len({p.parent for p in final_paths}) == 1

    def test_rename_mode_also_groups(self, tmp_path: Path, monkeypatch):
        """Grouping fires in 'rename' mode too, not just 'organize'."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        chapter_files = self._chapter_files(source, count=3)
        standalone_files = _write(source, ["OtherBook.m4b"])
        all_files = chapter_files + standalone_files

        monkeypatch.setattr(
            "shelfmark.download.postprocess.transfer.get_template",
            lambda *, is_audiobook, organization_mode: "{Title}",
        )

        final_paths, error, _ = transfer_book_files(
            all_files,
            destination=dest,
            task=_task(),
            use_hardlink=False,
            is_torrent=False,
            organization_mode="rename",
        )

        assert error is None
        assert len(final_paths) == 4
        # Chapter group and standalone should be in different subdirectories
        all_parents = {p.parent for p in final_paths}
        assert len(all_parents) == 2

    def test_none_mode_skips_grouping(self, tmp_path: Path, monkeypatch):
        """Organization mode 'none' must never trigger grouping."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        all_files = self._chapter_files(source, count=3) + self._standalone_files(source)

        final_paths, error, _ = transfer_book_files(
            all_files,
            destination=dest,
            task=_task(),
            use_hardlink=False,
            is_torrent=False,
            organization_mode="none",
        )

        assert error is None
        # All files dumped flat into dest, no subfolders created
        assert all(p.parent == dest for p in final_paths)
