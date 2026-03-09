import sqlite3
from datetime import datetime

DB_PATH = "kakeibo.db"

INCOME_CATEGORIES = ["給与", "副業", "賞与", "その他"]
EXPENSE_CATEGORIES = ["食費", "交通費", "住居費", "光熱費", "娯楽費", "医療費", "衣類", "通信費", "その他"]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount INTEGER NOT NULL,
                memo TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                period_type TEXT NOT NULL,
                month TEXT,
                amount INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                is_preset INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 999,
                UNIQUE(type, name)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT,
                status TEXT NOT NULL DEFAULT 'unread',
                rating INTEGER,
                total_pages INTEGER,
                current_page INTEGER,
                start_date TEXT,
                end_date TEXT,
                memo TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                duration INTEGER NOT NULL,
                distance REAL,
                calories INTEGER,
                memo TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                meal_type TEXT NOT NULL,
                content TEXT NOT NULL,
                calories INTEGER,
                memo TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sleep_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                sleep_time TEXT NOT NULL,
                wake_time TEXT NOT NULL,
                duration_min INTEGER,
                quality INTEGER,
                memo TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                name TEXT,
                email TEXT,
                avatar_url TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(provider, provider_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT,
                tags TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meal_calorie_cache (
                content_key TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                calories INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weight_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                weight_kg REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        # プリセットカテゴリを初期投入（既存なら無視）
        for i, name in enumerate(INCOME_CATEGORIES):
            conn.execute(
                "INSERT OR IGNORE INTO categories (type, name, is_preset, sort_order) VALUES (?,?,1,?)",
                ("income", name, i),
            )
        for i, name in enumerate(EXPENSE_CATEGORIES):
            conn.execute(
                "INSERT OR IGNORE INTO categories (type, name, is_preset, sort_order) VALUES (?,?,1,?)",
                ("expense", name, i),
            )


def add_transaction(date, type_, category, amount, memo=""):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO transactions (date, type, category, amount, memo, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (date, type_, category, amount, memo, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


def delete_transaction(id_):
    with get_connection() as conn:
        conn.execute("DELETE FROM transactions WHERE id = ?", (id_,))


def get_transactions(month=None, q=None):
    with get_connection() as conn:
        conditions = []
        params = []
        if month:
            conditions.append("strftime('%Y-%m', date) = ?")
            params.append(month)
        if q:
            conditions.append("(category LIKE ? OR memo LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM transactions {where} ORDER BY date DESC, id DESC",
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def get_monthly_summary():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                strftime('%Y-%m', date) AS month,
                SUM(CASE WHEN type='income' THEN amount ELSE 0 END) AS income,
                SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expense
            FROM transactions
            GROUP BY month
            ORDER BY month DESC
        """).fetchall()
    return [dict(row) for row in rows]


def get_category_summary(month=None):
    with get_connection() as conn:
        if month:
            rows = conn.execute("""
                SELECT type, category, SUM(amount) AS total
                FROM transactions
                WHERE strftime('%Y-%m', date) = ?
                GROUP BY type, category
                ORDER BY type, total DESC
            """, (month,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT type, category, SUM(amount) AS total
                FROM transactions
                GROUP BY type, category
                ORDER BY type, total DESC
            """).fetchall()
    return [dict(row) for row in rows]


def upsert_budget(year, type_, category, period_type, amount, month=None):
    with get_connection() as conn:
        if period_type == "monthly_variable":
            conn.execute(
                "DELETE FROM budgets WHERE year=? AND type=? AND category=? AND period_type='monthly_variable' AND month=?",
                (year, type_, category, month),
            )
            conn.execute(
                "INSERT INTO budgets (year, type, category, period_type, month, amount) VALUES (?,?,?,?,?,?)",
                (year, type_, category, period_type, month, amount),
            )
        else:
            conn.execute(
                "DELETE FROM budgets WHERE year=? AND type=? AND category=? AND period_type != 'monthly_variable'",
                (year, type_, category),
            )
            conn.execute(
                "INSERT INTO budgets (year, type, category, period_type, month, amount) VALUES (?,?,?,?,NULL,?)",
                (year, type_, category, period_type, amount),
            )


def delete_budget(year, type_, category):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM budgets WHERE year=? AND type=? AND category=?",
            (year, type_, category),
        )


def get_budgets(year):
    """カテゴリごとに予算情報をまとめた辞書を返す。
    キー: (type, category)
    値: {period_type, amount(yearly/monthly_fixed時), month_amounts(monthly_variable時: {month: amount})}
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM budgets WHERE year=? ORDER BY type, category, month",
            (year,),
        ).fetchall()

    result = {}
    for row in rows:
        key = (row["type"], row["category"])
        if row["period_type"] == "monthly_variable":
            if key not in result:
                result[key] = {"period_type": "monthly_variable", "month_amounts": {}}
            result[key]["month_amounts"][row["month"]] = row["amount"]
        else:
            result[key] = {"period_type": row["period_type"], "amount": row["amount"]}
    return result


def get_monthly_budget(year, month_str, type_, category):
    """指定月の予算額を返す。未設定なら None。yearly は ÷12 で返す。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM budgets WHERE year=? AND type=? AND category=?",
            (year, type_, category),
        ).fetchall()

    if not rows:
        return None

    period_type = rows[0]["period_type"]
    if period_type == "yearly":
        return rows[0]["amount"] // 12
    if period_type == "monthly_fixed":
        return rows[0]["amount"]
    # monthly_variable
    for row in rows:
        if row["month"] == month_str:
            return row["amount"]
    return None


def get_yearly_budget(year, type_, category):
    """指定カテゴリの年予算額を返す。未設定なら None。monthly_fixed は ×12 で返す。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM budgets WHERE year=? AND type=? AND category=?",
            (year, type_, category),
        ).fetchall()

    if not rows:
        return None

    period_type = rows[0]["period_type"]
    if period_type == "yearly":
        return rows[0]["amount"]
    if period_type == "monthly_fixed":
        return rows[0]["amount"] * 12
    # monthly_variable: 全月合計
    return sum(row["amount"] for row in rows)


def get_yearly_actual(year, type_, category):
    """指定カテゴリの年間実績合計を返す。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT SUM(amount) AS total FROM transactions WHERE strftime('%Y', date)=? AND type=? AND category=?",
            (str(year), type_, category),
        ).fetchone()
    return row["total"] or 0


def get_categories(type_=None):
    """カテゴリ名リストを sort_order 順で返す。type_ 指定時はその種別のみ。"""
    with get_connection() as conn:
        if type_:
            rows = conn.execute(
                "SELECT name FROM categories WHERE type=? ORDER BY sort_order, id",
                (type_,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT type, name, is_preset FROM categories ORDER BY type, sort_order, id"
            ).fetchall()
    return [dict(row) for row in rows] if type_ is None else [row["name"] for row in rows]


def add_category(type_, name):
    """ユーザー追加カテゴリを登録する。既存の場合は何もしない。"""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO categories (type, name, is_preset, sort_order) VALUES (?,?,0,999)",
            (type_, name),
        )


def delete_category(type_, name):
    """カスタムカテゴリを削除する。プリセットや取引が残っている場合は削除しない。
    戻り値: 'ok' | 'preset' | 'has_transactions'
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT is_preset FROM categories WHERE type=? AND name=?", (type_, name)
        ).fetchone()
        if not row or row["is_preset"]:
            return "preset"
        count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM transactions WHERE type=? AND category=?",
            (type_, name),
        ).fetchone()["cnt"]
        if count > 0:
            return "has_transactions"
        conn.execute("DELETE FROM categories WHERE type=? AND name=?", (type_, name))
    return "ok"


def get_categories_detail(type_=None):
    """管理ページ用: is_preset + 取引件数付きで全カテゴリを返す。"""
    with get_connection() as conn:
        if type_:
            rows = conn.execute("""
                SELECT c.type, c.name, c.is_preset,
                       COUNT(t.id) AS tx_count
                FROM categories c
                LEFT JOIN transactions t ON t.type=c.type AND t.category=c.name
                WHERE c.type=?
                GROUP BY c.type, c.name, c.is_preset
                ORDER BY c.sort_order, c.id
            """, (type_,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT c.type, c.name, c.is_preset,
                       COUNT(t.id) AS tx_count
                FROM categories c
                LEFT JOIN transactions t ON t.type=c.type AND t.category=c.name
                GROUP BY c.type, c.name, c.is_preset
                ORDER BY c.type, c.sort_order, c.id
            """).fetchall()
    return [dict(row) for row in rows]


