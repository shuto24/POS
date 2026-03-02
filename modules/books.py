from datetime import datetime
from flask import Blueprint, redirect, render_template, request, url_for
import database as db

bp = Blueprint("books", __name__, url_prefix="/books")


@bp.route("/")
def index():
    status = request.args.get("status", "")
    books = db.get_books(status=status or None)
    return render_template(
        "books/index.html",
        module="books",
        books=books,
        status=status,
        statuses=db.BOOK_STATUSES,
    )


@bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        db.add_book(
            title=request.form["title"],
            author=request.form.get("author", ""),
            status=request.form["status"],
            rating=request.form.get("rating") or None,
            total_pages=request.form.get("total_pages") or None,
            start_date=request.form.get("start_date") or None,
            end_date=request.form.get("end_date") or None,
            memo=request.form.get("memo", ""),
        )
        return redirect(url_for("books.index"))

    today = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "books/add.html",
        module="books",
        today=today,
        statuses=db.BOOK_STATUSES,
    )


@bp.route("/delete/<int:id_>", methods=["POST"])
def delete(id_):
    db.delete_book(id_)
    return redirect(url_for("books.index"))
