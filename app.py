import os
import sqlite3
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# ── FAILLE #1 — Credentials internes Free en dur dans le code (détecté par gitleaks) ──
INTERNAL_API_TOKEN = "freetelecom_internal_api_x7k9m2p4q1"
DB_PASSWORD = "FreeProd@MySQL2024!"

DB_PATH = "subscribers.db"


def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id        INTEGER PRIMARY KEY,
            phone     TEXT,
            name      TEXT,
            email     TEXT,
            iban      TEXT,
            line_id   TEXT,
            plan      TEXT,
            data_used_gb REAL
        )
    """)
    if not conn.execute("SELECT 1 FROM subscribers LIMIT 1").fetchone():
        conn.executemany(
            "INSERT INTO subscribers (phone, name, email, iban, line_id, plan, data_used_gb) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("0612345678", "Jean Dupont",     "jean.dupont@free.fr",       "FR76 3000 6000 0112 3456 7890 189", "FBX-29471", "Freebox Ultra",       142.3),
                ("0698765432", "Marie Martin",    "marie.martin@free.fr",      "FR76 1427 8060 0001 2345 6789 012", "FBX-18293", "Freebox Revolution",  87.1),
                ("0634567890", "Ahmed Benali",    "ahmed.benali@laposte.net",  "FR76 2004 1010 0505 0013 4056 024", "FBX-44821", "Freebox Pop",         310.7),
                ("0645678901", "Sophie Leclerc",  "sophie.leclerc@yahoo.fr",   "FR76 3000 4000 0300 0000 0350 461", "FBX-57392", "Freebox Ultra",       55.2),
                ("0656789012", "Pierre Moreau",   "pierre.moreau@orange.fr",   "FR76 1820 6000 2000 6543 2100 002", "FBX-61047", "Freebox Mini 4K",     201.8),
            ],
        )
        conn.commit()
    conn.close()


@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Free DevSecOps Lab</title>
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background-color: #1a1a2e;
      background-image:
        linear-gradient(rgba(0,255,70,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,70,0.03) 1px, transparent 1px);
      background-size: 32px 32px;
      font-family: 'Press Start 2P', monospace;
      color: #00ff46;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 20px;
    }
    .container {
      max-width: 860px;
      width: 100%;
      border: 4px solid #00ff46;
      box-shadow: 0 0 30px #00ff4655, inset 0 0 30px #00ff4608;
      padding: 40px;
      background: #0d0d1a;
      image-rendering: pixelated;
    }
    h1 {
      font-size: 1.4rem;
      text-align: center;
      color: #fff;
      text-shadow: 3px 3px #00ff46, -1px -1px #005c1a;
      margin-bottom: 8px;
      letter-spacing: 2px;
    }
    .subtitle {
      text-align: center;
      font-size: 0.45rem;
      color: #00cc38;
      margin-bottom: 36px;
      letter-spacing: 1px;
    }
    .warning-box {
      border: 3px solid #ff4444;
      background: #1a0000;
      padding: 14px 18px;
      margin-bottom: 32px;
      font-size: 0.42rem;
      color: #ff6666;
      line-height: 2;
    }
    .warning-box span { color: #ff2222; font-size: 0.5rem; }
    .section-title {
      font-size: 0.5rem;
      color: #ffdd00;
      margin-bottom: 14px;
      border-bottom: 2px solid #ffdd0044;
      padding-bottom: 6px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 32px;
      font-size: 0.38rem;
    }
    th {
      color: #ffdd00;
      padding: 10px 14px;
      text-align: left;
      border-bottom: 2px solid #ffdd0033;
    }
    td {
      padding: 10px 14px;
      border-bottom: 1px solid #00ff4622;
      line-height: 2;
    }
    td a {
      color: #00cfff;
      text-decoration: none;
    }
    td a:hover { text-decoration: underline; color: #fff; }
    tr:hover td { background: #00ff4608; }
    .badge-vuln { color: #ff4444; }
    .badge-safe { color: #00ff46; }
    .footer {
      text-align: center;
      font-size: 0.35rem;
      color: #00ff4666;
      margin-top: 10px;
      line-height: 2.5;
    }
    .blink { animation: blink 1s step-end infinite; }
    @keyframes blink { 50% { opacity: 0; } }
  </style>
</head>
<body>
  <div class="container">
    <h1>[ FREE DEVSECOPS LAB ]</h1>
    <p class="subtitle">>>> API INTERNE GESTION ABONNES — ENVIRONNEMENT DE LAB <<<</p>

    <div class="warning-box">
      <span>⚠ ATTENTION</span><br>
      Ce code contient des failles INTENTIONNELLES.<br>
      Objectif : les identifier, comprendre leur impact, et les corriger.<br>
      Ne jamais déployer ce code en production.
    </div>

    <p class="section-title">▶ ENDPOINTS DISPONIBLES</p>
    <table>
      <tr>
        <th>Route</th>
        <th>Exemple</th>
        <th>Statut</th>
      </tr>
      <tr>
        <td>/subscriber</td>
        <td><a href="/subscriber?phone=0612345678">/subscriber?phone=0612345678</a></td>
        <td class="badge-vuln">⚠ FAILLE SQL</td>
      </tr>
      <tr>
        <td>/line-status</td>
        <td><a href="/line-status?id=FBX-29471">/line-status?id=FBX-29471</a></td>
        <td class="badge-safe">✔ OK</td>
      </tr>
      <tr>
        <td>/invoice</td>
        <td><a href="/invoice?account=1">/invoice?account=1</a></td>
        <td class="badge-safe">✔ OK</td>
      </tr>
      <tr>
        <td>/health</td>
        <td><a href="/health">/health</a></td>
        <td class="badge-vuln">⚠ FUITE RGPD</td>
      </tr>
    </table>

    <p class="section-title">▶ FAILLES A CORRIGER</p>
    <table>
      <tr><th>#</th><th>Faille</th><th>Outil CI</th></tr>
      <tr><td>1</td><td>Credentials en dur dans le code</td><td>Gitleaks</td></tr>
      <tr><td>2</td><td>Injection SQL sur /subscriber</td><td>Semgrep</td></tr>
      <tr><td>3</td><td>Données RGPD exposées dans /health</td><td>Semgrep</td></tr>
      <tr><td>4</td><td>debug=True en production</td><td>Semgrep</td></tr>
      <tr><td>5</td><td>Image Docker python:3.9 avec CVE</td><td>Trivy</td></tr>
    </table>

    <p class="footer">
      Lab DevSecOps — Formateur : Yacine Romdhani<br>
      <span class="blink">_</span>
    </p>
  </div>
</body>
</html>
""")


