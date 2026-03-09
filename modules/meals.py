import csv
import io
import os
from datetime import datetime
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
import database as db

bp = Blueprint("meals", __name__, url_prefix="/meals")


@bp.route("/")
def index():
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    q = request.args.get("q", "")
    meals = db.get_meals(month=month, q=q or None)
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
        q=q,
    )


@bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        date = request.form["date"]
        meal_type = request.form.get("meal_type", db.MEAL_TYPES[0])
        contents = request.form.getlist("content[]")
        qty_list = request.form.getlist("qty[]")
        calorie_list = request.form.getlist("calories[]")
        protein_list = request.form.getlist("protein[]")
        fat_list = request.form.getlist("fat[]")
        carbs_list = request.form.getlist("carbs[]")
        saved = 0
        for i, content in enumerate(contents):
            content = content.strip()
            if not content:
                continue
            qty = qty_list[i].strip() if i < len(qty_list) else ""
            full_content = f"{content} {qty}" if qty else content
            calories = calorie_list[i].strip() if i < len(calorie_list) else ""
            protein = protein_list[i].strip() if i < len(protein_list) else ""
            fat = fat_list[i].strip() if i < len(fat_list) else ""
            carbs = carbs_list[i].strip() if i < len(carbs_list) else ""
            db.add_meal(date=date, meal_type=meal_type, content=full_content,
                        calories=calories or None, memo="",
                        protein=protein or None, fat=fat or None, carbs=carbs or None)
            saved += 1
        if saved:
            flash(f"{saved} 品目の食事を記録しました", "success")
        return redirect(url_for("meals.index", month=date[:7]))

    today = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "meals/add.html",
        module="meals",
        today=today,
        meal_types=db.MEAL_TYPES,
        suggestions=db.get_meal_suggestions(),
        calorie_hints=db.get_calorie_hints(),
    )


@bp.route("/estimate", methods=["POST"])
def estimate_calories():
    try:
        from openai import OpenAI
    except ImportError:
        return jsonify({"error": "openai パッケージが未インストールです"}), 500

    # .env の変更を再起動なしで反映
    from dotenv import load_dotenv
    load_dotenv(override=True)

    data = request.get_json(silent=True) or {}
    content = data.get("content", "").strip()
    meal_type = data.get("meal_type", "")
    if not content:
        return jsonify({"error": "内容を入力してください"}), 400

    # キャッシュ確認（API呼び出し不要）
    cached = db.get_cached_nutrition(content)
    if cached is not None:
        return jsonify({**cached, "cached": True})

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY が未設定"}), 500

    client = OpenAI(api_key=api_key)
    try:
        import json as _json
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": (
                    f"次の食事の栄養素を推定してください。\n"
                    f"食事: {meal_type} {content}\n"
                    f"JSON形式で回答: {{\"calories\": 整数, \"protein\": 小数(g), "
                    f"\"fat\": 小数(g), \"carbs\": 小数(g)}}\n"
                    f"数値のみ、説明なし"
                ),
            }],
            max_tokens=80,
            response_format={"type": "json_object"},
        )
        data_parsed = _json.loads(resp.choices[0].message.content)
        calories = int(data_parsed.get("calories") or 0)
        protein = float(data_parsed.get("protein") or 0) or None
        fat = float(data_parsed.get("fat") or 0) or None
        carbs = float(data_parsed.get("carbs") or 0) or None
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    # キャッシュに保存
    if calories > 0:
        db.set_cached_nutrition(content, calories, protein, fat, carbs)

    return jsonify({"calories": calories, "protein": protein, "fat": fat, "carbs": carbs})


@bp.route("/<int:id_>/edit", methods=["GET", "POST"])
def edit(id_):
    meal = db.get_meal(id_)
    if not meal:
        flash("データが見つかりません", "warning")
        return redirect(url_for("meals.index"))
    if request.method == "POST":
        date = request.form["date"]
        meal_type = request.form["meal_type"]
        content = request.form["content"].strip()
        calories = request.form.get("calories", "").strip() or None
        memo = request.form.get("memo", "").strip()
        db.update_meal(id_, date=date, meal_type=meal_type, content=content,
                       calories=calories, memo=memo)
        flash("食事を更新しました", "success")
        return redirect(url_for("meals.index", month=date[:7]))
    return render_template(
        "meals/edit.html",
        module="meals",
        meal=meal,
        meal_types=db.MEAL_TYPES,
    )


@bp.route("/delete/<int:id_>", methods=["POST"])
def delete(id_):
    month = request.form.get("month", datetime.now().strftime("%Y-%m"))
    db.delete_meal(id_)
    return redirect(url_for("meals.index", month=month))


@bp.route("/import", methods=["POST"])
def import_csv():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("ファイルを選択してください", "warning")
        return redirect(url_for("meals.index"))

    stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
    reader = csv.DictReader(stream)
    rows, errors = [], 0
    for row in reader:
        try:
            rows.append({
                "date": row["date"].strip(),
                "meal_type": row["meal_type"].strip(),
                "content": row["content"].strip(),
                "calories": row.get("calories", "").strip(),
                "memo": row.get("memo", "").strip(),
            })
        except (KeyError, ValueError):
            errors += 1

    if rows:
        db.import_meals(rows)
        msg = f"{len(rows)} 件インポートしました"
        if errors:
            msg += f"（{errors} 件スキップ）"
        flash(msg, "success")
    else:
        flash(f"インポートできる行がありませんでした（{errors} 件エラー）", "danger")
    return redirect(url_for("meals.index"))
