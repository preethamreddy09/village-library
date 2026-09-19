from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Book, Loan
from routes.auth import login_required

circulation_bp = Blueprint("circulation", __name__)


@circulation_bp.route("/circulation")
@login_required
def circulation_home():
    active_loans = (
        Loan.query.filter(Loan.return_date.is_(None))
        .order_by(Loan.due_date)
        .all()
    )
    lendable_books = [b for b in Book.query.order_by(Book.title).all() if b.is_available]
    return render_template(
        "circulation.html", active_loans=active_loans, lendable_books=lendable_books
    )


@circulation_bp.route("/lend", methods=["POST"])
@login_required
def lend_book():
    book_id = request.form.get("book_id")
    borrower_name = request.form.get("borrower_name", "").strip()
    borrower_contact = request.form.get("borrower_contact", "").strip()
    days = request.form.get("days", "14").strip()

    book = Book.query.get(book_id)
    try:
        days = max(1, int(days))
    except ValueError:
        days = 14

    if not book or not borrower_name:
        flash("Pick a book and enter the borrower's name.")
        return redirect(url_for("circulation.circulation_home"))

    if not book.is_available:
        flash("No copies available for that book.")
        return redirect(url_for("circulation.circulation_home"))

    loan = Loan(
        book_id=book.id,
        book_title=book.title,
        book_genre=book.genre,
        borrower_name=borrower_name,
        borrower_contact=borrower_contact,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=days),
    )
    db.session.add(loan)
    db.session.commit()
    flash(f'Lent "{book.title}" to {borrower_name}.')
    return redirect(url_for("circulation.circulation_home"))


@circulation_bp.route("/return/<int:loan_id>", methods=["POST"])
@login_required
def return_book(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    loan.return_date = date.today()
    db.session.commit()
    flash(f'Marked "{loan.book_title}" as returned.')
    return redirect(url_for("circulation.circulation_home"))