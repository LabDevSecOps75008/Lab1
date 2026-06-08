import os
import sqlite3
import hashlib
import hmac
import base64
import json
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# =============================================================================
# SECRETS INTENTIONNELLEMENT EXPOSÉS — LAB DEVSECOPS FREE MOBILE
# Simule une erreur réelle : un développeur a commité des credentials de prod
# =============================================================================

# FAILLE #1 — Token provisioning réseau (Gitleaks)
PROVISIONING_TOKEN = "freemobile_prov_api_4f8a2c1e9b3d7f05"

# FAILLE #2 — Secret JWT sessions abonnés (TruffleHog entropie)
JWT_SECRET = "fm-jwt-s1gn1ng-k3y-pr0d-2024!"

# FAILLE #3 — Password MySQL CDR (Call Detail Records) prod (Gitleaks)
CDR_DB_PASSWORD = "Fr33M0b!leCDR@Prod2024"

# FAILLE #4 — Credentials AWS S3 stockage CDR (Gitleaks + TruffleHog)
AWS_ACCESS_KEY_ID     = "LAB_AKIAIOSFODNN7FREEMOB"
AWS_SECRET_ACCESS_KEY = "LAB_wJalrXUtnFEMI/K7MDENG/bPxRfiCYFREEMOBILE"

# FAILLE #5 — Clé API partenaire MVNO (TruffleHog entropie)
MVNO_PARTNER_KEY = "mvno_partner_key_9e8d7c6b5a4f3210"

DB_PATH = "freemobile.db"


