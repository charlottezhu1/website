"""What a recruiter, hiring manager, or research lead expects from a new-grad portfolio.

These encode common review criteria (first impression, credibility, scannability,
accessibility, honesty, mobile, page weight) rather than implementation details. Gaps
that only the owner can fill (LinkedIn, photo) are marked xfail so they stay visible
without hiding real regressions.
"""

import re

import pytest

from app import portfolio
from tests.conftest import STATIC_DIR, Page, static_path

HOME_ROUTES = ["/", "/apm", "/engineering", "/research", "/design"]
JOB_TITLES = re.compile(r"product manager|software engineer|research engineer|researcher|\bAPM\b|\bSWE\b", re.I)
GENERIC_LINK_TEXT = {"here", "link", "click here", "read more", "more", "this", "page"}
LABELLED_LINK_TEXT = {"Slides", "Poster", "Paper", "Demo", "GitHub", "Write-up", "Prototype"}
FIRST_SCREEN = 4  # cards a visitor sees before scrolling
ROLE_WORDS = {"apm", "engineering", "research", "swe", "pm"}

content_gap = lambda why: pytest.mark.xfail(reason=f"needs content from owner: {why}", strict=True)


def all_pages(page, projects):
    paths = HOME_ROUTES + ["/publications"]
    return {path: page(path) for path in paths}


# ------------------------------------------------------------------ first impression