@app.route("/subscriber")
def subscriber():
    # ── FAILLE #2 — Injection SQL sur la recherche par numéro (détecté par Semgrep) ──
    # Impact réel : exposition de l'ensemble de la base abonnés Free (millions de lignes)
    phone = request.args.get("phone", "")
    conn = get_db()
    query = "SELECT id, phone, name, email, plan, data_used_gb FROM subscribers WHERE phone = '" + phone + "'"
    rows = conn.execute(query).fetchall()
    conn.close()
    keys = ["id", "phone", "name", "email", "plan", "data_used_gb"]
    return jsonify([dict(zip(keys, r)) for r in rows])


@app.route("/line-status")
def line_status():
    line_id = request.args.get("id", "")
    conn = get_db()
    row = conn.execute(
        "SELECT name, plan, data_used_gb FROM subscribers WHERE line_id = ?", (line_id,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Ligne introuvable"}), 404
    return jsonify({
        "line_id":              line_id,
        "status":               "active",
        "subscriber":           row[0],
        "plan":                 row[1],
        "data_used_gb":         row[2],
        "sync_down_mbps":       987,
        "sync_up_mbps":         642,
    })


@app.route("/invoice")
def invoice():
    account = request.args.get("account", "")
    conn = get_db()
    row = conn.execute(
        "SELECT name, email, plan FROM subscribers WHERE id = ?", (account,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Compte introuvable"}), 404
    return jsonify({
        "account":    account,
        "subscriber": row[0],
        "email":      row[1],
        "plan":       row[2],
        "amount_eur": 39.99,
        "period":     "mai 2026",
        "status":     "payée",
    })


@app.route("/health")
def health():
    # ── FAILLE #3 — Données RGPD + credentials exposés dans le healthcheck ──
    # Violation directe du RGPD : IBAN, email, token interne accessibles sans auth
    conn = get_db()
    last = conn.execute(
        "SELECT name, email, iban FROM subscribers ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return jsonify({
        "status":           "ok",
        "internal_token":   INTERNAL_API_TOKEN,
        "db_host":          "prod-mysql-01.infra.free.fr",
        "db_password":      DB_PASSWORD,
        "last_subscriber":  {"name": last[0], "email": last[1], "iban": last[2]},
    })


if __name__ == "__main__":
    init_db()
    # ── FAILLE #4 — debug=True = console Werkzeug = exécution de code arbitraire ──
    app.run(host="0.0.0.0", port=5000, debug=True)
