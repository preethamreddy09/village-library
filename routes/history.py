from flask import Blueprint, render_template, request
from models import db, Loan
from routes.auth import login_required

history_bp = Blueprint("history", __name__)

PER_PAGE = 50


@history_bp.route("/history")
@login_required
def history_home():
    genre = request.args.get("genre", "").strip()
    book_title = request.args.get("book_title", "").strip()
    status = request.args.get("status", "").strip()
    page = request.args.get("page", "1")

    try:
        page = max(1, int(page))
    except ValueError:
        page = 1

    query = Loan.query

    if genre:
        query = query.filter(Loan.book_genre == genre)
    if book_title:
        query = query.filter(Loan.book_title == book_title)
    if status == "active":
        query = query.filter(Loan.return_date.is_(None))
    elif status == "overdue":
        from datetime import date
        query = query.filter(Loan.return_date.is_(None), Loan.due_date < date.today())
    elif status == "returned":
        query = query.filter(Loan.return_date.isnot(None))

    query = query.order_by(Loan.issue_date.desc())

    total_count = query.count()
    loans = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()
    has_next = (page * PER_PAGE) < total_count
    has_prev = page > 1

    # For the filter dropdowns — distinct values actually present in loan history
    all_genres = [r[0] for r in db.session.query(Loan.book_genre).distinct().order_by(Loan.book_genre).all()]
    all_titles = [r[0] for r in db.session.query(Loan.book_title).distinct().order_by(Loan.book_title).all()]

    return render_template(
        "history.html",
        loans=loans,
        all_genres=all_genres,
        all_titles=all_titles,
        selected_genre=genre,
        selected_title=book_title,
        selected_status=status,
        page=page,
        has_next=has_next,
        has_prev=has_prev,
        total_count=total_count,
    )