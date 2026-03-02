from datetime import datetime
from flask import Blueprint, redirect, render_template, request, url_for
import database as db

bp = Blueprint("exercise", __name__, url_prefix="/exercise")


@bp.route("/")
def index():
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    exercises = db.get_exercises(month=month)
    months = db.get_exercise_months()
    if month not in months:
        months.insert(0, month)

    total_duration = sum(e["duration"] for e in exercises)
    total_calories = sum(e["calories"] or 0 for e in exercises)

    return render_template(
        "exercise/index.html",
        module="exercise",
        exercises=exercises,
        month=month,
        months=months,
        total_duration=total_duration,
        total_calories=total_calories,
    )


@bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        db.add_exercise(
            date=request.form["date"],
            type_=request.form["type"],
            duration=int(request.form["duration"]),
            distance=request.form.get("distance") or None,
            calories=request.form.get("calories") or None,
            memo=request.form.get("memo", ""),
        )
        return redirect(url_for("exercise.index", month=request.form["date"][:7]))

    today = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "exercise/add.html",
        module="exercise",
        today=today,
        exercise_types=db.EXERCISE_TYPES,
    )


@bp.route("/delete/<int:id_>", methods=["POST"])
def delete(id_):
    month = request.form.get("month", datetime.now().strftime("%Y-%m"))
    db.delete_exercise(id_)
    return redirect(url_for("exercise.index", month=month))
