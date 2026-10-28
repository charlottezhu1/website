"""Shared fixtures. The portfolio is tested through a minimal Flask app, so the tests
need neither Supabase nor a settings.py (they also run in CI)."""

import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import portfolio  # noqa: E402
from app import create_portfolio_app  # noqa: E402

STATIC_DIR = ROOT / "app" / "static"


def make_app(content_dir=None):
    app = create_portfolio_app(content_dir)
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="session")
def site():
    return portfolio.load_site()


@pytest.fixture(scope="session")
def projects(site):
    return portfolio.load_projects(site=site)


@pytest.fixture()
def client():
    return make_app().test_client()


@pytest.fixture()
def content_copy(tmp_path):
    """A writable copy of the real content directory for scenario tests."""
    dest = tmp_path / "content"
    shutil.copytree(portfolio.CONTENT_DIR, dest)
    return dest


@pytest.fixture()
def crowded_client(content_copy):
    """Real content plus 6 synthetic projects (one a placeholder): enough to need Show more."""
    for i in range(6):
        extra = "placeholder: true\n" if i == 0 else ""
        (content_copy / "projects" / f"extra-{i}.yaml").write_text(
            f"slug: extra-{i}\ntitle: Extra {i}\ndescription: "
            + ("'Placeholder: extra.'" if i == 0 else "Extra project.")
            + f"\ncategories: [product]\npriority: {50 + i}\n{extra}"
        )
    return make_app(content_copy).test_client()


class Page:
    """Small HTML inspector on the stdlib parser (no extra test dependencies)."""

    def __init__(self, html: str):
        self.html = html
        self.elements = []  # (tag, attrs)
        self.text = []
        self.anchors = []  # dicts: href, text, attrs
        self.headings = []  # (level, text)
        self._open_anchor = None
        self._open_heading = None
        outer = self

        class P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                outer.elements.append((tag, attrs))
                if tag == "a":
                    outer._open_anchor = {"href": attrs.get("href"), "text": "", "attrs": attrs}
                if re.fullmatch(r"h[1-6]", tag):
                    outer._open_heading = [int(tag[1]), ""]

            def handle_endtag(self, tag):
                if tag == "a" and outer._open_anchor is not None:
                    outer._open_anchor["text"] = re.sub(r"\s+", " ", outer._open_anchor["text"]).strip()
                    outer.anchors.append(outer._open_anchor)
                    outer._open_anchor = None
                if re.fullmatch(r"h[1-6]", tag) and outer._open_heading is not None:
                    level, txt = outer._open_heading
                    outer.headings.append((level, re.sub(r"\s+", " ", txt).strip()))
                    outer._open_heading = None

            def handle_data(self, data):
                outer.text.append(data)
                if outer._open_anchor is not None:
                    outer._open_anchor["text"] += data
                if outer._open_heading is not None:
                    outer._open_heading[1] += data

        P().feed(html)

    def tags(self, name):
        return [a for t, a in self.elements if t == name]

    def ids(self):
        return {a["id"] for _, a in self.elements if "id" in a}

    @property
    def visible_text(self):
        return re.sub(r"\s+", " ", " ".join(self.text))

    def links(self, text=None):
        return [a for a in self.anchors if text is None or a["text"] == text]


@pytest.fixture()
def page(client):
    def get(path, status=200):
        response = client.get(path)
        assert response.status_code == status, f"{path} -> {response.status_code}"
        return Page(response.get_data(as_text=True))

    return get


def static_path(ref: str) -> Path | None:
    """Local file for a static-relative reference, or None for external URLs."""
    if ref.startswith(("http://", "https://")):
        return None
    return STATIC_DIR / ref
