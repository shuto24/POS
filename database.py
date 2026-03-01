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


def get_available_months():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT strftime('%Y-%m', date) AS month
            FROM transactions
            ORDER BY month DESC
        """).fetchall()
    return [row["month"] for row in rows]
