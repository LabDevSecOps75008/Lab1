import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

# ============================================================
# SECRETS HARDCODÉS — à détecter avec Gitleaks
# ============================================================

API_TOKEN             = "freemobile_api_token_4f8a2c1e9b3d7f05"
JWT_SECRET            = "fm-jwt-s1gn1ng-k3y-pr0d-2024"
DB_PASSWORD           = "Fr33M0b!leProd2024"
AWS_ACCESS_KEY_ID     = "LAB_AKIAIOSFODNN7FREEMOB"
AWS_SECRET_ACCESS_KEY = "LAB_wJalrXUtnFEMI/K7MDENG/bPxRfiCYFREEMOBILE"

DB_PATH = "freemobile.db"


def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id     INTEGER PRIMARY KEY,
            msisdn TEXT,
            name   TEXT,
            plan   TEXT
        )
    """)
    if not conn.execute("SELECT 1 FROM subscribers LIMIT 1").fetchone():
        conn.executemany("INSERT INTO subscribers VALUES (?,?,?,?)", [
            (1, "0612345678", "Jean Dupont",  "Free 5G 210Go"),
            (2, "0698765432", "Marie Martin", "Free 4G 80Go"),
            (3, "0634567890", "Ahmed Benali", "Free 5G 130Go"),
        ])
        conn.commit()
    conn.close()


@app.route("/subscriber")
def subscriber():
    msisdn = request.args.get("msisdn", "")
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM subscribers WHERE msisdn = ?", (msisdn,)
    ).fetchall()
    conn.close()
    return jsonify([{"id": r[0], "msisdn": r[1], "name": r[2], "plan": r[3]} for r in rows])


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