def get_available_months():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT strftime('%Y-%m', date) AS month
            FROM transactions
            ORDER BY month DESC
        """).fetchall()
    return [row["month"] for row in rows]


# ── 読書管理 ──────────────────────────────────────────
BOOK_STATUSES = {"wishlist": "読みたい", "unread": "積読", "reading": "読書中", "done": "読了"}

def get_books(status=None, q=None):
    with get_connection() as conn:
        conditions = []
        params = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if q:
            conditions.append("(title LIKE ? OR author LIKE ? OR memo LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM books {where} ORDER BY created_at DESC",
            params,
        ).fetchall()
    return [dict(r) for r in rows]

def add_book(title, author, status, rating, total_pages, start_date, end_date, memo):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO books (title,author,status,rating,total_pages,start_date,end_date,memo,created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (title, author, status, rating or None, total_pages or None,
             start_date or None, end_date or None, memo,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

def update_book_status(id_, status, current_page=None, end_date=None):
    with get_connection() as conn:
        conn.execute(
            "UPDATE books SET status=?, current_page=?, end_date=? WHERE id=?",
            (status, current_page, end_date, id_),
        )

def delete_book(id_):
    with get_connection() as conn:
        conn.execute("DELETE FROM books WHERE id=?", (id_,))


# ── 運動管理 ──────────────────────────────────────────
EXERCISE_TYPES = ["ランニング", "ウォーキング", "筋トレ", "水泳", "サイクリング", "ヨガ", "ストレッチ", "その他"]

def get_exercises(month=None, q=None):
    with get_connection() as conn:
        conditions = []
        params = []
        if month:
            conditions.append("strftime('%Y-%m',date) = ?")
            params.append(month)
        if q:
            conditions.append("(type LIKE ? OR memo LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM exercises {where} ORDER BY date DESC, id DESC",
            params,
        ).fetchall()
    return [dict(r) for r in rows]

def add_exercise(date, type_, duration, distance, calories, memo):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO exercises (date,type,duration,distance,calories,memo,created_at) VALUES (?,?,?,?,?,?,?)",
            (date, type_, duration, distance or None, calories or None, memo,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

def get_exercise(id_):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM exercises WHERE id=?", (id_,)).fetchone()
    return dict(row) if row else None


def update_exercise(id_, type_, duration, distance, calories, memo):
    with get_connection() as conn:
        conn.execute(
            "UPDATE exercises SET type=?,duration=?,distance=?,calories=?,memo=? WHERE id=?",
            (type_, duration, distance or None, calories or None, memo, id_),
        )


def delete_exercise(id_):
    with get_connection() as conn:
        conn.execute("DELETE FROM exercises WHERE id=?", (id_,))

def get_exercise_months():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT strftime('%Y-%m',date) AS month FROM exercises ORDER BY month DESC"
        ).fetchall()
    return [r["month"] for r in rows]


# ── 食事管理 ──────────────────────────────────────────
MEAL_TYPES = ["朝食", "昼食", "夕食", "間食"]

def get_meals(month=None, q=None):
    with get_connection() as conn:
        conditions = []
        params = []
        if month:
            conditions.append("strftime('%Y-%m',date) = ?")
            params.append(month)
        if q:
            conditions.append("(content LIKE ? OR meal_type LIKE ? OR memo LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM meals {where} ORDER BY date DESC, id DESC",
            params,
        ).fetchall()
    return [dict(r) for r in rows]

def add_meal(date, meal_type, content, calories, memo):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO meals (date,meal_type,content,calories,memo,created_at) VALUES (?,?,?,?,?,?)",
            (date, meal_type, content, calories or None, memo,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

def get_meal(id_):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM meals WHERE id = ?", (id_,)).fetchone()
    return dict(row) if row else None


def update_meal(id_, date, meal_type, content, calories, memo):
    with get_connection() as conn:
        conn.execute(
            "UPDATE meals SET date=?, meal_type=?, content=?, calories=?, memo=? WHERE id=?",
            (date, meal_type, content, calories or None, memo, id_),
        )


def delete_meal(id_):
    with get_connection() as conn:
        conn.execute("DELETE FROM meals WHERE id=?", (id_,))

def get_meal_months():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT strftime('%Y-%m',date) AS month FROM meals ORDER BY month DESC"
        ).fetchall()
    return [r["month"] for r in rows]


def get_meal_suggestions():
    """過去の食事記録から品目名リストを返す（重複除去・ソート済み）"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT content FROM meals WHERE content != '' ORDER BY content"
        ).fetchall()
    return [r["content"] for r in rows]


