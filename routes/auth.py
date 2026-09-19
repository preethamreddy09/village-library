from functools import wraps
from flask import session, redirect, url_for, request, render_template, Blueprint, current_app

auth_bp = Blueprint("auth", __name__)


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("is_librarian"):
            return redirect(url_for("auth.login", next=request.referrer or url_for("catalog.home")))
        return view_func(*args, **kwargs)
    return wrapped


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        entered = request.form.get("passcode", "")
        if entered == current_app.config["ADMIN_PASSCODE"]:
            session["is_librarian"] = True
            next_url = request.form.get("next") or url_for("catalog.home")
            return redirect(next_url)
        error = "That code isn't right — try again."
    # Use the page the user came FROM, not the form-submit URL itself
    default_next = request.referrer or url_for("catalog.home")
    return render_template("login.html", error=error, next=request.args.get("next", default_next))


@auth_bp.route("/logout")
def logout():
    session.pop("is_librarian", None)
    return redirect(url_for("catalog.home"))