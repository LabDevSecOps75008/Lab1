import os
import sqlite3
import hashlib
import hmac
import base64
import json
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# =============================================================================
# ██████╗  FAILLES VOLONTAIRES — CONTEXTE FREE TELECOM
# ██╔══██╗ Ce fichier contient 5 types de secrets intentionnellement exposés.
# ██████╔╝ Objectif : les détecter avec Gitleaks + TruffleHog et les corriger.
# ╚═════╝
# =============================================================================

# FAILLE #1 — Token API interne Free (détecté par Gitleaks — pattern connu)
FREE_INTERNAL_TOKEN = "freetelecom_internal_api_x7k9m2p4q1"

# FAILLE #2 — Secret JWT (signature des sessions abonnés — détecté par TruffleHog)
JWT_SECRET = "fr33-s3cr3t-jwt-pr0d-2024!"

# FAILLE #3 — Password base de données production (détecté par Gitleaks)
DB_PASSWORD = "FreeProd@MySQL2024!"

# FAILLE #4 — Credentials AWS S3 (backups facturation — détecté par Gitleaks + TruffleHog)
AWS_ACCESS_KEY_ID     = "AKIAIOSFODNN7FREETEL"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYFREETELECOM"

# FAILLE #5 — OAuth2 client secret (SSO interne Free — détecté par TruffleHog entropie)
OAUTH2_CLIENT_SECRET = "oauth2_free_9f8e7d6c5b4a3210abcdef1234567890"

DB_PATH = "subscribers.db"


def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id           INTEGER PRIMARY KEY,
            phone        TEXT,
            name         TEXT,
            email        TEXT,
            iban         TEXT,
            line_id      TEXT,
            plan         TEXT,
            data_used_gb REAL,
            account_ref  TEXT
        )
    """)
    if not conn.execute("SELECT 1 FROM subscribers LIMIT 1").fetchone():
        conn.executemany(
            """INSERT INTO subscribers
               (phone, name, email, iban, line_id, plan, data_used_gb, account_ref)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                ("0612345678", "Jean Dupont",    "jean.dupont@free.fr",      "FR76 3000 6000 0112 3456 7890 189", "FBX-29471", "Freebox Ultra",      142.3, "FR-88412"),
                ("0698765432", "Marie Martin",   "marie.martin@free.fr",     "FR76 1427 8060 0001 2345 6789 012", "FBX-18293", "Freebox Revolution", 87.1,  "FR-55301"),
                ("0634567890", "Ahmed Benali",   "ahmed.benali@laposte.net", "FR76 2004 1010 0505 0013 4056 024", "FBX-44821", "Freebox Pop",        310.7, "FR-22184"),
                ("0645678901", "Sophie Leclerc", "sophie.leclerc@yahoo.fr",  "FR76 3000 4000 0300 0000 0350 461", "FBX-57392", "Freebox Ultra",      55.2,  "FR-71093"),
                ("0656789012", "Pierre Moreau",  "pierre.moreau@orange.fr",  "FR76 1820 6000 2000 6543 2100 002", "FBX-61047", "Freebox Mini 4K",    201.8, "FR-39876"),
            ],
        )
        conn.commit()
    conn.close()


# ── Générateur JWT minimal (sans librairie externe) ───────────────────────────
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_jwt(payload: dict) -> str:
    header  = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body    = _b64url(json.dumps(payload).encode())
    sig_input = f"{header}.{body}".encode()
    sig = _b64url(hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest())
    return f"{header}.{body}.{sig}"


# =============================================================================
# ROUTES
# =============================================================================

