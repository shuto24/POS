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


def get_transactions(month=None):
    with get_connection() as conn:
        if month:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE strftime('%Y-%m', date) = ? ORDER BY date DESC, id DESC",
                (month,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY date DESC, id DESC"
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
BOOK_STATUSES = {"unread": "積読", "reading": "読書中", "done": "読了"}

def get_books(status=None):
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM books WHERE status=? ORDER BY created_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY created_at DESC").fetchall()
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

def get_exercises(month=None):
    with get_connection() as conn:
        if month:
            rows = conn.execute(
                "SELECT * FROM exercises WHERE strftime('%Y-%m',date)=? ORDER BY date DESC, id DESC",
                (month,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM exercises ORDER BY date DESC, id DESC").fetchall()
    return [dict(r) for r in rows]

def add_exercise(date, type_, duration, distance, calories, memo):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO exercises (date,type,duration,distance,calories,memo,created_at) VALUES (?,?,?,?,?,?,?)",
            (date, type_, duration, distance or None, calories or None, memo,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
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

def get_meals(month=None):
    with get_connection() as conn:
        if month:
            rows = conn.execute(
                "SELECT * FROM meals WHERE strftime('%Y-%m',date)=? ORDER BY date DESC, id DESC",
                (month,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM meals ORDER BY date DESC, id DESC").fetchall()
    return [dict(r) for r in rows]

def add_meal(date, meal_type, content, calories, memo):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO meals (date,meal_type,content,calories,memo,created_at) VALUES (?,?,?,?,?,?)",
            (date, meal_type, content, calories or None, memo,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
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

def get_sleep_logs(month=None):
    with get_connection() as conn:
        if month:
            rows = conn.execute(
                "SELECT * FROM sleep_logs WHERE strftime('%Y-%m',date)=? ORDER BY date DESC, id DESC",
                (month,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM sleep_logs ORDER BY date DESC, id DESC").fetchall()
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
