"""Pure logic: filtering, ordering, featured split, content validation."""

import random
from pathlib import Path

import pytest

from app import portfolio
from app.portfolio import (
    ALL,
    ContentError,
    Project,
    category_counts,
    filter_projects,
    sort_projects,
)


def P(slug, cats, year=None, priority=None, title=None):
    kwargs = {} if priority is None else {"priority": priority}
    return Project(slug=slug, title=title or slug, description="d", categories=cats, year=year, **kwargs)


SAMPLE = [
    P("a", ["product", "engineering"], 2023, 1),
    P("b", ["ai"], 2025, 2),
    P("c", ["engineering", "ai"], 2024, 3),
    P("d", ["research"], 2022, 4),
    P("e", ["product"], 2025, 5),
    P("f", ["design", "creative"], 2021, 6),
]


def slugs(projects):
    return [p.slug for p in projects]


class TestFiltering:
    def test_all_returns_every_project(self):
        assert sorted(slugs(filter_projects(SAMPLE, ALL))) == sorted(slugs(SAMPLE))

    def test_multi_category_project_appears_under_each_category(self):
        assert "a" in slugs(filter_projects(SAMPLE, "product"))
        assert "a" in slugs(filter_projects(SAMPLE, "engineering"))

    def test_ai_only_project_is_not_in_engineering(self):
        assert "b" not in slugs(filter_projects(SAMPLE, "engineering"))
        assert "c" in slugs(filter_projects(SAMPLE, "engineering"))

    def test_unknown_category_returns_nothing(self):
        assert filter_projects(SAMPLE, "no-such-category") == []

    def test_filtering_does_not_mutate_input(self):
        before = slugs(SAMPLE)
        filter_projects(SAMPLE, "product")
        assert slugs(SAMPLE) == before


class TestOrdering:
    def test_lower_priority_number_first(self):
        assert slugs(sort_projects([P("x", ["ai"], priority=9), P("y", ["ai"], priority=1)])) == ["y", "x"]

    def test_same_priority_newest_year_first(self):
        out = sort_projects([P("old", ["ai"], 2020, 1), P("new", ["ai"], 2025, 1)])
        assert slugs(out) == ["new", "old"]

    def test_then_title_alphabetical(self):
        out = sort_projects([P("z", ["ai"], 2024, 1, title="Zebra"), P("a", ["ai"], 2024, 1, title="apple")])
        assert slugs(out) == ["a", "z"]

    def test_missing_priority_sorts_after_explicit(self):
        out = sort_projects([P("none", ["ai"], 2025), P("set", ["ai"], 2000, 50)])
        assert slugs(out) == ["set", "none"]

    def test_missing_year_sorts_last_within_priority(self):
        out = sort_projects([P("noyear", ["ai"], None, 1), P("year", ["ai"], 2010, 1)])
        assert slugs(out) == ["year", "noyear"]

    def test_order_is_deterministic_regardless_of_input_order(self):
        base = [P(f"p{i}", ["ai"], 2020 + i % 3, i % 4) for i in range(12)]
        expected = slugs(sort_projects(base))
        for seed in range(5):
            shuffled = base[:]
            random.Random(seed).shuffle(shuffled)
            assert slugs(sort_projects(shuffled)) == expected


class TestCounts:
    def test_counts(self):
        counts = category_counts(SAMPLE, {"product": "Product", "ai": "AI", "design": "Design"})
        assert counts == {ALL: 6, "product": 2, "ai": 2, "design": 1}


class TestContentValidation:
    def write(self, tmp_path, project_yaml, site_extra=""):
        (tmp_path / "projects").mkdir()
        (tmp_path / "site.yaml").write_text(
            "name: T\ncategories: {product: Product, ai: AI}\n"
            "route_filters: {'/': all, '/apm': product}\n" + site_extra
        )
        (tmp_path / "projects" / "x.yaml").write_text(project_yaml)
        return tmp_path

    def test_valid_minimal_project(self, tmp_path):
        d = self.write(tmp_path, "slug: x\ntitle: X\ndescription: d\ncategories: [ai]\n")
        assert slugs(portfolio.load_projects(d)) == ["x"]

    @pytest.mark.parametrize("missing", ["slug", "title", "description", "categories"])
    def test_required_fields(self, tmp_path, missing):
        fields = {"slug": "x", "title": "X", "description": "d", "categories": "[ai]"}
        del fields[missing]
        d = self.write(tmp_path, "".join(f"{k}: {v}\n" for k, v in fields.items()))
        with pytest.raises(ContentError, match=missing):
            portfolio.load_projects(d)

    def test_slug_must_match_filename(self, tmp_path):
        d = self.write(tmp_path, "slug: other\ntitle: X\ndescription: d\ncategories: [ai]\n")
        with pytest.raises(ContentError, match="slug"):
            portfolio.load_projects(d)

    def test_unknown_category_rejected(self, tmp_path):
        d = self.write(tmp_path, "slug: x\ntitle: X\ndescription: d\ncategories: [wizardry]\n")
        with pytest.raises(ContentError, match="unknown categories"):
            portfolio.load_projects(d)

    def test_thumbnail_fit_defaults_to_cover_and_is_validated(self, tmp_path):
        d = self.write(tmp_path, "slug: x\ntitle: X\ndescription: d\ncategories: [ai]\n")
        assert portfolio.load_projects(d)[0].thumbnail_fit == "cover"
        (d / "projects" / "x.yaml").write_text("slug: x\ntitle: X\ndescription: d\ncategories: [ai]\nthumbnail_fit: stretch\n")
        with pytest.raises(ContentError, match="thumbnail_fit"):
            portfolio.load_projects(d)

    def test_unknown_link_type_rejected(self, tmp_path):
        d = self.write(tmp_path, "slug: x\ntitle: X\ndescription: d\ncategories: [ai]\nlinks: {fax: 'x'}\n")
        with pytest.raises(ContentError, match="link types"):
            portfolio.load_projects(d)

    def test_route_filter_must_name_known_category(self, tmp_path):
        d = self.write(tmp_path, "slug: x\ntitle: X\ndescription: d\ncategories: [ai]\n")
        (d / "site.yaml").write_text("name: T\ncategories: {ai: AI}\nroute_filters: {'/x': nope}\n")
        with pytest.raises(ContentError, match="unknown category"):
            portfolio.load_site(d)

    def test_links_are_ordered_and_empty_ones_skipped(self):
        proj = Project("x", "X", "d", ["ai"], links={"github": "g", "paper": "p", "demo": ""})
        assert [label for label, _ in proj.external_links] == ["Paper", "GitHub"]

    def test_link_labels_say_what_they_lead_to(self):
        links = {k: "u" for k in portfolio.LINK_LABELS}
        labels = [label for label, _ in Project("x", "X", "d", ["ai"], links=links).external_links]
        assert labels[:3] == ["Paper", "Preprint", "Report"], "papers come before code and demos"
        assert {"GitHub", "Slides", "Poster", "Website", "Write-up"} <= set(labels)