def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id           INTEGER PRIMARY KEY,
            msisdn       TEXT,
            iccid        TEXT,
            name         TEXT,
            email        TEXT,
            plan         TEXT,
            data_used_gb REAL,
            status       TEXT,
            roaming      INTEGER
        );
        CREATE TABLE IF NOT EXISTS network_cells (
            id         INTEGER PRIMARY KEY,
            cell_id    TEXT,
            site       TEXT,
            tech       TEXT,
            region     TEXT,
            status     TEXT,
            load_pct   INTEGER
        );
    """)
    if not conn.execute("SELECT 1 FROM subscribers LIMIT 1").fetchone():
        conn.executemany(
            "INSERT INTO subscribers (msisdn,iccid,name,email,plan,data_used_gb,status,roaming) VALUES (?,?,?,?,?,?,?,?)",
            [
                ("0612345678","8933150319080167234","Jean Dupont",   "j.dupont@free.fr",  "Free 5G 210Go", 142.3,"active",0),
                ("0698765432","8933150319080198765","Marie Martin",  "m.martin@free.fr",  "Free 5G 130Go", 87.1, "active",1),
                ("0634567890","8933150319080134567","Ahmed Benali",  "a.benali@free.fr",  "Free 4G 80Go",  310.7,"active",0),
                ("0645678901","8933150319080145678","Sophie Leclerc","s.leclerc@free.fr", "Free 5G 210Go", 55.2, "suspended",0),
                ("0656789012","8933150319080156789","Pierre Moreau", "p.moreau@free.fr",  "Free 4G 50Go",  201.8,"active",0),
            ]
        )
        conn.executemany(
            "INSERT INTO network_cells (cell_id,site,tech,region,status,load_pct) VALUES (?,?,?,?,?,?)",
            [
                ("FR-5G-75001","Paris-01-Rivoli",  "5G NR","Île-de-France","active",67),
                ("FR-4G-75002","Paris-02-Bourse",  "4G LTE","Île-de-France","active",45),
                ("FR-5G-69001","Lyon-01-Bellecour","5G NR","Auvergne-Rhône-Alpes","active",38),
                ("FR-4G-13001","Marseille-01-Vieux-Port","4G LTE","PACA","degraded",89),
                ("FR-5G-31000","Toulouse-Centre",  "5G NR","Occitanie","active",52),
            ]
        )
        conn.commit()
    conn.close()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def make_jwt(payload: dict) -> str:
    header = _b64url(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
    body   = _b64url(json.dumps(payload).encode())
    sig    = _b64url(hmac.new(JWT_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest())
    return f"{header}.{body}.{sig}"


# ─── PAGE D'ACCUEIL ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string("""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Free Mobile — DevSecOps Lab 1</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    :root {
      --red: #E2001A;
      --dark: #111318;
      --card: #1C1F26;
      --border: #2A2D35;
      --text: #E8EAF0;
      --muted: #7A7F8E;
      --green: #22C55E;
      --orange: #F97316;
      --blue: #3B82F6;
    }
    * { margin:0; padding:0; box-sizing:border-box; }
    body { background:var(--dark); color:var(--text); font-family:'Inter',sans-serif;
           min-height:100vh; padding:32px 20px; }
    .topbar { display:flex; align-items:center; gap:16px; margin-bottom:40px; max-width:1000px; margin-left:auto; margin-right:auto; }
    .logo { background:var(--red); color:#fff; font-weight:700; font-size:1.1rem;
            padding:8px 18px; border-radius:6px; letter-spacing:.5px; }
    .topbar-title { font-size:.9rem; color:var(--muted); font-weight:400; }
    .topbar-badge { margin-left:auto; background:#1a1a2a; border:1px solid var(--border);
                    color:var(--muted); font-size:.72rem; padding:4px 12px; border-radius:20px; }
    .container { max-width:1000px; margin:0 auto; }
    .alert { background:#1a0a0a; border:1px solid #7a1a1a; border-left:4px solid var(--red);
             padding:14px 18px; border-radius:6px; margin-bottom:32px;
             font-size:.78rem; color:#ffaaaa; line-height:1.8; }
    .alert strong { color:var(--red); }
    .grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:32px; }
    .stat-card { background:var(--card); border:1px solid var(--border); border-radius:8px;
                 padding:20px 24px; }
    .stat-label { font-size:.7rem; color:var(--muted); text-transform:uppercase;
                  letter-spacing:.8px; margin-bottom:8px; }
    .stat-value { font-size:1.8rem; font-weight:700; }
    .stat-sub { font-size:.72rem; color:var(--muted); margin-top:4px; }
    .red-val { color:var(--red); }
    .grn-val { color:var(--green); }
    .section-title { font-size:.75rem; font-weight:600; color:var(--muted);
                     text-transform:uppercase; letter-spacing:.8px; margin-bottom:12px; }
    .table-card { background:var(--card); border:1px solid var(--border); border-radius:8px;
                  overflow:hidden; margin-bottom:24px; }
    table { width:100%; border-collapse:collapse; font-size:.78rem; }
    th { padding:11px 16px; text-align:left; font-size:.68rem; font-weight:600;
         color:var(--muted); text-transform:uppercase; letter-spacing:.6px;
         border-bottom:1px solid var(--border); background:#161820; }
    td { padding:11px 16px; border-bottom:1px solid var(--border); }
    tr:last-child td { border-bottom:none; }
    tr:hover td { background:#ffffff06; }
    td a { color:var(--blue); text-decoration:none; font-family:monospace; font-size:.75rem; }
    td a:hover { text-decoration:underline; }
    .badge { display:inline-block; font-size:.65rem; font-weight:600; padding:2px 8px;
             border-radius:4px; }
    .badge-red    { background:#7a1a1a; color:#ffaaaa; }
    .badge-green  { background:#14532d; color:#86efac; }
    .badge-orange { background:#7c2d12; color:#fdba74; }
    .footer { text-align:center; font-size:.7rem; color:var(--muted); margin-top:32px;
              padding-top:24px; border-top:1px solid var(--border); }
    .footer span { color:var(--red); }
  </style>
</head>
<body>
  <div class="topbar">
    <div class="logo">Free Mobile</div>
    <span class="topbar-title">Internal Network & Subscriber API</span>
    <span class="topbar-badge">ENV: PRODUCTION ⚠</span>
  </div>

  <div class="container">
    <div class="alert">
      <strong>ATTENTION — LAB DEVSECOPS :</strong> Cette API contient des secrets et des failles
      intentionnels simulant une erreur réelle de développeur. Objectif : les détecter avec
      Gitleaks &amp; TruffleHog, construire le pipeline CI, et corriger le code.
    </div>

    <div class="grid">
      <div class="stat-card">
        <div class="stat-label">Abonnés actifs</div>
        <div class="stat-value grn-val">28 400 000</div>
        <div class="stat-sub">Données exposées si SQL injection</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Secrets dans le code</div>
        <div class="stat-value red-val">5</div>
        <div class="stat-sub">Détectables par Gitleaks + TruffleHog</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Jobs CI à compléter</div>
        <div class="stat-value" style="color:#F97316">5</div>
        <div class="stat-sub">Gitleaks · TruffleHog · Semgrep · pip-audit · Trivy</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Antennes réseau</div>
        <div class="stat-value grn-val">47 800</div>
        <div class="stat-sub">Sites 4G/5G en France métropolitaine</div>
      </div>
    </div>

    <p class="section-title">Endpoints API</p>
    <div class="table-card">
      <table>
        <tr><th>Route</th><th>Exemple</th><th>Faille</th></tr>
        <tr>
          <td>/subscriber/search</td>
          <td><a href="/subscriber/search?msisdn=0612345678">/subscriber/search?msisdn=0612345678</a></td>
          <td><span class="badge badge-red">SQL Injection</span></td>
        </tr>
        <tr>
          <td>/sim/info</td>
          <td><a href="/sim/info?iccid=8933150319080167234">/sim/info?iccid=8933150319080167234</a></td>
          <td><span class="badge badge-green">OK</span></td>
        </tr>
        <tr>
          <td>/network/cell</td>
          <td><a href="/network/cell?id=FR-5G-75001">/network/cell?id=FR-5G-75001</a></td>
          <td><span class="badge badge-green">OK</span></td>
        </tr>
        <tr>
          <td>/auth/token</td>
          <td><a href="/auth/token?msisdn=0612345678">/auth/token?msisdn=0612345678</a></td>
          <td><span class="badge badge-red">JWT Secret exposé</span></td>
        </tr>
        <tr>
          <td>/internal/config</td>
          <td><a href="/internal/config">/internal/config</a></td>
          <td><span class="badge badge-red">Credentials prod</span></td>
        </tr>
        <tr>
          <td>/cdr/storage</td>
          <td><a href="/cdr/storage">/cdr/storage</a></td>
          <td><span class="badge badge-red">Clés AWS exposées</span></td>
        </tr>
        <tr>
          <td>/health</td>
          <td><a href="/health">/health</a></td>
          <td><span class="badge badge-orange">Fuite RGPD</span></td>
        </tr>
      </table>
    </div>

    <p class="section-title">Secrets à détecter</p>
    <div class="table-card">
      <table>
        <tr><th>#</th><th>Variable</th><th>Type</th><th>Impact</th><th>Outil</th></tr>
        <tr><td>1</td><td>PROVISIONING_TOKEN</td><td>Token API réseau</td><td>Accès provisioning SIM</td><td>Gitleaks</td></tr>
        <tr><td>2</td><td>JWT_SECRET</td><td>Clé signature JWT</td><td>Forge sessions abonnés</td><td>TruffleHog</td></tr>
        <tr><td>3</td><td>CDR_DB_PASSWORD</td><td>Password MySQL</td><td>Accès CDR production</td><td>Gitleaks</td></tr>
        <tr><td>4</td><td>AWS_ACCESS_KEY_ID</td><td>Credentials AWS</td><td>Accès stockage CDR S3</td><td>Gitleaks + TruffleHog</td></tr>
        <tr><td>5</td><td>MVNO_PARTNER_KEY</td><td>Clé partenaire MVNO</td><td>Accès API partenaires</td><td>TruffleHog (entropie)</td></tr>
      </table>
    </div>

    <div class="footer">
      Free Mobile — DevSecOps Lab 1 &nbsp;·&nbsp;
      Formateur : <span>Yacine Romdhani</span> &nbsp;·&nbsp;
      <a href="https://github.com/RomdhaniYacine/Lab1" style="color:#3B82F6">GitHub</a>
    </div>
  </div>
</body>
</html>""")


# ─── ENDPOINTS API ────────────────────────────────────────────────────────────

@app.route("/subscriber/search")
def subscriber_search():
    # FAILLE — SQL injection sur le MSISDN (numéro mobile)
    # Exploit : /subscriber/search?msisdn=0612345678' OR '1'='1
    msisdn = request.args.get("msisdn", "")
    conn   = get_db()
    query  = "SELECT id,msisdn,iccid,name,email,plan,data_used_gb,status FROM subscribers WHERE msisdn = '" + msisdn + "'"
    rows   = conn.execute(query).fetchall()
    conn.close()
    keys = ["id","msisdn","iccid","name","email","plan","data_used_gb","status"]
    return jsonify([dict(zip(keys, r)) for r in rows])


@app.route("/sim/info")
def sim_info():
    iccid = request.args.get("iccid", "")
    conn  = get_db()
    row   = conn.execute(
        "SELECT msisdn,name,plan,status,roaming FROM subscribers WHERE iccid = ?", (iccid,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "SIM introuvable"}), 404
    return jsonify({
        "iccid":   iccid,
        "msisdn":  row[0],
        "owner":   row[1],
        "plan":    row[2],
        "status":  row[3],
        "roaming": bool(row[4]),
        "network": "Free Mobile",
        "imsi_prefix": "20815",
    })


@app.route("/network/cell")
def network_cell():
    cell_id = request.args.get("id", "")
    conn    = get_db()
    row     = conn.execute(
        "SELECT site,tech,region,status,load_pct FROM network_cells WHERE cell_id = ?", (cell_id,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Cellule introuvable"}), 404
    return jsonify({
        "cell_id": cell_id,
        "site":    row[0],
        "tech":    row[1],
        "region":  row[2],
        "status":  row[3],
        "load_pct": row[4],
        "bands": ["n78","n1"] if "5G" in row[1] else ["B3","B7","B20"],
    })


@app.route("/auth/token")
def auth_token():
    msisdn = request.args.get("msisdn", "")
    conn   = get_db()
    row    = conn.execute("SELECT id,name,plan FROM subscribers WHERE msisdn = ?", (msisdn,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Abonné introuvable"}), 404
    token = make_jwt({"sub": str(row[0]), "msisdn": msisdn, "name": row[1], "plan": row[2]})
    return jsonify({"access_token": token, "token_type": "Bearer", "expires_in": 3600})


@app.route("/internal/config")
def internal_config():
    # FAILLE — expose tous les credentials sans authentification
    return jsonify({
        "provisioning_token":   PROVISIONING_TOKEN,
        "jwt_secret":           JWT_SECRET,
        "cdr_db_host":          "cdr-mysql-prod-01.infra.free.fr",
        "cdr_db_password":      CDR_DB_PASSWORD,
        "mvno_partner_key":     MVNO_PARTNER_KEY,
        "environment":          "production",
    })


@app.route("/cdr/storage")
def cdr_storage():
    # FAILLE — expose les credentials AWS des CDR (enregistrements d'appels)
    return jsonify({
        "status":                "ok",
        "bucket":                "freemobile-cdr-prod-eu-west-3",
        "region":                "eu-west-3",
        "aws_access_key_id":     AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
        "records_today":         14_820_441,
        "size_tb":               2.4,
    })


@app.route("/health")
def health():
    # FAILLE RGPD — expose des données abonné dans le healthcheck
    conn = get_db()
    last = conn.execute(
        "SELECT name, email, msisdn FROM subscribers ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return jsonify({
        "status":          "ok",
        "last_subscriber": {"name": last[0], "email": last[1], "msisdn": last[2]},
    })


if __name__ == "__main__":
    init_db()
    # FAILLE — debug=True en production
    app.run(host="0.0.0.0", port=5000, debug=True)
