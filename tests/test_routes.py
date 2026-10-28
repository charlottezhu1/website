"""URL-initialised filtering, shared layout, fragment endpoint, old project URLs."""

import re

import pytest

from app import portfolio
from tests.conftest import Page, make_app

FILTER_ROUTES = {"/": "all", "/apm": "product", "/engineering": "engineering", "/research": "research", "/design": "design"}


def card_slugs(page: Page):
    return [a["data-slug"] for t, a in page.elements if t == "li" and "data-slug" in a]


def selected_value(page: Page):
    options = [a for t, a in page.elements if t == "option"]
    selected = [o["value"] for o in options if "selected" in o]
    assert len(selected) == 1, "exactly one option must be selected"
    return selected[0]


def gallery_html(html: str) -> str:
    start = html.index('<div id="gallery"')
    end = html.index("</main>")
    return html[start:end]


def normalise(s: str) -> str:
    return re.sub(r"\s+", "", s)


@pytest.mark.parametrize("route,category", FILTER_ROUTES.items())
class TestInitialFilter:
    def test_route_renders(self, page, route, category):
        page(route)

    def test_dropdown_reflects_route(self, page, route, category):
        assert selected_value(page(route)) == category

    def test_gallery_declares_category(self, page, route, category):
        assert any(a.get("data-category") == category for t, a in page(route).elements if t == "div" and a.get("id") == "gallery")

    def test_cards_match_filter_logic(self, page, projects, site, route, category):
        expected = [p.slug for p in portfolio.filter_projects(projects, category)]
        assert sorted(card_slugs(page(route))) == sorted(expected)

    def test_cards_are_in_priority_order(self, page, projects, route, category):
        expected = [x.slug for x in portfolio.filter_projects(projects, category)]
        assert card_slugs(page(route)) == expected

    def test_there_is_one_projects_list_no_featured_split(self, page, route, category):
        html = page(route).html
        assert html.count('class="project-grid') == 1
        assert "Featured" not in html and "All Projects" not in html

    def test_no_project_appears_twice(self, page, route, category):
        slugs = card_slugs(page(route))
        assert len(slugs) == len(set(slugs))


def test_all_routes_share_one_page_structure(page):
    structures = []
    for route in FILTER_ROUTES:
        p = page(route)
        structures.append((sorted(p.ids() - {"gallery-status", "all-projects", "show-more"}), [h for h in p.headings if h[0] == 2]))
    assert all(s == structures[0] for s in structures)


def test_unknown_route_is_404(page):
    p = page("/does-not-exist", status=404)
    assert "not found" in p.visible_text.lower()


def test_old_research_page_moved_to_publications(page):
    p = page("/publications")
    assert any(level == 1 and text == "Publications" for level, text in p.headings)


def test_navigation_anchors_stay_on_current_route(page):
    """On /apm, 'About' must be /apm#about so the initial filter is not lost."""
    p = page("/apm")
    assert "/apm#about" in {a["href"] for a in p.anchors}


class TestFilterChangeIsClientSide:
    def test_dropdown_is_a_plain_select_with_no_navigation(self, page):
        p = page("/")
        select = next(a for t, a in p.elements if t == "select")
        assert not any(k.startswith("on") for k in select), "no inline handler may navigate"
        assert select["data-gallery-url"] == "/_gallery"
        form_ancestors = [t for t, _ in p.elements if t == "form"]
        assert not form_ancestors, "a form submit would reload the page"

    @pytest.mark.parametrize("route,category", FILTER_ROUTES.items())
    def test_fragment_equals_initial_render_for_same_category(self, client, route, category):
        """The dropdown (fragment) and the URL (full page) must never disagree."""
        fragment = client.get(f"/_gallery?category={category}").get_data(as_text=True)
        full = client.get(route).get_data(as_text=True)
        assert normalise(fragment) in normalise(full)

    def test_fragment_defaults_to_all(self, client):
        assert 'data-category="all"' in client.get("/_gallery").get_data(as_text=True)

    def test_fragment_rejects_unknown_category(self, client):
        assert client.get("/_gallery?category=nope").status_code == 404

    def test_fragment_is_not_a_full_page(self, client):
        assert "<html" not in client.get("/_gallery?category=ai").get_data(as_text=True)