def get_calorie_hints():
    """キャッシュテーブルから {content_key: calories} の辞書を返す"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT content_key, calories FROM meal_calorie_cache"
        ).fetchall()
    return {r["content_key"]: r["calories"] for r in rows}


def get_cached_calories(content):
    key = content.lower().strip()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT calories FROM meal_calorie_cache WHERE content_key = ?", (key,)
        ).fetchone()
    return row["calories"] if row else None


def set_cached_calories(content, calories):
    key = content.lower().strip()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO meal_calorie_cache (content_key, content, calories, updated_at)"
            " VALUES (?,?,?,?)",
            (key, content, calories, now),
        )


# ── 睡眠管理 ──────────────────────────────────────────
def _calc_duration(sleep_time, wake_time):
    """HH:MM 2つから睡眠時間(分)を計算する。日跨ぎ対応。"""
    try:
        sh, sm = map(int, sleep_time.split(":"))
        wh, wm = map(int, wake_time.split(":"))
        total = wh * 60 + wm - (sh * 60 + sm)
        if total <= 0:
            total += 24 * 60
        return total
    except Exception:
        return None

def get_sleep_logs(month=None, q=None):
    with get_connection() as conn:
        conditions = []
        params = []
        if month:
            conditions.append("strftime('%Y-%m',date) = ?")
            params.append(month)
        if q:
            conditions.append("memo LIKE ?")
            params.append(f"%{q}%")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM sleep_logs {where} ORDER BY date DESC, id DESC",
            params,
        ).fetchall()
    return [dict(r) for r in rows]

def add_sleep_log(date, sleep_time, wake_time, quality, memo):
    duration = _calc_duration(sleep_time, wake_time)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sleep_logs (date,sleep_time,wake_time,duration_min,quality,memo,created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (date, sleep_time, wake_time, duration, quality or None, memo,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

def delete_sleep_log(id_):
    with get_connection() as conn:
        conn.execute("DELETE FROM sleep_logs WHERE id=?", (id_,))

def get_sleep_months():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT strftime('%Y-%m',date) AS month FROM sleep_logs ORDER BY month DESC"
        ).fetchall()
    return [r["month"] for r in rows]


# ── 一括インポート ──────────────────────────────────────────

def import_transactions(rows):
    """rows: list of dict {date, type, category, amount, memo}"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO transactions (date,type,category,amount,memo,created_at) VALUES (?,?,?,?,?,?)",
            [(r["date"], r["type"], r["category"], int(r["amount"]), r.get("memo",""), now) for r in rows],
        )
    return len(rows)


