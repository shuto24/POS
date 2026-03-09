from datetime import date, timedelta
from dotenv import load_dotenv
from flask import Blueprint, render_template, request
import json
import os
import database as db

bp = Blueprint("report", __name__, url_prefix="/report")


def _this_week_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _build_prompt(data: dict) -> str:
    lines = [
        f"以下は {data['week_start']} 〜 {data['week_end']} の週間健康データです。",
        "このデータをもとに、日本語で具体的な振り返りコメントと来週へのアドバイスを生成してください。",
        "形式: JSON {{ \"summary\": \"全体総評(2-3文)\", \"insights\": [\"観察1\",\"観察2\",...], \"advice\": [\"アドバイス1\",...] }}",
        "",
        "## 運動",
    ]
    if data["exercises"]:
        for e in data["exercises"]:
            lines.append(f"- {e['type']}: {e['cnt']}回 計{e['total_min']}分 {e['total_cal'] or 0}kcal")
    else:
        lines.append("- 記録なし")

    lines.append("## 睡眠")
    if data["sleeps"]:
        for s in data["sleeps"]:
            dur = f"{s['duration_min']//60}h{s['duration_min']%60}m" if s["duration_min"] else "不明"
            q = f"質:{s['quality']}/5" if s["quality"] else ""
            lines.append(f"- {s['date']}: {dur} {q}")
    else:
        lines.append("- 記録なし")

    lines.append("## 体重")
    if data["weights"]:
        for w in data["weights"]:
            lines.append(f"- {w['date']}: {w['weight_kg']} kg")
        wts = [w["weight_kg"] for w in data["weights"]]
        if len(wts) >= 2:
            diff = wts[-1] - wts[0]
            lines.append(f"（週間変動: {'+' if diff>=0 else ''}{diff:.1f} kg）")
    else:
        lines.append("- 記録なし")

    lines.append("## 食事（代表的な品目）")
    meal_items = [m["content"] for m in data["meals"] if m["content"]][:20]
    cal_total = sum(m["calories"] or 0 for m in data["meals"])
    lines.append(f"- 合計 {cal_total} kcal / 記録 {len(data['meals'])} 品目")
    if meal_items:
        lines.append(f"- 品目例: {', '.join(meal_items[:10])}")

    lines.append("## 家計")
    income = data["finance"].get("income", 0) or 0
    expense = data["finance"].get("expense", 0) or 0
    lines.append(f"- 収入: ¥{income:,} / 支出: ¥{expense:,} / 収支: ¥{income-expense:,}")

    return "\n".join(lines)


def _call_ai(prompt: str) -> dict:
    load_dotenv(override=True)
    import openai
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたは健康・生活習慣の専門アドバイザーです。データを分析して具体的で前向きなフィードバックをJSON形式で返してください。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content
    return json.loads(text)


@bp.route("/")
def index():
    # 先週月曜をデフォルト
    last_monday = (_this_week_monday() - timedelta(weeks=1)).isoformat()
    week_start = request.args.get("week", last_monday)
    try:
        d = date.fromisoformat(week_start)
        # 月曜に正規化
        week_start = (d - timedelta(days=d.weekday())).isoformat()
    except ValueError:
        week_start = last_monday

    week_end = (date.fromisoformat(week_start) + timedelta(days=6)).isoformat()
    prev_week = (date.fromisoformat(week_start) - timedelta(weeks=1)).isoformat()
    next_week = (date.fromisoformat(week_start) + timedelta(weeks=1)).isoformat()
    label = f"{week_start} 〜 {week_end}"

    report = None
    error = None
    data = db.get_weekly_detail(week_start)

    if request.args.get("generate") == "1":
        try:
            prompt = _build_prompt(data)
            report = _call_ai(prompt)
        except Exception as e:
            error = str(e)

    return render_template(
        "report/index.html",
        module="report",
        week_start=week_start,
        week_end=week_end,
        prev_week=prev_week,
        next_week=next_week,
        label=label,
        data=data,
        report=report,
        error=error,
    )
