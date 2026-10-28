"""Production entry point: gunicorn wsgi:app

Serves only the public portfolio. It does not import Supabase or settings.py, and the chat,
PhD tracker, and dev-login routes do not exist here.
"""

from app import create_portfolio_app

app = create_portfolio_app()
