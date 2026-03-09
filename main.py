from dotenv import load_dotenv
load_dotenv()

from flask import Flask, redirect, url_for
from flask_login import current_user

import database as db
from extensions import login_manager
from modules import kakeibo, books, exercise, meals, sleep_log, dashboard, garbage, memo, record, report
from modules.auth import bp as auth_bp, init_oauth

app = Flask(__name__)
app.secret_key = "pos-dev-secret-key"

app.register_blueprint(kakeibo.bp)
app.register_blueprint(books.bp)
app.register_blueprint(exercise.bp)
app.register_blueprint(meals.bp)
app.register_blueprint(sleep_log.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(garbage.bp)
app.register_blueprint(memo.bp)
app.register_blueprint(record.bp)
app.register_blueprint(report.bp)
app.register_blueprint(auth_bp)

login_manager.init_app(app)
init_oauth(app)


@app.before_request
def setup():
    db.init_db()


@app.before_request
def require_login():
    if current_user.is_authenticated:
        return
    from flask import request
    endpoint = request.endpoint or ""
    if endpoint in ("static",) or endpoint.startswith("auth."):
        return
    return redirect(url_for("auth.login"))


@app.route("/")
def root():
    return redirect(url_for("dashboard.index"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
