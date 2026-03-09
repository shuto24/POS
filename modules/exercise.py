import csv
import io
from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
import database as db

bp = Blueprint("exercise", __name__, url_prefix="/exercise")


@bp.route("/")
def index():
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    q = request.args.get("q", "")
    exercises = db.get_exercises(month=month, q=q or None)
    months = db.get_exercise_months()
    if month not in months:
        months.insert(0, month)

    total_duration = sum(e["duration"] for e in exercises)
    total_calories = sum(e["calories"] or 0 for e in exercises)
    weight_logs = db.get_weight_logs()

    return render_template(
        "exercise/index.html",
        module="exercise",
        exercises=exercises,
        month=month,
        months=months,
        total_duration=total_duration,
        total_calories=total_calories,
        weight_logs=weight_logs,
        now_date=datetime.now().strftime("%Y-%m-%d"),
        q=q,
    )


@bp.route("/weight", methods=["POST"])
def save_weight():
    date_ = request.form.get("date", "").strip()
    weight_kg = request.form.get("weight_kg", "").strip()
    month = request.form.get("month", datetime.now().strftime("%Y-%m"))
    if date_ and weight_kg:
        try:
            db.add_or_update_weight(date_, float(weight_kg))
        except ValueError:
            pass
    return redirect(url_for("exercise.index", month=month))


@bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        date_ = request.form["date"]
        db.add_exercise(
            date=date_,
            type_=request.form["type"],
            duration=int(request.form["duration"]),
            distance=request.form.get("distance") or None,
            calories=request.form.get("calories") or None,
            memo=request.form.get("memo", ""),
        )
        weight_kg = request.form.get("weight_kg", "").strip()
        if weight_kg:
            try:
                db.add_or_update_weight(date_, float(weight_kg))
            except ValueError:
                pass
        return redirect(url_for("exercise.index", month=date_[:7]))

    today = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "exercise/add.html",
        module="exercise",
        today=today,
        exercise_types=db.EXERCISE_TYPES,
    )


@bp.route("/<int:id_>/edit", methods=["GET", "POST"])
def edit(id_):
    ex = db.get_exercise(id_)
    if not ex:
        return redirect(url_for("exercise.index"))
    if request.method == "POST":
        db.update_exercise(
            id_=id_,
            type_=request.form["type"],
            duration=int(request.form["duration"]),
            distance=request.form.get("distance") or None,
            calories=request.form.get("calories") or None,
            memo=request.form.get("memo", ""),
        )
        return redirect(url_for("exercise.index", month=ex["date"][:7]))
    return render_template(
        "exercise/edit.html",
        module="exercise",
        ex=ex,
        exercise_types=db.EXERCISE_TYPES,
    )


@bp.route("/delete/<int:id_>", methods=["POST"])
def delete(id_):
    month = request.form.get("month", datetime.now().strftime("%Y-%m"))
    db.delete_exercise(id_)
    return redirect(url_for("exercise.index", month=month))


@bp.route("/import", methods=["POST"])
def import_csv():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("ファイルを選択してください", "warning")
        return redirect(url_for("exercise.index"))

    stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
    reader = csv.DictReader(stream)
    rows, errors = [], 0
    for row in reader:
        try:
            rows.append({
                "date": row["date"].strip(),
                "type": row["type"].strip(),
                "duration": int(row["duration"]),
                "distance": row.get("distance", "").strip(),
                "calories": row.get("calories", "").strip(),
                "memo": row.get("memo", "").strip(),
            })
        except (KeyError, ValueError):
            errors += 1

    if rows:
        db.import_exercises(rows)
        msg = f"{len(rows)} 件インポートしました"
        if errors:
            msg += f"（{errors} 件スキップ）"
        flash(msg, "success")
    else:
        flash(f"インポートできる行がありませんでした（{errors} 件エラー）", "danger")
    return redirect(url_for("exercise.index"))