class TestFirstImpression:
    def test_name_is_the_single_h1_on_home(self, page, site):
        p = page("/")
        h1s = [t for level, t in p.headings if level == 1]
        assert h1s == [site["name"]]

    def test_intro_states_who_you_are_before_anything_else(self, page, site):
        html = page("/").html
        assert html.index(site["headline"]) < html.index('id="about"')
        assert site["affiliation"] in html

    def test_headline_does_not_pigeonhole_into_one_career_track(self, site):
        assert not JOB_TITLES.search(site["headline"])

    def test_section_order_matches_visitor_priorities(self, page):
        order = [t for level, t in page("/").headings if level == 2]
        assert order == ["About", "Projects", "Publications", "Fun Facts"]

    def test_about_is_brief(self, site):
        words = sum(len(re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", para).split()) for para in site["about"])
        assert words <= 220, f"About is {words} words; recruiters skim"

    def test_contact_options_are_in_the_intro_not_only_the_footer(self, page):
        html = page("/").html
        intro = html[html.index('id="intro"') : html.index('id="about"')]
        assert "email-link" in intro and "Resume" in intro and "GitHub" in intro

    def test_top_bar_has_no_resume_or_contact_item(self, page):
        for route in HOME_ROUTES:
            p = page(route)
            nav = p.html[p.html.index("<nav") : p.html.index("</nav>")]
            assert "Resume" not in nav and "Contact" not in nav, route
            assert 'id="contact"' not in p.html, f"{route}: Contact section should be gone"

    def test_no_role_switcher(self, page):
        for route in HOME_ROUTES:
            p = page(route)
            assert not [a for t, a in p.elements if a.get("role") in {"tab", "tablist"}]
            nav = {a["text"].lower() for a in p.links() if a["href"] and a["href"].split("#")[-1] in {"about", "projects", "publications", "fun-facts"}}
            assert not (nav & ROLE_WORDS)
            assert not [a for a in p.links() if a["href"] in {"/apm", "/engineering", "/design"}]

    def test_linkedin_is_listed(self, page):
        assert page("/").links("LinkedIn")

    def test_has_profile_photo(self, page, site):
        assert site.get("photo")


# ------------------------------------------------------------------ projects: the main event


class TestProjectsAreConvincing:
    def test_first_screenful_of_projects_is_real_work(self, projects):
        first = portfolio.filter_projects(projects, "all")[:FIRST_SCREEN]
        real = [p for p in first if not p.placeholder]
        assert len(real) >= len(first) - 1, "the first projects on / are mostly placeholders"

    @pytest.mark.parametrize("route", HOME_ROUTES)
    def test_first_projects_are_visual(self, route, projects, site):
        first = portfolio.filter_projects(projects, site["route_filters"][route])[:FIRST_SCREEN]
        with_image = [p for p in first if p.thumbnail]
        assert len(with_image) * 2 >= len(first), f"{route}: most of the first cards have no image"

    def test_every_real_project_shows_evidence(self, projects):
        """A link, a publication status, or a result: something a reader can verify."""
        for p in projects:
            if not p.placeholder:
                assert p.links or p.outcome, f"{p.slug} has no link or outcome"

    def test_paper_status_is_stated_honestly(self, projects):
        under_review = {"emotional-impact-prediction", "social-media-feed-elicitation", "llm-literacy-young-people"}
        for p in projects:
            if p.slug in under_review:
                assert "under review" in (p.outcome or "").lower()
                assert "published" not in (p.outcome or "").lower()

    def test_cards_show_title_description_and_tags(self, page):
        p = page("/")
        cards = [a for t, a in p.elements if t == "li" and "data-slug" in a]
        assert cards
        assert len(p.links()) > 0
        assert p.html.count('class="card-title"') == len(cards)
        assert p.html.count('class="card-description"') == len(cards)
        assert p.html.count('aria-label="Categories"') == len(cards)

    def test_placeholders_are_visibly_labelled(self, crowded_client):
        """crowded_client adds exactly one placeholder project to the real content."""
        html = crowded_client.get("/").get_data(as_text=True)
        assert html.count("badge-placeholder") == 1
        assert ">Placeholder<" in html

    def test_home_lists_publications_right_after_projects(self, page):
        for route in HOME_ROUTES:
            html = page(route).html
            i_gallery, i_pubs, i_fun = (html.index(f'id="{x}"') for x in ("gallery", "publications", "fun-facts"))
            assert i_gallery < i_pubs < i_fun, route
            text = Page(html).visible_text
            for pub in portfolio.load_publications():
                assert pub["title"].replace('"', "") in text.replace('"', ""), f"{route}: missing {pub['title']}"

    def test_publication_titles_are_the_links(self, page):
        p = page("/publications")
        linked = [pub for pub in portfolio.load_publications() if pub.get("link")]
        assert linked
        for pub in linked:
            title = pub["title"].replace('"', "")
            matches = [a for a in p.links() if a["text"].replace('"', "") == title]
            assert matches, f"title is not a link: {pub['title']}"
            assert matches[0]["attrs"].get("target") == "_blank"
        assert not [a for a in p.links() if a["text"] in {"DOI", "Slides", "Link"}], "no separate label links"

    def test_publications_page_lists_every_publication(self, page):
        text = page("/publications").visible_text
        for pub in portfolio.load_publications():
            assert pub["title"] in text.replace("&quot;", '"') or pub["title"].replace('"', "") in text


# ------------------------------------------------------------------ honesty


class TestNothingUnfinishedLeaksOut:
    def test_no_todo_lorem_or_example_text_on_any_page(self, page, projects):
        for path, p in all_pages(page, projects).items():
            text = p.visible_text
            for bad in ("TODO", "lorem ipsum", "example.com", "None"):
                assert bad.lower() not in text.lower(), f"{path} shows '{bad}'"

    def test_no_dead_supabase_hosts_referenced(self, page, projects):
        for path, p in all_pages(page, projects).items():
            assert "supabase.co" not in p.html, path


# ------------------------------------------------------------------ accessibility


class TestAccessibility:
    def test_document_basics(self, page, projects):
        for path, p in all_pages(page, projects).items():
            assert p.tags("html")[0].get("lang") == "en", path
            assert [a for a in p.tags("meta") if a.get("name") == "viewport"], path
            desc = [a for a in p.tags("meta") if a.get("name") == "description"]
            assert desc and 20 <= len(desc[0]["content"]) <= 200, path
            assert "<title>" in p.html and "</title>" in p.html

    def test_titles_are_unique_per_page_type(self, page, projects):
        titles = {}
        for path, p in all_pages(page, projects).items():
            if path in HOME_ROUTES:
                continue
            title = re.search(r"<title>(.*?)</title>", p.html, re.S).group(1).strip()
            assert title not in titles, f"{path} and {titles[title]} share a title"
            titles[title] = path

    def test_landmarks_and_skip_link(self, page, projects):
        for path, p in all_pages(page, projects).items():
            tags = {t for t, _ in p.elements}
            assert {"header", "nav", "main", "footer"} <= tags, path
            assert p.links()[0]["href"] == "#main", f"{path}: skip link must be first"
            assert "main" in p.ids()

    def test_exactly_one_h1_and_no_skipped_heading_levels(self, page, projects):
        for path, p in all_pages(page, projects).items():
            levels = [level for level, _ in p.headings]
            assert levels.count(1) == 1, path
            for prev, cur in zip(levels, levels[1:]):
                assert cur <= prev + 1, f"{path}: heading jumps from h{prev} to h{cur}"

    def test_images_have_alt_and_content_images_describe_themselves(self, page, projects):
        for path, p in all_pages(page, projects).items():
            for img in p.tags("img"):
                assert "alt" in img, f"{path}: image without alt"
        profile = [a for a in page("/").tags("img") if "profile-photo" in a.get("class", "")]
        assert profile and all(img["alt"].strip() for img in profile), "the profile photo needs real alt text"

    def test_dropdown_has_a_label(self, page):
        p = page("/")
        select = next(a for t, a in p.elements if t == "select")
        labels = [a for t, a in p.elements if t == "label"]
        assert any(l.get("for") == select["id"] for l in labels)

    def test_link_text_is_descriptive(self, page, projects):
        for path, p in all_pages(page, projects).items():
            for a in p.links():
                name = (a["attrs"].get("aria-label") or a["text"]).strip().lower()
                if a["attrs"].get("aria-hidden") == "true":
                    continue
                assert name, f"{path}: link {a['href']} has no accessible name"
                assert name not in GENERIC_LINK_TEXT, f"{path}: '{name}' is not descriptive"

    def test_repeated_link_labels_are_disambiguated(self, page):
        """Many cards each have a 'Slides' link; screen readers need the project name."""
        html = page("/").html
        p = Page(html[html.index('<div id="gallery"') : html.index('id="fun-facts"')])
        checked = 0
        for a in p.links():
            if a["text"] in LABELLED_LINK_TEXT:
                checked += 1
                label = a["attrs"].get("aria-label", "")
                assert label.startswith(a["text"]) and len(label) > len(a["text"]), a
        assert checked, "expected project cards with external links"

    def test_card_images_are_decorative_and_not_links(self, page):
        html = page("/").html
        cards = html[html.index('<div id="gallery"') : html.index('id="publications"')]
        assert 'class="card-image"' in cards and '<a class="card-image"' not in cards
        for img in Page(cards).tags("img"):
            assert img.get("alt") == "", "card images repeat the title next to them, so they are decorative"

    def test_new_tab_links_use_noopener(self, page, projects):
        for path, p in all_pages(page, projects).items():
            for a in p.links():
                if a["attrs"].get("target") == "_blank":
                    assert "noopener" in a["attrs"].get("rel", ""), f"{path}: {a['href']}"

    def test_internal_anchors_resolve(self, page, projects):
        for path, p in all_pages(page, projects).items():
            for a in p.links():
                href = a["href"] or ""
                if "#" in href and (href.startswith("#") or href.split("#")[0] in ("", path)):
                    assert href.split("#")[1] in p.ids(), f"{path}: {href}"

    def test_css_has_visible_focus_and_no_hover_only_content(self):
        css = (STATIC_DIR / "portfolio.css").read_text()
        assert ":focus-visible" in css
        for rule in re.findall(r":hover[^{]*\{([^}]*)\}", css):
            assert "display" not in rule and "visibility" not in rule, "content must not depend on hover"

    def test_show_more_is_a_real_button(self, crowded_client):
        p = Page(crowded_client.get("/").get_data(as_text=True))
        assert [t for t, a in p.elements if t == "button" and a.get("id") == "show-more"]
        assert not [a for t, a in p.elements if t in {"div", "span"} and a.get("id") == "show-more"]

    def test_status_is_announced_to_screen_readers(self, page):
        assert 'role="status"' in page("/").html


# ------------------------------------------------------------------ resume and contact


class TestResumeAndContact:
    def test_resume_file_exists_and_is_a_pdf(self, site):
        path = static_path(site["links"]["resume"])
        assert path.exists() and path.suffix == ".pdf" and path.stat().st_size > 10_000

    def test_resume_is_linked_from_the_intro(self, page):
        html = page("/").html
        intro = html[html.index('id="intro"') : html.index('id="about"')]
        assert "Resume (PDF)" in intro

    def test_email_is_shown_obfuscated_and_never_as_a_scrapable_address(self, page, site):
        email = site["links"]["email"]
        assert "[at]" in email, "keep the [at] form in site.yaml"
        for route in HOME_ROUTES:
            html = page(route).html
            assert email in html, f"{route}: visitors must be able to read the address"
            assert "@" + email.split("[at]")[1].strip() not in html, f"{route}: raw address leaked"
            assert "mailto:" not in html, f"{route}: a static mailto: link is scrapable"

    def test_email_link_is_upgraded_by_script(self):
        js = (STATIC_DIR / "portfolio.js").read_text()
        assert "email-link" in js and '"mailto:"' in js

    def test_every_page_links_home(self, page, projects):
        for path, p in all_pages(page, projects).items():
            hrefs = {a["href"] for a in p.links()}
            assert "/" in hrefs or any(h.endswith("#about") for h in hrefs), path


# ------------------------------------------------------------------ mobile and weight


class TestMobileAndWeight:
    def test_card_images_fill_their_frame(self):
        css = (STATIC_DIR / "portfolio.css").read_text()
        block = re.search(r"\.card-image img\s*\{([^}]*)\}", css).group(1)
        assert "object-fit: cover" in block

    def test_card_image_frames_have_one_fixed_shape(self):
        """An image taller than 16:10 must not stretch its card (it did, for Sabotage & Spice)."""
        css = (STATIC_DIR / "portfolio.css").read_text()
        block = re.search(r"\.card-image\s*\{([^}]*)\}", css).group(1)
        assert "aspect-ratio: 16 / 10" in block and "overflow: hidden" in block
        img = re.search(r"\.card-image img,\s*\.image-placeholder\s*\{([^}]*)\}", css).group(1)
        assert "position: absolute" in img

    def test_whole_image_option_renders_for_research_diagrams(self, page):
        html = page("/").html
        for slug in ("lovesims", "emotional-impact-prediction", "vera"):
            card = html[html.index(f'data-slug="{slug}"') :]
            assert 'class="fit-contain"' in card[: card.index("</li>")], slug

    def test_css_is_responsive(self):
        css = (STATIC_DIR / "portfolio.css").read_text()
        assert "@media (max-width" in css and "grid-template-columns: 1fr" in css

    def test_buttons_set_text_color_with_their_background(self):
        """style.css gives every button white text; a light background would hide the label."""
        css = (STATIC_DIR / "portfolio.css").read_text()
        for selector in (".show-more",):
            block = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css).group(1)
            assert "background" in block and re.search(r"(^|[;\s])color:", block), f"{selector} needs an explicit color"

    def test_tap_targets_are_at_least_40px(self):
        css = (STATIC_DIR / "portfolio.css").read_text()
        assert css.count("min-height: 40px") >= 2  # dropdown and Show more

    def test_thumbnails_are_web_sized(self, projects):
        for p in projects:
            for ref in ([p.thumbnail] if p.thumbnail else []) :
                path = static_path(ref)
                if path:
                    assert path.stat().st_size <= 600_000, f"{ref} is {path.stat().st_size // 1000} KB"

    def test_below_the_fold_images_are_lazy_loaded(self, page):
        for img in page("/").tags("img"):
            if "profile-photo" in img.get("class", ""):
                assert img.get("loading") != "lazy", "the hero photo is above the fold"
            else:
                assert img.get("loading") == "lazy"

    def test_profile_photo_is_web_sized(self, site):
        path = static_path(site["photo"])
        assert path.exists() and path.stat().st_size <= 150_000, "profile photo is too heavy"

    def test_only_expected_third_party_hosts(self, page):
        allowed = ("fonts.googleapis.com", "fonts.gstatic.com")
        for t, a in page("/").elements:
            for attr in ("src", "href"):
                value = a.get(attr, "")
                if t in {"script", "link", "img"} and value.startswith("http"):
                    assert any(h in value for h in allowed), value
