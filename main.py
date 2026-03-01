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
        income_categories=db.get_categories("income"),
        expense_categories=db.get_categories("expense"),
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

    year = int(month[:4])
    monthly = db.get_monthly_summary()
    category_data = db.get_category_summary(month=month)

    income_cats = {d["category"]: d["total"] for d in category_data if d["type"] == "income"}
    expense_cats = {d["category"]: d["total"] for d in category_data if d["type"] == "expense"}

    # 月予算 vs 実績
    def build_budget_rows(cats, type_):
        rows = []
        for cat, actual in cats.items():
            budget = db.get_monthly_budget(year, month, type_, cat)
            rows.append({"category": cat, "actual": actual, "budget": budget})
        return rows

    income_budget_rows = build_budget_rows(income_cats, "income")
    expense_budget_rows = build_budget_rows(expense_cats, "expense")

    # 年間サマリー（全カテゴリ）
    all_categories = {
        "income": db.get_categories("income"),
        "expense": db.get_categories("expense"),
    }
    yearly_rows = {"income": [], "expense": []}
    for type_, cats in all_categories.items():
        for cat in cats:
            budget = db.get_yearly_budget(year, type_, cat)
            actual = db.get_yearly_actual(year, type_, cat)
            if budget is not None or actual > 0:
                yearly_rows[type_].append({"category": cat, "actual": actual, "budget": budget})

    return render_template(
        "summary.html",
        month=month,
        year=year,
        months=months,
        monthly=monthly,
        income_cats=income_cats,
        expense_cats=expense_cats,
        income_budget_rows=income_budget_rows,
        expense_budget_rows=expense_budget_rows,
        yearly_rows=yearly_rows,
    )


@app.route("/budget")
def budget():
    year = int(request.args.get("year", datetime.now().year))
    years = list(range(datetime.now().year + 1, datetime.now().year - 3, -1))
    budgets = db.get_budgets(year)
    months_list = [f"{year}-{m:02d}" for m in range(1, 13)]
    return render_template(
        "budget.html",
        year=year,
        years=years,
        budgets=budgets,
        income_categories=db.get_categories("income"),
        expense_categories=db.get_categories("expense"),
        months_list=months_list,
    )


@app.route("/budget/save", methods=["POST"])
def budget_save():
    year = int(request.form["year"])
    type_ = request.form["type"]
    category = request.form["category"]
    period_type = request.form["period_type"]

    if period_type == "monthly_variable":
        months_list = [f"{year}-{m:02d}" for m in range(1, 13)]
        for m in months_list:
            raw = request.form.get(f"amount_{m}", "").strip()
            if raw:
                db.upsert_budget(year, type_, category, period_type, int(raw), month=m)
    else:
        amount = int(request.form["amount"])
        db.upsert_budget(year, type_, category, period_type, amount)

    return redirect(url_for("budget", year=year))


@app.route("/budget/delete", methods=["POST"])
def budget_delete():
    year = int(request.form["year"])
    type_ = request.form["type"]
    category = request.form["category"]
    db.delete_budget(year, type_, category)
    return redirect(url_for("budget", year=year))


@app.route("/categories")
def categories():
    cats = db.get_categories_detail()
    income_cats = [c for c in cats if c["type"] == "income"]
    expense_cats = [c for c in cats if c["type"] == "expense"]
    return render_template("categories.html", income_cats=income_cats, expense_cats=expense_cats)


@app.route("/categories/add", methods=["POST"])
def categories_add():
    type_ = request.form["type"]
    name = request.form["name"].strip()
    if name:
        db.add_category(type_, name)
    return redirect(url_for("categories"))


@app.route("/categories/delete", methods=["POST"])
def categories_delete():
    type_ = request.form["type"]
    name = request.form["name"]
    db.delete_category(type_, name)
    return redirect(url_for("categories"))


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
