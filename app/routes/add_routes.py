from flask import Blueprint, render_template, request, redirect, url_for
from datetime import datetime
from app import supabase_extension
from app.utils.helpers import convert_to_paragraphs

add_bp = Blueprint("add", __name__)


@add_bp.route("/add", methods=["GET", "POST"])
def add_article():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        summary = request.form.get("summary", "").strip()
        content = convert_to_paragraphs(request.form.get("content", "").strip())
        created_at = request.form.get("created_at", "").strip()

        if not title or not content or not created_at:
            return "Title, content, and created time are required.", 400

        try:
            dt = datetime.fromisoformat(created_at)
        except ValueError:
            return "Invalid date format.", 400

        response = (
            supabase_extension.client.table("writings")
            .insert(
                [
                    {
                        "title": title,
                        "summary": summary,
                        "content": content,
                        "created_at": dt.isoformat(),
                    }
                ]
            )
            .execute()
        )

        return redirect(url_for("index.index"))

    now = datetime.now().isoformat(timespec="minutes")
    # Get all articles for navigation
    response = supabase_extension.client.table("writings").select("id, title").execute()
    articles = response.data
    return render_template("add.html", now=now, articles=articles)
