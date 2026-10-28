from flask import Flask
import os

# Supabase is only needed by the chat and legacy pages. It is created lazily so the
# portfolio code (app.portfolio, app.routes.portfolio_routes) can be imported and
# tested without it.
_supabase_extension = None


def _get_supabase_extension():
    global _supabase_extension
    if _supabase_extension is None:
        from flask_supabase import Supabase

        _supabase_extension = Supabase()
    return _supabase_extension


def __getattr__(name):
    # Keeps `from app import supabase_extension` working for the existing routes.
    if name == "supabase_extension":
        return _get_supabase_extension()
    raise AttributeError(name)


def create_portfolio_app(content_dir=None):
    """The public site only: no Supabase, no settings.py, no chat or admin routes.
    This is what production serves (see wsgi.py)."""
    from .routes.portfolio_routes import portfolio_bp

    app = Flask(__name__)
    if content_dir is not None:
        app.config["PORTFOLIO_CONTENT_DIR"] = str(content_dir)
    app.register_blueprint(portfolio_bp)
    return app


def create_app():
    from settings import supabase_url, supabase_key

    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    app.config["SUPABASE_URL"] = supabase_url
    app.config["SUPABASE_KEY"] = supabase_key

    _get_supabase_extension().init_app(app)

    from .routes.portfolio_routes import portfolio_bp
    from .routes.index_routes import index_bp
    from .routes.chat_routes import chat_bp

    app.register_blueprint(portfolio_bp)
    app.register_blueprint(index_bp)
    app.register_blueprint(chat_bp)

    return app
