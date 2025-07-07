from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    url_for,
    jsonify,
)
from app import supabase_extension
from settings import DEV_PASSWORD
from app.utils.projects_data import get_all_projects, get_project_by_id

index_bp = Blueprint("index", __name__)


@index_bp.route("/")
def index():
    response = supabase_extension.client.table("writings").select("id, title").execute()
    articles = response.data
    return render_template("index.html", articles=articles)


@index_bp.route("/research")
def research():
    response = supabase_extension.client.table("writings").select("id, title").execute()
    articles = response.data
    return render_template("research.html", articles=articles)


@index_bp.route("/drawings")
def drawings():
    response = supabase_extension.client.table("writings").select("id, title").execute()
    articles = response.data
    return render_template("drawings.html", articles=articles)


@index_bp.route("/photos")
def photos():
    response = supabase_extension.client.table("writings").select("id, title").execute()
    articles = response.data
    return render_template("photos.html", articles=articles)


@index_bp.route("/writings")
def writings():
    response = (
        supabase_extension.client.table("writings")
        .select("id, title, summary, created_at")
        .execute()
    )
    articles = response.data
    return render_template("writings.html", articles=articles)


@index_bp.route("/phd-tracker")
def phd_tracker():
    if not session.get("dev"):
        return redirect(url_for("index.index"))

    response = supabase_extension.client.table("writings").select("id, title").execute()
    articles = response.data
    return render_template("phd-tracker.html", articles=articles)


@index_bp.route("/api/phd-applications", methods=["GET"])
def get_phd_applications():
    if not session.get("dev"):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        response = (
            supabase_extension.client.table("phd_applications")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@index_bp.route("/api/phd-applications", methods=["POST"])
def create_phd_application():
    if not session.get("dev"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        response = (
            supabase_extension.client.table("phd_applications").insert(data).execute()
        )
        return jsonify(response.data[0] if response.data else {})
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@index_bp.route("/api/phd-applications/<application_id>", methods=["PUT"])
def update_phd_application(application_id):
    if not session.get("dev"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        response = (
            supabase_extension.client.table("phd_applications")
            .update(data)
            .eq("id", application_id)
            .execute()
        )
        return jsonify(response.data[0] if response.data else {})
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@index_bp.route("/api/phd-applications/<application_id>", methods=["DELETE"])
def delete_phd_application(application_id):
    if not session.get("dev"):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        response = (
            supabase_extension.client.table("phd_applications")
            .delete()
            .eq("id", application_id)
            .execute()
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@index_bp.route("/projects")
def projects():
    projects = get_all_projects()
    return render_template("projects.html", projects=projects)


@index_bp.route("/projects/<int:project_id>")
def project_detail(project_id):
    project = get_project_by_id(project_id)
    if not project:
        return "Project not found", 404
    return render_template("project_detail.html", project=project)


@index_bp.route("/article/<int:article_id>")
def show_article(article_id):
    response = (
        supabase_extension.client.table("writings")
        .select("*")
        .eq("id", article_id)
        .single()
        .execute()
    )
    article = response.data
    if not article:
        return "Article not found", 404

    # Get all articles for navigation
    articles_response = (
        supabase_extension.client.table("writings").select("id, title").execute()
    )
    articles = articles_response.data

    return render_template("article.html", article=article, articles=articles)


@index_bp.route("/dev_login", methods=["POST"])
def dev_login():
    password = request.form.get("password")
    if password == DEV_PASSWORD:
        session["dev"] = True
    return redirect(url_for("index.index"))


@index_bp.route("/logout_dev")
def logout_dev():
    session.pop("dev", None)
    return redirect(url_for("index.index"))
