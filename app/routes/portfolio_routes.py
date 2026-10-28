"""Portfolio pages: one shared home page, a gallery fragment, and the publications page."""

import re
from functools import partial
from pathlib import Path

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from markupsafe import Markup, escape

from app import portfolio

portfolio_bp = Blueprint("portfolio", __name__)

_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]*)\)")


def _content_dir() -> Path:
    return Path(current_app.config.get("PORTFOLIO_CONTENT_DIR", portfolio.CONTENT_DIR))


def _load():
    site = portfolio.load_site(_content_dir())
    return site, portfolio.load_projects(_content_dir(), site)


@portfolio_bp.app_template_filter("linkify")
def linkify(text):
    """Escape text, then turn [label](https://url) into links. Only http(s) and
    site-relative targets are accepted, so content cannot inject other schemes."""
    escaped = str(escape(text or ""))
    html = _LINK_RE.sub(
        lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener noreferrer">{m.group(1)}</a>',
        escaped,
    )
    return Markup(html)


@portfolio_bp.app_template_global()
def asset_url(path):
    """Static-relative paths go through url_for; full URLs pass through."""
    if not path:
        return None
    if path.startswith(("http://", "https://")):
        return path
    return url_for("static", filename=path)


def _home_context(site, projects, initial):
    return {
        "site": site,
        "shown": portfolio.filter_projects(projects, initial),
        "category": initial,
        "counts": portfolio.category_counts(projects, site["categories"]),
        "initial_visible": site["initial_visible"],
        "nav_base": request.path,  # anchors stay on the current route, keeping its filter
        "show_publications": bool(site["links"].get("publications")),
    }


def home_view(initial):
    site, projects = _load()
    return render_template(
        "home.html",
        publications=portfolio.load_publications(_content_dir()),
        **_home_context(site, projects, initial),
    )


@portfolio_bp.route("/_gallery")
def gallery_fragment():
    """Server-rendered gallery for the dropdown. The page URL never changes."""
    site, projects = _load()
    category = request.args.get("category", portfolio.ALL)
    if category != portfolio.ALL and category not in site["categories"]:
        abort(404)
    ctx = _home_context(site, projects, category)
    return render_template("_gallery.html", **ctx)


@portfolio_bp.route("/projects", defaults={"rest": ""})
@portfolio_bp.route("/projects/<path:rest>")
def projects_redirect(rest):
    """Projects no longer have their own pages; old URLs land on the gallery."""
    return redirect(url_for("portfolio.home") + "#projects", code=301)


@portfolio_bp.route("/publications")
def publications():
    site = portfolio.load_site(_content_dir())
    return render_template(
        "publications.html",
        site=site,
        publications=portfolio.load_publications(_content_dir()),
        nav_base=url_for("portfolio.home"),
        show_publications=True,
    )


def _register_home_routes():
    """One page, one view; each URL only differs in the initial filter."""
    site = portfolio.load_site()
    for path, category in site["route_filters"].items():
        endpoint = "home" if path == "/" else path.strip("/")
        portfolio_bp.add_url_rule(
            path, endpoint=endpoint, view_func=partial(home_view, category)
        )


_register_home_routes()


@portfolio_bp.app_errorhandler(404)
def not_found(_error):
    site = portfolio.load_site(_content_dir())
    return (
        render_template(
            "404.html",
            site=site,
            nav_base=url_for("portfolio.home"),
            show_publications=bool(site["links"].get("publications")),
        ),
        404,
    )
