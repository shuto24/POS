import csv
import io
from datetime import datetime

from flask import Flask, redirect, render_template, request, Response, url_for

import database as db

app = Flask(__name__)


@app.before_request
def setup():
    db.init_db()


@app.route("/")
def index():
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    transactions = db.get_transactions(month=month)
    months = db.get_available_months()
    if month not in months:
        months.insert(0, month)

    income_total = sum(t["amount"] for t in transactions if t["type"] == "income")
    expense_total = sum(t["amount"] for t in transactions if t["type"] == "expense")
    balance = income_total - expense_total

    return render_template(
        "index.html",
        transactions=transactions,
        month=month,
        months=months,
        income_total=income_total,
        expense_total=expense_total,
        balance=balance,
    )


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        date = request.form["date"]
        type_ = request.form["type"]
        category = request.form["category"]
        amount = int(request.form["amount"])
        memo = request.form.get("memo", "")
        db.add_transaction(date, type_, category, amount, memo)
        return redirect(url_for("index", month=date[:7]))

    today = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "add.html",
        today=today,
        income_categories=db.INCOME_CATEGORIES,
        expense_categories=db.EXPENSE_CATEGORIES,
    )


@app.route("/delete/<int:id_>", methods=["POST"])
def delete(id_):
    month = request.form.get("month", datetime.now().strftime("%Y-%m"))
    db.delete_transaction(id_)
    return redirect(url_for("index", month=month))


@app.route("/summary")
def summary():
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    months = db.get_available_months()
    if month not in months:
        months.insert(0, month)

    monthly = db.get_monthly_summary()
    category_data = db.get_category_summary(month=month)

    income_cats = {d["category"]: d["total"] for d in category_data if d["type"] == "income"}
    expense_cats = {d["category"]: d["total"] for d in category_data if d["type"] == "expense"}

    return render_template(
        "summary.html",
        month=month,
        months=months,
        monthly=monthly,
        income_cats=income_cats,
        expense_cats=expense_cats,
    )


@app.route("/export")
def export():
    month = request.args.get("month")
    transactions = db.get_transactions(month=month)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["日付", "種別", "カテゴリ", "金額", "メモ"])
    for t in transactions:
        type_label = "収入" if t["type"] == "income" else "支出"
        writer.writerow([t["date"], type_label, t["category"], t["amount"], t["memo"] or ""])

    filename = f"kakeibo_{month or 'all'}.csv"
    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
