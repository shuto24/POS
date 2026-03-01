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


def get_available_months():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT strftime('%Y-%m', date) AS month
            FROM transactions
            ORDER BY month DESC
        """).fetchall()
    return [row["month"] for row in rows]
