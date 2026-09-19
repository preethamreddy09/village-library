from datetime import date
from flask import Blueprint, render_template
from sqlalchemy import func
from models import db, Book, Loan

patterns_bp = Blueprint("patterns", __name__)


@patterns_bp.route("/patterns")
def patterns_home():
    total_books = Book.query.count()
    total_loans = Loan.query.count()
    active_loans = Loan.query.filter(Loan.return_date.is_(None)).count()
    overdue_loans = Loan.query.filter(
        Loan.return_date.is_(None), Loan.due_date < date.today()
    ).count()

    # Reads straight from the loans table's own snapshot fields — no
    # join to books needed, so history stays intact even after a book
    # is removed from the catalog.
    genre_counts = (
        db.session.query(Loan.book_genre, func.count(Loan.id).label("loan_count"))
        .group_by(Loan.book_genre)
        .order_by(func.count(Loan.id).desc())
        .all()
    )
    max_genre_count = genre_counts[0][1] if genre_counts else 0

    top_books = (
        db.session.query(Loan.book_title, func.count(Loan.id).label("loan_count"))
        .group_by(Loan.book_title)
        .order_by(func.count(Loan.id).desc())
        .limit(5)
        .all()
    )

    return render_template(
        "patterns.html",
        total_books=total_books,
        total_loans=total_loans,
        active_loans=active_loans,
        overdue_loans=overdue_loans,
        genre_counts=genre_counts,
        max_genre_count=max_genre_count,
        top_books=top_books,
    )