def import_books(rows):
    """rows: list of dict {title, author, status, rating, total_pages, start_date, end_date, memo}"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO books (title,author,status,rating,total_pages,start_date,end_date,memo,created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            [(r["title"], r.get("author",""), r.get("status","unread") or "unread",
              int(r["rating"]) if r.get("rating") else None,
              int(r["total_pages"]) if r.get("total_pages") else None,
              r.get("start_date") or None, r.get("end_date") or None,
              r.get("memo",""), now) for r in rows],
        )
    return len(rows)


def import_exercises(rows):
    """rows: list of dict {date, type, duration, distance, calories, memo}"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO exercises (date,type,duration,distance,calories,memo,created_at) VALUES (?,?,?,?,?,?,?)",
            [(r["date"], r["type"], int(r["duration"]),
              float(r["distance"]) if r.get("distance") else None,
              int(r["calories"]) if r.get("calories") else None,
              r.get("memo",""), now) for r in rows],
        )
    return len(rows)


def import_meals(rows):
    """rows: list of dict {date, meal_type, content, calories, memo}"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO meals (date,meal_type,content,calories,memo,created_at) VALUES (?,?,?,?,?,?)",
            [(r["date"], r["meal_type"], r["content"],
              int(r["calories"]) if r.get("calories") else None,
              r.get("memo",""), now) for r in rows],
        )
    return len(rows)


def import_sleep_logs(rows):
    """rows: list of dict {date, sleep_time, wake_time, quality, memo}"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        data = []
        for r in rows:
            dur = _calc_duration(r["sleep_time"], r["wake_time"])
            data.append((r["date"], r["sleep_time"], r["wake_time"], dur,
                         int(r["quality"]) if r.get("quality") else None,
                         r.get("memo",""), now))
        conn.executemany(
            "INSERT INTO sleep_logs (date,sleep_time,wake_time,duration_min,quality,memo,created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            data,
        )
    return len(rows)