class TestShowMore:
    def test_button_when_more_than_initial_visible(self, crowded_client):
        p = Page(crowded_client.get("/").get_data(as_text=True))
        assert [a for t, a in p.elements if t == "button" and a.get("id") == "show-more"]
        extra = [a for t, a in p.elements if t == "li" and "is-extra" in a.get("class", "")]
        assert extra, "cards beyond the initial count must be marked"

    def test_counts_in_button_match_hidden_cards(self, crowded_client):
        html = crowded_client.get("/").get_data(as_text=True)
        hidden = html.count("is-extra")
        assert f"Show more ({hidden})" in html

    def test_no_button_when_few_projects(self, page):
        assert not [a for t, a in page("/apm").elements if a.get("id") == "show-more"]

    def test_button_is_accessible(self, crowded_client):
        p = Page(crowded_client.get("/").get_data(as_text=True))
        button = next(a for t, a in p.elements if a.get("id") == "show-more")
        assert button["aria-controls"] == "project-list" and button["aria-expanded"] == "false"
        assert "project-list" in p.ids()

    def test_extras_are_not_hidden_by_markup(self, crowded_client):
        """Without JavaScript the full list must still be reachable."""
        p = Page(crowded_client.get("/").get_data(as_text=True))
        extras = [a for t, a in p.elements if "is-extra" in a.get("class", "")]
        assert extras
        for a in extras:
            assert "hidden" not in a and "display:none" not in a.get("style", "").replace(" ", "")


class TestEdgeCases:
    def test_zero_results_state(self, content_copy):
        import yaml

        site_file = content_copy / "site.yaml"
        data = yaml.safe_load(site_file.read_text())
        data["categories"]["empty"] = "Empty"
        data["route_filters"]["/empty"] = "empty"
        site_file.write_text(yaml.safe_dump(data))
        client = make_app(content_copy).test_client()
        html = client.get("/_gallery?category=empty").get_data(as_text=True)
        assert "No projects in this category yet" in html
        assert "Featured Projects" not in html and "show-more" not in html

    def test_minimal_project_renders_without_optional_fields(self, content_copy):
        (content_copy / "projects" / "bare.yaml").write_text(
            "slug: bare\ntitle: Bare Project\ndescription: Just the basics.\ncategories: [product]\npriority: 1\n"
        )
        html = make_app(content_copy).test_client().get("/").get_data(as_text=True)
        assert "Bare Project" in html
        text = Page(html).visible_text
        assert "None" not in text and "()" not in text

    def test_missing_thumbnail_uses_placeholder_visual(self, content_copy):
        (content_copy / "projects" / "bare.yaml").write_text(
            "slug: bare\ntitle: Bare\ndescription: d\ncategories: [product]\npriority: 1\n"
        )
        html = make_app(content_copy).test_client().get("/").get_data(as_text=True)
        assert "image-placeholder" in html

    def test_content_is_html_escaped(self, content_copy):
        (content_copy / "projects" / "bare.yaml").write_text(
            "slug: bare\ntitle: '<script>alert(1)</script>'\ndescription: d\ncategories: [product]\npriority: 1\n"
        )
        html = make_app(content_copy).test_client().get("/").get_data(as_text=True)
        assert "<script>alert(1)</script>" not in html


class TestOldProjectUrls:
    """Projects have no pages of their own, only labelled links on the card."""

    @pytest.mark.parametrize("path", ["/projects", "/projects/1", "/projects/lovesims", "/projects/anything/else"])
    def test_old_project_urls_land_on_the_gallery(self, client, path):
        r = client.get(path)
        assert r.status_code == 301 and r.headers["Location"].endswith("/#projects")

    def test_cards_do_not_link_to_internal_project_pages(self, page):
        assert not [a for a in page("/").links() if (a["href"] or "").startswith("/projects/")]

    def test_every_card_link_opens_a_labelled_external_target(self, page):
        html = page("/").html
        cards = Page(html[html.index('<div id="gallery"') : html.index('id="publications"')])
        labelled = [a for a in cards.links() if a["attrs"].get("aria-label")]
        assert labelled
        for a in labelled:
            assert a["attrs"]["target"] == "_blank" and a["attrs"]["aria-label"].startswith(a["text"])
