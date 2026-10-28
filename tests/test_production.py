"""The production app (wsgi.py) serves only the public portfolio."""

import subprocess
import sys

import pytest

from tests.conftest import ROOT


@pytest.fixture()
def prod():
    sys.path.insert(0, str(ROOT))
    import wsgi

    wsgi.app.config["TESTING"] = True
    return wsgi.app.test_client()


def test_public_pages_work(prod):
    for path in ["/", "/apm", "/engineering", "/research", "/design", "/publications"]:
        assert prod.get(path).status_code == 200, path


def test_static_assets_are_served(prod):
    assert prod.get("/static/portfolio.css").status_code == 200
    assert prod.get("/static/files/CV_Xuyang_Zhu.pdf").status_code == 200


@pytest.mark.parametrize(
    "path",
    ["/chat", "/send", "/dev_login", "/phd-tracker", "/api/phd-applications", "/memory-log", "/emotion-log",
     "/test-save", "/current-user", "/writings", "/drawings", "/photos"],
)
def test_private_and_legacy_routes_do_not_exist(prod, path):
    assert prod.get(path).status_code == 404, f"{path} must not be reachable in production"
    assert prod.post(path).status_code in (404, 405)


def test_not_found_page_is_themed(prod):
    r = prod.get("/nope")
    assert r.status_code == 404 and "Page not found" in r.get_data(as_text=True)


def test_production_never_imports_supabase_or_settings():
    """Run in a clean interpreter: the server has neither settings.py nor the supabase client."""
    code = "import sys, wsgi; bad = [m for m in ('flask_supabase', 'supabase', 'settings') if m in sys.modules]; print(bad); sys.exit(1 if bad else 0)"
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