# ── ダッシュボード集計 ──────────────────────────────────────────

def _dashboard_kakeibo(conn, where, params):
    row = conn.execute(
        f"SELECT SUM(CASE WHEN type='income' THEN amount ELSE 0 END) AS income,"
        f" SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expense"
        f" FROM transactions {where}", params
    ).fetchone()
    income = row["income"] or 0
    expense = row["expense"] or 0
    return {"income": income, "expense": expense, "balance": income - expense}


def _dashboard_exercise(conn, where, params):
    row = conn.execute(
        f"SELECT SUM(duration) AS total_min, SUM(calories) AS total_cal, COUNT(*) AS count"
        f" FROM exercises {where}", params
    ).fetchone()
    return {
        "total_min": row["total_min"] or 0,
        "total_cal": row["total_cal"] or 0,
        "count": row["count"] or 0,
    }


def _dashboard_meals(conn, where, params, date_col="date"):
    row = conn.execute(
        f"SELECT SUM(calories) AS total_cal, COUNT(*) AS count,"
        f" COUNT(DISTINCT {date_col}) AS days"
        f" FROM meals {where}", params
    ).fetchone()
    total_cal = row["total_cal"] or 0
    days = row["days"] or 1
    return {
        "total_cal": total_cal,
        "count": row["count"] or 0,
        "avg_cal": total_cal // days if days else 0,
    }


def _dashboard_sleep(conn, where, params):
    row = conn.execute(
        f"SELECT AVG(duration_min) AS avg_min, AVG(quality) AS avg_quality, COUNT(*) AS count"
        f" FROM sleep_logs {where}", params
    ).fetchone()
    avg_min = int(row["avg_min"]) if row["avg_min"] else 0
    avg_q = round(row["avg_quality"], 1) if row["avg_quality"] else 0
    return {"avg_min": avg_min, "avg_quality": avg_q, "count": row["count"] or 0}


def _dashboard_books(conn):
    rows = conn.execute(
        "SELECT status, COUNT(*) AS cnt FROM books GROUP BY status"
    ).fetchall()
    counts = {r["status"]: r["cnt"] for r in rows}
    return {
        "done": counts.get("done", 0),
        "reading": counts.get("reading", 0),
        "unread": counts.get("unread", 0),
    }


def get_dashboard_day(day_str: str) -> dict:
    """特定の1日の集計を返す。"""
    where = "WHERE date = ?"
    params = [day_str]
    with get_connection() as conn:
        return {
            "kakeibo": _dashboard_kakeibo(conn, where, params),
            "exercise": _dashboard_exercise(conn, where, params),
            "meals": _dashboard_meals(conn, where, params),
            "sleep": _dashboard_sleep(conn, where, params),
            "books": _dashboard_books(conn),
        }


def get_dashboard_week(week_start: str) -> dict:
    """week_start (YYYY-MM-DD, 月曜) から7日間の集計を返す。"""
    from datetime import date, timedelta
    d = date.fromisoformat(week_start)
    week_end = (d + timedelta(days=6)).isoformat()
    where = "WHERE date BETWEEN ? AND ?"
    params = [week_start, week_end]
    with get_connection() as conn:
        return {
            "kakeibo": _dashboard_kakeibo(conn, where, params),
            "exercise": _dashboard_exercise(conn, where, params),
            "meals": _dashboard_meals(conn, where, params),
            "sleep": _dashboard_sleep(conn, where, params),
            "books": _dashboard_books(conn),
        }


