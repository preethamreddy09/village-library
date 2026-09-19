import uuid
import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from models import db, Book, Loan
from routes.auth import login_required

catalog_bp = Blueprint("catalog", __name__)


def is_allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def upload_cover_to_supabase(file):
    """Uploads a cover image to Supabase Storage and returns its public URL, or None on failure."""
    ext = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"

    supabase_url = current_app.config["SUPABASE_URL"]
    service_key = current_app.config["SUPABASE_SERVICE_KEY"]
    bucket = current_app.config["SUPABASE_BUCKET"]

    if not supabase_url or not service_key:
        return None

    upload_endpoint = f"{supabase_url}/storage/v1/object/{bucket}/{filename}"
    file_bytes = file.read()

    response = requests.post(
        upload_endpoint,
        headers={
            "Authorization": f"Bearer {service_key}",
            "Content-Type": file.mimetype or "application/octet-stream",
        },
        data=file_bytes,
    )

    if response.status_code in (200, 201):
        return f"{supabase_url}/storage/v1/object/public/{bucket}/{filename}"
    print(f"SUPABASE UPLOAD FAILED: status={response.status_code}, body={response.text}")
    return None


@catalog_bp.route("/")
def home():
    books = Book.query.order_by(Book.title).all()
    return render_template("catalog.html", books=books)


@catalog_bp.route("/add-book", methods=["GET", "POST"])
@login_required
def add_book():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        genre = request.form.get("genre", "").strip()
        summary = request.form.get("summary", "").strip()
        total_copies = request.form.get("total_copies", "1").strip()

        if not title or not author or not genre:
            flash("Title, author, and genre are required.")
            return render_template("book_form.html")

        try:
            total_copies = max(1, int(total_copies))
        except ValueError:
            total_copies = 1

        cover_url = None
        file = request.files.get("cover_image")
        if file and file.filename and is_allowed_file(file.filename):
            cover_url = upload_cover_to_supabase(file)
            if cover_url is None:
                flash("Book saved, but the cover image failed to upload.")

        new_book = Book(
            title=title,
            author=author,
            genre=genre,
            summary=summary,
            total_copies=total_copies,
            cover_image=cover_url,
        )
        db.session.add(new_book)
        db.session.commit()

        flash(f'"{title}" added to the catalog.')
        return redirect(url_for("catalog.home"))

    return render_template("book_form.html")


@catalog_bp.route("/edit-book/<int:book_id>", methods=["GET", "POST"])
@login_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        genre = request.form.get("genre", "").strip()
        summary = request.form.get("summary", "").strip()
        total_copies = request.form.get("total_copies", "1").strip()

        if not title or not author or not genre:
            flash("Title, author, and genre are required.")
            return render_template("book_form.html", book=book)

        try:
            total_copies = max(1, int(total_copies))
        except ValueError:
            total_copies = 1

        active_count = Loan.query.filter_by(book_id=book.id, return_date=None).count()
        if total_copies < active_count:
            flash(f"Can't set total copies below {active_count} — that many are currently out on loan.")
            return render_template("book_form.html", book=book)

        file = request.files.get("cover_image")
        if file and file.filename and is_allowed_file(file.filename):
            cover_url = upload_cover_to_supabase(file)
            if cover_url:
                book.cover_image = cover_url
            else:
                flash("Changes saved, but the new cover image failed to upload.")

        book.title = title
        book.author = author
        book.genre = genre
        book.summary = summary
        book.total_copies = total_copies
        db.session.commit()

        flash(f'"{title}" updated.')
        return redirect(url_for("catalog.home"))

    return render_template("book_form.html", book=book)


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