@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Free DevSecOps Lab — Lab 1</title>
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
    body {
      background: #0d0d1a;
      background-image:
        linear-gradient(rgba(0,255,70,.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,70,.04) 1px, transparent 1px);
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
    .card {
      max-width: 900px; width: 100%;
      border: 4px solid #00ff46;
      box-shadow: 0 0 40px #00ff4640;
      background: #0a0a18;
      padding: 36px 40px;
    }
    h1 { font-size:1.3rem; text-align:center; color:#fff;
         text-shadow: 3px 3px #00ff46; margin-bottom:6px; }
    .sub { text-align:center; font-size:.4rem; color:#00cc38;
           margin-bottom:30px; letter-spacing:1px; }
    .tag { display:inline-block; background:#00ff4618; border:2px solid #00ff4644;
           color:#00ff46; font-size:.35rem; padding:4px 10px; margin-bottom:28px; }
    .warn { border:3px solid #ff4444; background:#1a0000;
            padding:14px 18px; margin-bottom:28px;
            font-size:.38rem; color:#ff8888; line-height:2.2; }
    .warn strong { color:#ff3333; font-size:.42rem; }
    h2 { font-size:.5rem; color:#ffdd00; margin-bottom:12px;
         border-bottom:2px solid #ffdd0033; padding-bottom:6px; }
    table { width:100%; border-collapse:collapse; margin-bottom:28px; font-size:.34rem; }
    th { color:#ffdd00; padding:8px 12px; text-align:left; border-bottom:2px solid #ffdd0022; }
    td { padding:8px 12px; border-bottom:1px solid #00ff4618; line-height:2; }
    td a { color:#00cfff; text-decoration:none; }
    td a:hover { color:#fff; text-decoration:underline; }
    tr:hover td { background:#00ff4606; }
    .red  { color:#ff5555; }
    .grn  { color:#00ff46; }
    .ylw  { color:#ffdd00; }
    .foot { text-align:center; font-size:.32rem; color:#00ff4655; margin-top:8px; line-height:2.5; }
    .blink { animation: blink 1s step-end infinite; }
    @keyframes blink { 50%{opacity:0} }
  </style>
</head>
<body>
<div class="card">
  <h1>[ FREE DEVSECOPS — LAB 1 ]</h1>
  <p class="sub">&gt;&gt;&gt; SECRETS DETECTION &amp; PIPELINE CI &lt;&lt;&lt;</p>
  <div style="text-align:center;margin-bottom:24px;">
    <span class="tag">Gitleaks</span>
    <span class="tag">TruffleHog</span>
    <span class="tag">Semgrep</span>
    <span class="tag">pip-audit</span>
    <span class="tag">Trivy</span>
  </div>

  <div class="warn">
    <strong>⚠ AVERTISSEMENT</strong><br>
    Ce code contient des secrets INTENTIONNELS simulant une erreur réelle de développeur Free.<br>
    Objectif : les détecter avec les outils CI, comprendre leur impact, et les corriger.<br>
    Ne jamais déployer ce code en production.
  </div>

  <h2>▶ ENDPOINTS</h2>
  <table>
    <tr><th>Route</th><th>Exemple</th><th>Faille</th></tr>
    <tr>
      <td>/subscriber</td>
      <td><a href="/subscriber?phone=0612345678">/subscriber?phone=0612345678</a></td>
      <td class="red">⚠ SQL Injection</td>
    </tr>
    <tr>
      <td>/auth/token</td>
      <td><a href="/auth/token?user_id=1">/auth/token?user_id=1</a></td>
      <td class="red">⚠ JWT Secret exposé</td>
    </tr>
    <tr>
      <td>/admin/config</td>
      <td><a href="/admin/config">/admin/config</a></td>
      <td class="red">⚠ Credentials en clair</td>
    </tr>
    <tr>
      <td>/backup/status</td>
      <td><a href="/backup/status">/backup/status</a></td>
      <td class="red">⚠ Clés AWS exposées</td>
    </tr>
    <tr>
      <td>/line-status</td>
      <td><a href="/line-status?id=FBX-29471">/line-status?id=FBX-29471</a></td>
      <td class="grn">✔ OK</td>
    </tr>
    <tr>
      <td>/health</td>
      <td><a href="/health">/health</a></td>
      <td class="red">⚠ Fuite RGPD</td>
    </tr>
  </table>

  <h2>▶ SECRETS À DÉTECTER</h2>
  <table>
    <tr><th>#</th><th>Secret</th><th>Impact</th><th>Outil</th></tr>
    <tr><td class="ylw">1</td><td>FREE_INTERNAL_TOKEN</td><td>Accès systèmes internes Free</td><td>Gitleaks</td></tr>
    <tr><td class="ylw">2</td><td>JWT_SECRET</td><td>Usurpation sessions abonnés</td><td>TruffleHog</td></tr>
    <tr><td class="ylw">3</td><td>DB_PASSWORD</td><td>Accès BDD production</td><td>Gitleaks</td></tr>
    <tr><td class="ylw">4</td><td>AWS_ACCESS_KEY_ID / SECRET</td><td>Accès backups facturation S3</td><td>Gitleaks + TruffleHog</td></tr>
    <tr><td class="ylw">5</td><td>OAUTH2_CLIENT_SECRET</td><td>Compromission SSO Free</td><td>TruffleHog (entropie)</td></tr>
  </table>

  <p class="foot">
    Lab DevSecOps Free — Formateur : Yacine Romdhani<br>
    <span class="blink">_</span>
  </p>
</div>
</body>
</html>
""")


@app.route("/subscriber")
def subscriber():
    # FAILLE SQL — concaténation directe du numéro de téléphone
    # Exploit : /subscriber?phone=0612345678' OR '1'='1
    phone = request.args.get("phone", "")
    conn  = get_db()
    query = "SELECT id, phone, name, email, plan, data_used_gb FROM subscribers WHERE phone = '" + phone + "'"
    rows  = conn.execute(query).fetchall()
    conn.close()
    keys = ["id", "phone", "name", "email", "plan", "data_used_gb"]
    return jsonify([dict(zip(keys, r)) for r in rows])


@app.route("/auth/token")
def auth_token():
    # Génère un JWT signé avec le secret hardcodé
    # Impact : quiconque connaît JWT_SECRET peut forger n'importe quelle session
    user_id = request.args.get("user_id", "1")
    conn = get_db()
    row  = conn.execute("SELECT name, plan FROM subscribers WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Abonné introuvable"}), 404
    token = make_jwt({"sub": user_id, "name": row[0], "plan": row[1], "role": "subscriber"})
    return jsonify({"token": token, "type": "Bearer"})


@app.route("/admin/config")
def admin_config():
    # Expose toute la configuration interne — aucune authentification requise
    return jsonify({
        "free_internal_token": FREE_INTERNAL_TOKEN,
        "jwt_secret":          JWT_SECRET,
        "db_host":             "prod-mysql-01.infra.free.fr",
        "db_password":         DB_PASSWORD,
        "oauth2_client_secret": OAUTH2_CLIENT_SECRET,
        "environment":         "production",
    })


@app.route("/backup/status")
def backup_status():
    # Expose les credentials AWS S3 utilisés pour les backups de facturation
    return jsonify({
        "status":                 "ok",
        "bucket":                 "free-billing-backups-prod",
        "region":                 "eu-west-3",
        "aws_access_key_id":      AWS_ACCESS_KEY_ID,
        "aws_secret_access_key":  AWS_SECRET_ACCESS_KEY,
        "last_backup":            "2026-06-08T02:00:00Z",
        "size_gb":                1842,
    })


@app.route("/line-status")
def line_status():
    line_id = request.args.get("id", "")
    conn = get_db()
    row  = conn.execute(
        "SELECT name, plan, data_used_gb FROM subscribers WHERE line_id = ?", (line_id,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Ligne introuvable"}), 404
    return jsonify({
        "line_id":        line_id,
        "status":         "active",
        "subscriber":     row[0],
        "plan":           row[1],
        "data_used_gb":   row[2],
        "sync_down_mbps": 987,
        "sync_up_mbps":   642,
    })


@app.route("/health")
def health():
    # RGPD — données personnelles exposées dans le healthcheck
    conn = get_db()
    last = conn.execute(
        "SELECT name, email, iban FROM subscribers ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return jsonify({
        "status":           "ok",
        "db_host":          "prod-mysql-01.infra.free.fr",
        "last_subscriber":  {"name": last[0], "email": last[1], "iban": last[2]},
    })


if __name__ == "__main__":
    init_db()
    # FAILLE — debug=True = console Werkzeug accessible = exécution de code arbitraire
    app.run(host="0.0.0.0", port=5000, debug=True)