def get_dashboard_month(month_str: str) -> dict:
    """YYYY-MM の月集計を返す。"""
    where = "WHERE strftime('%Y-%m', date) = ?"
    params = [month_str]
    with get_connection() as conn:
        return {
            "kakeibo": _dashboard_kakeibo(conn, where, params),
            "exercise": _dashboard_exercise(conn, where, params),
            "meals": _dashboard_meals(conn, where, params),
            "sleep": _dashboard_sleep(conn, where, params),
            "books": _dashboard_books(conn),
        }


def get_dashboard_year(year: int) -> dict:
    """年集計 + 月別時系列データを返す。"""
    where = "WHERE strftime('%Y', date) = ?"
    params = [str(year)]
    with get_connection() as conn:
        summary = {
            "kakeibo": _dashboard_kakeibo(conn, where, params),
            "exercise": _dashboard_exercise(conn, where, params),
            "meals": _dashboard_meals(conn, where, params),
            "sleep": _dashboard_sleep(conn, where, params),
            "books": _dashboard_books(conn),
        }
        # 月別時系列
        months = [f"{year}-{m:02d}" for m in range(1, 13)]
        series = []
        for m in months:
            mp = [m]
            mw = "WHERE strftime('%Y-%m', date) = ?"
            k = _dashboard_kakeibo(conn, mw, mp)
            e = _dashboard_exercise(conn, mw, mp)
            ml = _dashboard_meals(conn, mw, mp)
            sl = _dashboard_sleep(conn, mw, mp)
            series.append({
                "month": m,
                "income": k["income"],
                "expense": k["expense"],
                "ex_min": e["total_min"],
                "meal_cal": ml["total_cal"],
                "sleep_min": sl["avg_min"],
            })
        summary["month_series"] = series
    return summary


# ── ユーザー管理 ──────────────────────────────────────────

def get_user_by_id(id_):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (id_,)).fetchone()
    return dict(row) if row else None


def get_or_create_user(provider, provider_id, name, email, avatar_url):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (provider, provider_id, name, email, avatar_url, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (provider, provider_id, name, email, avatar_url, now),
        )
        row = conn.execute(
            "SELECT * FROM users WHERE provider=? AND provider_id=?",
            (provider, provider_id),
        ).fetchone()
    return dict(row)


# ── メモ管理 ──────────────────────────────────────────

def get_memos(tag=None, q=None):
    with get_connection() as conn:
        conditions, params = [], []
        if tag:
            conditions.append("(',' || tags || ',') LIKE ?")
            params.append(f"%,{tag},%")
        if q:
            conditions.append("(title LIKE ? OR body LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM memos {where} ORDER BY updated_at DESC",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def get_memo(id_):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM memos WHERE id = ?", (id_,)).fetchone()
    return dict(row) if row else None


def add_memo(title, body, tags):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO memos (title, body, tags, created_at, updated_at) VALUES (?,?,?,?,?)",
            (title, body or "", tags or "", now, now),
        )


def update_memo(id_, title, body, tags):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            "UPDATE memos SET title=?, body=?, tags=?, updated_at=? WHERE id=?",
            (title, body or "", tags or "", now, id_),
        )


def delete_memo(id_):
    with get_connection() as conn:
        conn.execute("DELETE FROM memos WHERE id=?", (id_,))


def get_all_memo_tags():
    with get_connection() as conn:
        rows = conn.execute("SELECT tags FROM memos WHERE tags != ''").fetchall()
    tags = set()
    for row in rows:
        for t in row["tags"].split(","):
            t = t.strip()
            if t:
                tags.add(t)
    return sorted(tags)


# ── 体重管理 ──────────────────────────────────────────

def add_or_update_weight(date, weight_kg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO weight_logs (date, weight_kg, created_at) VALUES (?,?,?)"
            " ON CONFLICT(date) DO UPDATE SET weight_kg=excluded.weight_kg",
            (date, weight_kg, now),
        )


def get_weight_logs(month=None):
    with get_connection() as conn:
        if month:
            rows = conn.execute(
                "SELECT * FROM weight_logs WHERE strftime('%Y-%m', date) = ? ORDER BY date",
                (month,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM weight_logs ORDER BY date ASC LIMIT 365"
            ).fetchall()
    return [dict(r) for r in rows]
