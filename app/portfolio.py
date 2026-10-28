"""Portfolio content loading and gallery logic.

Everything here is plain Python/YAML with no Supabase or Flask dependency, so the
filtering rules can be tested in isolation. Content lives in ``content/``:

* ``content/site.yaml``           intro, about, interests, categories, route filters
* ``content/projects/<slug>.yaml`` one canonical file per project
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
ALL = "all"

# Order and labels for the external links shown on each card. The label says what the
# link leads to, so a visitor knows before clicking.
LINK_LABELS = {
    "paper": "Paper",
    "preprint": "Preprint",
    "report": "Report",
    "poster": "Poster",
    "slides": "Slides",
    "github": "GitHub",
    "demo": "Demo",
    "website": "Website",
    "writeup": "Write-up",
    "prototype": "Prototype",
}

DEFAULT_PRIORITY = 100
THUMBNAIL_FITS = {"cover", "contain"}


class ContentError(ValueError):
    """Raised when a content file is missing a field or is inconsistent."""


@dataclass
class Project:
    slug: str
    title: str
    description: str
    categories: list[str]
    year: int | None = None
    technologies: list[str] = field(default_factory=list)
    thumbnail: str | None = None
    thumbnail_fit: str = "cover"  # "cover" fills the frame; "contain" shows the whole image
    role: str | None = None
    outcome: str | None = None
    links: dict[str, str] = field(default_factory=dict)
    priority: int = DEFAULT_PRIORITY
    placeholder: bool = False

    @property
    def external_links(self) -> list[tuple[str, str]]:
        """(label, target) pairs in a stable order, skipping empty values."""
        return [
            (LINK_LABELS[key], self.links[key])
            for key in LINK_LABELS
            if self.links.get(key)
        ]


# ---------------------------------------------------------------- loading


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ContentError(f"{path.name}: expected a mapping at the top level")
    return data


def load_publications(content_dir: Path = CONTENT_DIR) -> list[dict[str, Any]]:
    path = Path(content_dir) / "publications.yaml"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or []
    for i, pub in enumerate(data):
        for key in ("title", "authors", "venue", "year"):
            if not pub.get(key):
                raise ContentError(f"publications.yaml entry {i + 1}: missing '{key}'")
    return data


def load_site(content_dir: Path = CONTENT_DIR) -> dict[str, Any]:
    site = _read_yaml(Path(content_dir) / "site.yaml")
    for key in ("name", "categories", "route_filters"):
        if key not in site:
            raise ContentError(f"site.yaml: missing '{key}'")
    site.setdefault("initial_visible", 6)
    for path, category in site["route_filters"].items():
        if category != ALL and category not in site["categories"]:
            raise ContentError(
                f"site.yaml: route {path} filters on unknown category '{category}'"
            )
    return site


def _build_project(path: Path, categories: dict[str, str]) -> Project:
    data = _read_yaml(path)
    for key in ("slug", "title", "description", "categories"):
        if not data.get(key):
            raise ContentError(f"{path.name}: missing required field '{key}'")
    if data["slug"] != path.stem:
        raise ContentError(
            f"{path.name}: slug '{data['slug']}' must match the file name"
        )
    unknown = [c for c in data["categories"] if c not in categories]
    if unknown:
        raise ContentError(f"{path.name}: unknown categories {unknown}")
    fit = data.get("thumbnail_fit", "cover")
    if fit not in THUMBNAIL_FITS:
        raise ContentError(f"{path.name}: thumbnail_fit must be one of {sorted(THUMBNAIL_FITS)}")
    unknown_links = [k for k in (data.get("links") or {}) if k not in LINK_LABELS]
    if unknown_links:
        raise ContentError(f"{path.name}: unknown link types {unknown_links}")
    return Project(
        slug=data["slug"],
        title=data["title"],
        description=data["description"],
        categories=list(data["categories"]),
        year=data.get("year"),
        technologies=list(data.get("technologies") or []),
        thumbnail=data.get("thumbnail"),
        thumbnail_fit=fit,
        role=data.get("role"),
        outcome=data.get("outcome"),
        links={k: v for k, v in (data.get("links") or {}).items() if v},
        priority=data.get("priority", DEFAULT_PRIORITY),
        placeholder=bool(data.get("placeholder", False)),
    )


def load_projects(
    content_dir: Path = CONTENT_DIR, site: dict[str, Any] | None = None
) -> list[Project]:
    content_dir = Path(content_dir)
    site = site or load_site(content_dir)
    files = sorted((content_dir / "projects").glob("*.yaml"))
    projects = [_build_project(f, site["categories"]) for f in files]
    slugs = [p.slug for p in projects]
    if len(slugs) != len(set(slugs)):
        raise ContentError("duplicate project slugs")
    return sort_projects(projects)


# ---------------------------------------------------------------- filtering


def sort_key(project: Project) -> tuple:
    """Lower priority number first, then newest year, then title (fully deterministic)."""
    return (project.priority, -(project.year or 0), project.title.lower(), project.slug)


def sort_projects(projects: list[Project]) -> list[Project]:
    return sorted(projects, key=sort_key)


def filter_projects(projects: list[Project], category: str) -> list[Project]:
    """Projects whose ``categories`` include ``category``; everything for ``all``."""
    if category == ALL:
        return sort_projects(projects)
    return sort_projects([p for p in projects if category in p.categories])


def category_counts(projects: list[Project], categories: dict[str, str]) -> dict[str, int]:
    counts = {ALL: len(projects)}
    for cat in categories:
        counts[cat] = sum(1 for p in projects if cat in p.categories)
    return counts
