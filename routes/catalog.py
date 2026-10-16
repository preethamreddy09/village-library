import uuid
import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from sqlalchemy import or_, func
from models import db, Book, Loan
from routes.auth import login_required
from options import LANGUAGES, AGE_GROUPS, GENRES
from sqlalchemy.orm import selectinload

catalog_bp = Blueprint("catalog", __name__)

PER_PAGE = 24


def is_allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def upload_cover_to_supabase(file):
    """Uploads a cover image to Supabase Storage. Returns (public_url, error_message)."""
    ext = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"

    supabase_url = current_app.config["SUPABASE_URL"]
    service_key = current_app.config["SUPABASE_SERVICE_KEY"]
    bucket = current_app.config["SUPABASE_BUCKET"]

    if not supabase_url or not service_key:
        return None, "SUPABASE_URL or SUPABASE_SERVICE_KEY is not set on the server"

    upload_endpoint = f"{supabase_url}/storage/v1/object/{bucket}/{filename}"
    file_bytes = file.read()

    try:
        response = requests.post(
            upload_endpoint,
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": file.mimetype or "application/octet-stream",
            },
            data=file_bytes,
            timeout=20,
        )
    except requests.RequestException as e:
        print(f"SUPABASE UPLOAD ERROR: {e}", flush=True)
        return None, f"could not reach Supabase ({type(e).__name__})"

    if response.status_code in (200, 201):
        return f"{supabase_url}/storage/v1/object/public/{bucket}/{filename}", None

    print(f"SUPABASE UPLOAD FAILED: status={response.status_code}, body={response.text}", flush=True)
    return None, f"Supabase said {response.status_code}: {response.text[:150]}"


def read_book_form():
    """Reads and validates the add/edit form. Returns (data, error_message)."""
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    genre = request.form.get("genre", "").strip()
    language = request.form.get("language", "").strip()
    age_group = request.form.get("age_group", "").strip()
    summary = request.form.get("summary", "").strip()

    try:
        total_copies = max(1, int(request.form.get("total_copies", "1").strip()))
    except ValueError:
        total_copies = 1

    if not title or not author:
        return None, "Title and author are required."
    if genre not in GENRES:
        return None, "Please pick a genre from the list."
    if language not in LANGUAGES:
        return None, "Please pick a language."
    if age_group not in AGE_GROUPS:
        return None, "Please pick an age group."

    return {
        "title": title,
        "author": author,
        "genre": genre,
        "language": language,
        "age_group": age_group,
        "summary": summary,
        "total_copies": total_copies,
    }, None


@catalog_bp.route("/")
def home():
    q = request.args.get("q", "").strip()
    language = request.args.get("language", "").strip()
    age_group = request.args.get("age_group", "").strip()
    genre = request.args.get("genre", "").strip()
    only_available = request.args.get("available", "") == "1"
    page = request.args.get("page", 1, type=int)

    query = Book.query.options(selectinload(Book.loans))

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Book.title.ilike(like), Book.author.ilike(like)))
    if language:
        query = query.filter(Book.language == language)
    if age_group:
        query = query.filter(Book.age_group == age_group)
    if genre:
        query = query.filter(Book.genre == genre)
    if only_available:
        active_count = (
            db.session.query(func.count(Loan.id))
            .filter(Loan.book_id == Book.id, Loan.return_date.is_(None))
            .correlate(Book)
            .scalar_subquery()
        )
        query = query.filter(Book.total_copies > active_count)

    query = query.order_by(Book.title)
    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)

    # Only non-empty filters, so page links stay clean
    active_filters = {
        k: v
        for k, v in {
            "q": q,
            "language": language,
            "age_group": age_group,
            "genre": genre,
            "available": "1" if only_available else "",
        }.items()
        if v
    }

    return render_template(
        "catalog.html",
        books=pagination.items,
        pagination=pagination,
        active_filters=active_filters,
        q=q,
        selected_language=language,
        selected_age_group=age_group,
        selected_genre=genre,
        only_available=only_available,
        languages=LANGUAGES,
        age_groups=AGE_GROUPS,
        genres=GENRES,
    )


@catalog_bp.route("/add-book", methods=["GET", "POST"])
@login_required
def add_book():
    if request.method == "POST":
        data, error = read_book_form()
        if error:
            flash(error)
            return render_template("book_form.html", languages=LANGUAGES, age_groups=AGE_GROUPS, genres=GENRES)

        cover_url = None
        file = request.files.get("cover_image")
        if file and file.filename and is_allowed_file(file.filename):
            cover_url, upload_error = upload_cover_to_supabase(file)
            if cover_url is None:
                flash(f"Book saved, but the cover image failed to upload: {upload_error}")

        new_book = Book(cover_image=cover_url, **data)
        db.session.add(new_book)
        db.session.commit()

        flash(f'"{data["title"]}" added to the catalog.')
        return redirect(url_for("catalog.home"))

    return render_template("book_form.html", languages=LANGUAGES, age_groups=AGE_GROUPS, genres=GENRES)


@catalog_bp.route("/edit-book/<int:book_id>", methods=["GET", "POST"])
@login_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)

    if request.method == "POST":
        data, error = read_book_form()
        if error:
            flash(error)
            return render_template("book_form.html", book=book, languages=LANGUAGES, age_groups=AGE_GROUPS, genres=GENRES)

        active_count = Loan.query.filter_by(book_id=book.id, return_date=None).count()
        if data["total_copies"] < active_count:
            flash(f"Can't set total copies below {active_count} — that many are currently out on loan.")
            return render_template("book_form.html", book=book, languages=LANGUAGES, age_groups=AGE_GROUPS, genres=GENRES)

        file = request.files.get("cover_image")
        if file and file.filename and is_allowed_file(file.filename):
            cover_url, upload_error = upload_cover_to_supabase(file)
            if cover_url:
                book.cover_image = cover_url
            else:
                flash(f"Changes saved, but the cover image failed to upload: {upload_error}")

        for field, value in data.items():
            setattr(book, field, value)
        db.session.commit()

        flash(f'"{data["title"]}" updated.')
        return redirect(url_for("catalog.home"))

    return render_template("book_form.html", book=book, languages=LANGUAGES, age_groups=AGE_GROUPS, genres=GENRES)


@catalog_bp.route("/delete-book/<int:book_id>", methods=["POST"])
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)

    active_count = Loan.query.filter_by(book_id=book.id, return_date=None).count()
    if active_count > 0:
        flash("Can't remove — copies are still out on loan.")
        return redirect(url_for("catalog.home"))

    Loan.query.filter_by(book_id=book.id).update({"book_id": None})

    title = book.title
    db.session.delete(book)
    db.session.commit()

    flash(f'"{title}" removed from the catalog.')
    return redirect(url_for("catalog.home"))