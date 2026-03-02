from flask import Flask, redirect, url_for

import database as db
from modules import kakeibo, books, exercise, meals, sleep_log

app = Flask(__name__)

app.register_blueprint(kakeibo.bp)
app.register_blueprint(books.bp)
app.register_blueprint(exercise.bp)
app.register_blueprint(meals.bp)
app.register_blueprint(sleep_log.bp)


@app.before_request
def setup():
    db.init_db()


@app.route("/")
def root():
    return redirect(url_for("kakeibo.index"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
