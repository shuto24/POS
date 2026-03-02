from datetime import datetime
from flask import Blueprint, redirect, render_template, request, url_for
import database as db

bp = Blueprint("sleep_log", __name__, url_prefix="/sleep")


@bp.route("/")
def index():
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    logs = db.get_sleep_logs(month=month)
    months = db.get_sleep_months()
    if month not in months:
        months.insert(0, month)

    durations = [l["duration_min"] for l in logs if l["duration_min"]]
    avg_duration = sum(durations) // len(durations) if durations else None
    qualities = [l["quality"] for l in logs if l["quality"]]
    avg_quality = round(sum(qualities) / len(qualities), 1) if qualities else None

    return render_template(
        "sleep/index.html",
        module="sleep_log",
        logs=logs,
        month=month,
        months=months,
        avg_duration=avg_duration,
        avg_quality=avg_quality,
    )


@bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        db.add_sleep_log(
            date=request.form["date"],
            sleep_time=request.form["sleep_time"],
            wake_time=request.form["wake_time"],
            quality=request.form.get("quality") or None,
            memo=request.form.get("memo", ""),
        )
        return redirect(url_for("sleep_log.index", month=request.form["date"][:7]))

    today = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "sleep/add.html",
        module="sleep_log",
        today=today,
    )


@bp.route("/delete/<int:id_>", methods=["POST"])
def delete(id_):
    month = request.form.get("month", datetime.now().strftime("%Y-%m"))
    db.delete_sleep_log(id_)
    return redirect(url_for("sleep_log.index", month=month))
