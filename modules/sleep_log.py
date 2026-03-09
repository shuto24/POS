import csv
import io
from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
import database as db

bp = Blueprint("sleep_log", __name__, url_prefix="/sleep")


@bp.route("/")
def index():
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    q = request.args.get("q", "")
    logs = db.get_sleep_logs(month=month, q=q or None)
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
        q=q,
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


@bp.route("/<int:id_>/edit", methods=["GET", "POST"])
def edit(id_):
    log = db.get_sleep_log(id_)
    if not log:
        return redirect(url_for("sleep_log.index"))
    if request.method == "POST":
        db.update_sleep_log(
            id_=id_,
            sleep_time=request.form["sleep_time"],
            wake_time=request.form["wake_time"],
            quality=request.form.get("quality") or None,
            memo=request.form.get("memo", ""),
        )
        return redirect(url_for("sleep_log.index", month=log["date"][:7]))
    return render_template(
        "sleep/edit.html",
        module="sleep_log",
        log=log,
    )


@bp.route("/delete/<int:id_>", methods=["POST"])
def delete(id_):
    month = request.form.get("month", datetime.now().strftime("%Y-%m"))
    db.delete_sleep_log(id_)
    return redirect(url_for("sleep_log.index", month=month))


@bp.route("/import", methods=["POST"])
def import_csv():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("ファイルを選択してください", "warning")
        return redirect(url_for("sleep_log.index"))

    stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
    reader = csv.DictReader(stream)
    rows, errors = [], 0
    for row in reader:
        try:
            rows.append({
                "date": row["date"].strip(),
                "sleep_time": row["sleep_time"].strip(),
                "wake_time": row["wake_time"].strip(),
                "quality": row.get("quality", "").strip(),
                "memo": row.get("memo", "").strip(),
            })
        except (KeyError, ValueError):
            errors += 1

    if rows:
        db.import_sleep_logs(rows)
        msg = f"{len(rows)} 件インポートしました"
        if errors:
            msg += f"（{errors} 件スキップ）"
        flash(msg, "success")
    else:
        flash(f"インポートできる行がありませんでした（{errors} 件エラー）", "danger")
    return redirect(url_for("sleep_log.index"))
