from flask import Flask
from flask_supabase import Supabase
from settings import supabase_url, supabase_key
import os

supabase_extension = Supabase()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    app.config["SUPABASE_URL"] = supabase_url
    app.config["SUPABASE_KEY"] = supabase_key

    supabase_extension.init_app(app)

    from .routes.index_routes import index_bp
    from .routes.chat_routes import chat_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(chat_bp)

    return app
