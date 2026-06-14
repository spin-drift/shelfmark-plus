from shelfmark.core.search_plan import build_release_search_plan
from shelfmark.metadata_providers import BookMetadata


class TestReleaseSearchPlan:
    def test_uses_default_languages_when_none(self, monkeypatch):
        # config.BOOK_LANGUAGE is a Config attribute; patch the instance.
        import shelfmark.core.search_plan as sp

        monkeypatch.setattr(sp.config, "BOOK_LANGUAGE", ["en", "hu"], raising=False)

        book = BookMetadata(
            provider="hardcover",
            provider_id="123",
            title="Mistborn: The Final Empire",
            search_title="The Final Empire",
            search_author="Brandon Sanderson",
            authors=["Brandon Sanderson"],
            titles_by_language={
                "en": "Mistborn: The Final Empire",
                "hu": "A végső birodalom",
            },
            isbn_13="9780765311788",
        )

        plan = build_release_search_plan(book, languages=None)

        assert plan.languages == ["en", "hu"]
        assert plan.isbn_candidates == ["9780765311788"]
        assert [v.query for v in plan.title_variants] == [
            "The Final Empire Brandon Sanderson",
            "A végső birodalom Brandon Sanderson",
        ]

        # Title-only variants are used by some sources (e.g. Prowlarr).
        assert [v.title for v in plan.title_variants] == [
            "The Final Empire",
            "A végső birodalom",
        ]

        assert [(v.title, v.languages) for v in plan.grouped_title_variants] == [
            ("The Final Empire", ["en"]),
            ("A végső birodalom", ["hu"]),
        ]

    def test_all_language_disables_grouping(self, monkeypatch):
        import shelfmark.core.search_plan as sp

        monkeypatch.setattr(sp.config, "BOOK_LANGUAGE", ["en"], raising=False)

        book = BookMetadata(
            provider="hardcover",
            provider_id="123",
            title="The Lightning Thief",
            authors=["Rick Riordan"],
            titles_by_language={"hu": "A villámtolvaj"},
        )

        plan = build_release_search_plan(book, languages=["all"])

        assert plan.languages is None
        assert [v.query for v in plan.title_variants] == [
            "The Lightning Thief Rick Riordan",
        ]
        assert [v.title for v in plan.title_variants] == [
            "The Lightning Thief",
        ]
        assert [(v.title, v.languages) for v in plan.grouped_title_variants] == [
            ("The Lightning Thief", None),
        ]

    def test_strippable_title_appends_full_form_as_fallback_variant(self, monkeypatch):
        import shelfmark.core.search_plan as sp

        monkeypatch.setattr(sp.config, "BOOK_LANGUAGE", ["en"], raising=False)

        # Simulates a book from a provider that doesn't pre-compute search_title
        book = BookMetadata(
            provider="openlibrary",
            provider_id="OL1",
            title="Dune (Dune Chronicles, #1)",
            authors=["Frank Herbert"],
        )
        plan = build_release_search_plan(book, languages=None)

        queries = [v.query for v in plan.title_variants]
        # First variant: clean short form
        assert queries[0] == "Dune Frank Herbert"
        # Last variant: full original with parenthetical
        assert queries[-1] == "Dune (Dune Chronicles, #1) Frank Herbert"
        assert len(queries) >= 2

        # grouped_title_variants (used by Anna's Archive) must also include the full fallback
        grouped_queries = [v.query for v in plan.grouped_title_variants]
        assert grouped_queries[0] == "Dune Frank Herbert"
        assert grouped_queries[-1] == "Dune (Dune Chronicles, #1) Frank Herbert"

    def test_no_extra_variant_when_title_not_strippable(self, monkeypatch):
        import shelfmark.core.search_plan as sp

        monkeypatch.setattr(sp.config, "BOOK_LANGUAGE", ["en"], raising=False)

        book = BookMetadata(
            provider="openlibrary",
            provider_id="OL2",
            title="Dune",
            authors=["Frank Herbert"],
        )
        plan = build_release_search_plan(book, languages=None)

        queries = [v.query for v in plan.title_variants]
        # No stripping happened — only one variant
        assert queries == ["Dune Frank Herbert"]
