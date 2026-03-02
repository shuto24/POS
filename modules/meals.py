from datetime import datetime
from flask import Blueprint, redirect, render_template, request, url_for
import database as db

bp = Blueprint("meals", __name__, url_prefix="/meals")


@bp.route("/")
def index():
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    meals = db.get_meals(month=month)
    months = db.get_meal_months()
    if month not in months:
        months.insert(0, month)

    total_calories = sum(m["calories"] or 0 for m in meals)

    return render_template(
        "meals/index.html",
        module="meals",
        meals=meals,
        month=month,
        months=months,
        total_calories=total_calories,
        meal_types=db.MEAL_TYPES,
    )


@bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        db.add_meal(
            date=request.form["date"],
            meal_type=request.form["meal_type"],
            content=request.form["content"],
            calories=request.form.get("calories") or None,
            memo=request.form.get("memo", ""),
        )
        return redirect(url_for("meals.index", month=request.form["date"][:7]))

    today = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "meals/add.html",
        module="meals",
        today=today,
        meal_types=db.MEAL_TYPES,
    )


@bp.route("/delete/<int:id_>", methods=["POST"])
def delete(id_):
    month = request.form.get("month", datetime.now().strftime("%Y-%m"))
    db.delete_meal(id_)
    return redirect(url_for("meals.index", month=month))
