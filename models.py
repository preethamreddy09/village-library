from datetime import date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    genre = db.Column(db.String(100), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)
    total_copies = db.Column(db.Integer, nullable=False, default=1)

    loans = db.relationship("Loan", backref="book")

    @property
    def cover_image_url(self):
        """Returns the full image URL if one was uploaded, or None (template falls back to the default)."""
        return self.cover_image if self.cover_image else None

    @property
    def copies_on_loan(self):
        return sum(1 for loan in self.loans if loan.return_date is None)

    @property
    def copies_available(self):
        return max(0, self.total_copies - self.copies_on_loan)

    @property
    def is_available(self):
        return self.copies_available > 0

    @property
    def times_borrowed(self):
        return len(self.loans)

    @property
    def next_available_date(self):
        """Earliest due date among this book's active loans, or None if copies are already available."""
        if self.is_available:
            return None
        active = [l for l in self.loans if l.return_date is None]
        if not active:
            return None
        return min(l.due_date for l in active)


class Loan(db.Model):
    __tablename__ = "loans"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=True)

    book_title = db.Column(db.String(200), nullable=False)
    book_genre = db.Column(db.String(100), nullable=False)

    borrower_name = db.Column(db.String(150), nullable=False)
    borrower_contact = db.Column(db.String(150), nullable=True)

    issue_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date, nullable=True)

    @property
    def is_overdue(self):
        return self.return_date is None and self.due_date < date.today()

    @property
    def status(self):
        if self.return_date:
            return "returned"
        return "overdue" if self.is_overdue else "on loan"