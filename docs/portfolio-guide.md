# Portfolio guide

How the portfolio works and how to change it. Content lives in `content/`; presentation lives in
`app/templates/` and `app/static/portfolio.css`.

## Run it

```bash
pip install -r requirements.txt
python main.py          # http://localhost:5000
python -m pytest tests  # tests need no Supabase or settings.py
```

## Where things live

| What | Where |
|---|---|
| Name, headline, affiliation, links, About, Fun Facts, category labels, route filters | `content/site.yaml` |
| One project | `content/projects/<slug>.yaml` |
| Publications page | `content/publications.yaml` |
| Filtering and ordering | `app/portfolio.py` |
| Routes | `app/routes/portfolio_routes.py` |
| Page, card, gallery templates | `app/templates/{base,home,_gallery,_project_card}.html` |
| Gallery dropdown and Show more | `app/static/portfolio.js` |

## Add a project

Create `content/projects/my-project.yaml`. The file name must equal `slug`.

```yaml
slug: my-project
title: My Project
description: One line, 160 characters or fewer.
year: 2025
categories: [product, engineering]   # any of the ids in site.yaml
technologies: [Python, React]        # optional
thumbnail: images/my-project/cover.png   # path under app/static, or a full URL
thumbnail_fit: cover                 # optional: cover (fill, crops edges; default) or contain (whole image)
role: Lead engineer                  # optional
outcome: 1,200 users in the first month   # optional; only claims you can back up
links:                               # optional. Each shows as a labelled button on the card:
  paper: https://doi.org/...         # paper preprint report poster slides github demo website writeup prototype
  github: https://github.com/you/my-project
priority: 10                         # lower = earlier. Missing = 100
```

Everything except `slug`, `title`, `description`, and `categories` is optional and is omitted
cleanly when missing. Set `placeholder: true` to show a visible "Placeholder" badge on a project you haven't written.

Projects have no page of their own: the card is the whole entry, and its labelled link buttons
(Paper, Preprint, Report, Poster, Slides, GitHub...) go straight to the paper, repo, or file. Every
project needs at least one link (a test checks this). To host a PDF, put it in `app/static/files/papers/`
and use `report: files/papers/name.pdf`. Old `/projects/...` URLs redirect to the gallery.

## Change a project's categories

Edit its `categories:` list. Projects can have several. A project appears under a category
only if that category id is listed, so an `ai`-only project is not under `engineering`.
Rename a label (for example "Product" to "Product Management") in `categories:` in `site.yaml`.
The ids used in project files do not change.

## Ordering and Show more

There is a single Projects list. For the active filter, projects are sorted by `priority` (lower first),
then year (newest first), then title. The list shows the first `initial_visible` projects (set in `site.yaml`)
and a "Show more" button for the rest; with fewer projects than that there is no button.

## Park a project without deleting it

Move its file from `content/projects/` to `content/archive/`. Archived files are not loaded or shown.
Move it back to publish it again.

## Add a route with a default filter

In `site.yaml`, add to `route_filters`:

```yaml
route_filters:
  "/creative": creative
```

Restart the server. The new URL renders the same home page with its dropdown set to Creative.
The value must be `all` or a category id. Visitors can still change the filter without leaving the URL.

## How filtering works

1. The URL decides the initial filter, rendered by the server (so refresh and direct links work, and the
   page works without JavaScript).
2. Changing the dropdown fetches `/_gallery?category=<id>`, which is the same server code and template, and
   swaps the gallery. The page URL does not change.
3. Show more / Show less resets whenever the filter changes.

## Tests

`tests/test_filtering.py` covers the logic, `tests/test_routes.py` the URLs, fragment, edge cases and old project URLs,
`tests/test_content.py` the real content, and `tests/test_portfolio_quality.py` a recruiter-style checklist
(first impression, honesty, accessibility, mobile, page weight). Two tests are marked as expected failures until
LinkedIn and a profile photo are added; once you add them, those tests will report as failing ("XPASS strict"), which is the cue to delete the
`@content_gap` markers in `tests/test_portfolio_quality.py`.

## Known limits

- Client-side behaviour (dropdown swap, Show more, refresh) is checked by hand in a browser, not by automated tests.
- Placeholder projects have no outcomes, years, or technologies on purpose.
- The legacy pages (Drawings, Photos, Writings, PhD tracker, chat) are hidden and still need Supabase.
