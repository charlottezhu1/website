"""The real content in content/ must be consistent and honest."""

import re

import pytest

from app import portfolio
from tests.conftest import static_path

JOB_TITLE_CATEGORIES = {"apm", "pm", "swe", "sde", "engineer", "researcher"}
VISIBLE_FIELDS = ("title", "description", "role", "outcome")


def test_content_loads_and_validates(projects):
    assert len(projects) >= 5, "the gallery needs a few projects to look like a portfolio"


def test_archived_projects_are_not_published(projects):
    """content/archive holds parked projects; only content/projects is loaded."""
    archived = {f.stem for f in (portfolio.CONTENT_DIR / "archive").glob("*.yaml")}
    assert archived, "expected parked projects in content/archive"
    assert not archived & {p.slug for p in projects}


def test_slugs_unique(projects):
    slugs = [p.slug for p in projects]
    assert len(slugs) == len(set(slugs))


def test_categories_are_topics_not_job_titles(site):
    assert not (set(site["categories"]) & JOB_TITLE_CATEGORIES)


def test_every_route_filter_targets_a_real_category(site):
    for route, category in site["route_filters"].items():
        assert category == "all" or category in site["categories"], route


def test_required_routes_are_configured(site):
    assert site["route_filters"]["/"] == "all"
    assert site["route_filters"]["/apm"] == "product"
    assert site["route_filters"]["/engineering"] == "engineering"
    assert site["route_filters"]["/research"] == "research"


def test_every_route_filter_has_projects(site, projects):
    for route, category in site["route_filters"].items():
        assert portfolio.filter_projects(projects, category), f"{route} would show an empty gallery"


def test_local_assets_exist(site, projects):
    refs = [site.get("photo"), site["links"].get("resume")]
    for p in projects:
        refs += [p.thumbnail, *p.links.values()]
    missing = [r for r in refs if r and static_path(r) is not None and not static_path(r).exists()]
    assert not missing, f"referenced files not found under app/static: {missing}"


def test_external_links_are_https(projects):
    for p in projects:
        for label, target in p.external_links:
            if target.startswith("http"):
                assert target.startswith("https://"), f"{p.slug} {label} is not https"


def test_cards_are_scannable(projects):
    for p in projects:
        assert len(p.title) <= 80, f"{p.slug}: title too long for a card"
        assert len(p.description) <= 160, f"{p.slug}: one-line description too long"
        assert "\n" not in p.description


def test_real_projects_have_no_todo_in_visible_fields(projects):
    for p in projects:
        if p.placeholder:
            continue
        for field in VISIBLE_FIELDS:
            value = getattr(p, field) or ""
            assert "TODO" not in value, f"{p.slug}.{field} still has a TODO"


def test_placeholders_say_so(projects):
    for p in projects:
        if p.placeholder:
            assert p.description.lower().startswith("placeholder"), p.slug


def test_every_project_links_to_something_to_read(projects):
    """Cards have no detail pages, so each one must point to a paper, repo, report, or slides."""
    for p in projects:
        assert p.external_links, f"{p.slug} has no external link, so its card is a dead end"


def test_no_invented_metrics_in_placeholders(projects):
    """Placeholders must not carry numbers, outcomes or technologies nobody supplied."""
    for p in projects:
        if p.placeholder:
            assert not p.outcome and not p.technologies and not p.year, p.slug


def test_years_are_plausible(projects):
    for p in projects:
        if p.year:
            assert 2015 <= p.year <= 2030, p.slug


def test_publications_are_complete():
    pubs = portfolio.load_publications()
    assert pubs
    for pub in pubs:
        assert re.fullmatch(r"\d{4}", str(pub["year"]))
        assert pub["authors"] and pub["venue"]
        if pub.get("link"):
            ref = pub["link"]
            local = static_path(ref)
            assert local is None or local.exists(), ref
