from datetime import date, timedelta
from flask import Blueprint, render_template, request

import database as db
from modules.garbage import get_trash, TRASH_TYPES, _is_no_collection

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


def _this_week_monday():
    today = date.today()
    return today - timedelta(days=today.weekday())


def _week_label(week_start: date) -> str:
    week_end = week_start + timedelta(days=6)
    return f"{week_start.strftime('%m/%d')} 〜 {week_end.strftime('%m/%d')}"


def _today_trash_ctx():
    today_date = date.today()
    return {
        "today_trash": get_trash(today_date),
        "today_no_collect": _is_no_collection(today_date),
        "trash_types": TRASH_TYPES,
    }


def _latest_weight():
    logs = db.get_weight_logs()
    return logs[-1]["weight_kg"] if logs else None


@bp.route("/")
def index():
    period = request.args.get("period", "month")
    trash_ctx = _today_trash_ctx()

    latest_weight = _latest_weight()

    if period == "day":
        today = date.today()
        raw = request.args.get("day", today.isoformat())
        try:
            day_date = date.fromisoformat(raw)
        except ValueError:
            day_date = today
        prev_day = (day_date - timedelta(days=1)).isoformat()
        next_day = (day_date + timedelta(days=1)).isoformat()
        stats = db.get_dashboard_day(day_date.isoformat())
        label = "Today" if day_date == today else day_date.isoformat()
        return render_template(
            "dashboard/index.html",
            module="dashboard",
            period=period,
            label=label,
            stats=stats,
            day=day_date.isoformat(),
            prev_day=prev_day,
            next_day=next_day,
            latest_weight=latest_weight,
            **trash_ctx,
        )

    elif period == "week":
        raw = request.args.get("week", _this_week_monday().isoformat())
        try:
            week_start = date.fromisoformat(raw)
        except ValueError:
            week_start = _this_week_monday()
        prev_week = (week_start - timedelta(weeks=1)).isoformat()
        next_week = (week_start + timedelta(weeks=1)).isoformat()
        stats = db.get_dashboard_week(week_start.isoformat())
        label = _week_label(week_start)
        return render_template(
            "dashboard/index.html",
            module="dashboard",
            period=period,
            label=label,
            stats=stats,
            week=week_start.isoformat(),
            prev_week=prev_week,
            next_week=next_week,
            latest_weight=latest_weight,
            **trash_ctx,
        )

    elif period == "year":
        year = int(request.args.get("year", date.today().year))
        stats = db.get_dashboard_year(year)
        years = list(range(date.today().year, date.today().year - 5, -1))
        return render_template(
            "dashboard/index.html",
            module="dashboard",
            period=period,
            label=f"{year}年",
            stats=stats,
            year=year,
            years=years,
            latest_weight=latest_weight,
            **trash_ctx,
        )

    else:  # month
        month = request.args.get("month", date.today().strftime("%Y-%m"))
        stats = db.get_dashboard_month(month)
        months = []
        d = date.today().replace(day=1)
        for _ in range(24):
            months.append(d.strftime("%Y-%m"))
            if d.month == 1:
                d = d.replace(year=d.year - 1, month=12)
            else:
                d = d.replace(month=d.month - 1)
        if month not in months:
            months.insert(0, month)
        return render_template(
            "dashboard/index.html",
            module="dashboard",
            period=period,
            label=f"{month}",
            stats=stats,
            month=month,
            months=months,
            latest_weight=latest_weight,
            **trash_ctx,
        )
