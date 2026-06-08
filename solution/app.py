import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

DB_PATH = "shop.db"


def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_db()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price REAL)"
    )
    if not conn.execute("SELECT 1 FROM products LIMIT 1").fetchone():
        conn.executemany(
            "INSERT INTO products (name, price) VALUES (?, ?)",
            [("Clavier", 49.9), ("Souris", 19.9), ("Ecran", 199.0)],
        )
        conn.commit()
    conn.close()


@app.route("/product")
def product():
    pid = request.args.get("id")
    conn = get_db()
    rows = conn.execute(
        "SELECT name, price FROM products WHERE id = ?", (pid,)
    ).fetchall()
    conn.close()
    return jsonify(rows)


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
