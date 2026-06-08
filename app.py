import os
import sqlite3
import hashlib
import hmac
import base64
import json
import requests as http_requests
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



# =============================================================================
# ROUTES API — FAILLES À DÉTECTER ET CORRIGER (Objectifs 1 & 3)
# =============================================================================

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




# =============================================================================
# INTERFACE WEB — Tableau de bord, IP Manager, Lab Guide
# (Ne pas modifier — ces routes sont là pour la démo visuelle)
# =============================================================================

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


@app.route("/ip-manager")
def ip_manager():
    # FAILLE — clé plateforme IP Management Free Mobile en dur (détectée par Gitleaks)
    IP_MGMT_API_KEY = "freeip_mgmt_5c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f"

    ip    = request.args.get("ip", "").strip()
    data  = None
    error = None

    QUICK_IPS = [
        {"label": "Free Mobile DNS",  "ip": "212.27.48.10",  "tag": "AS12322"},
        {"label": "Orange DNS",        "ip": "80.10.246.2",   "tag": "AS3215"},
        {"label": "SFR DNS",           "ip": "109.0.66.10",   "tag": "AS15557"},
        {"label": "Bouygues Telecom",  "ip": "194.158.122.10","tag": "AS5410"},
        {"label": "Cloudflare",        "ip": "1.1.1.1",       "tag": "AS13335"},
        {"label": "Google DNS",        "ip": "8.8.8.8",       "tag": "AS15169"},
        {"label": "OVH",               "ip": "5.135.0.1",     "tag": "AS16276"},
        {"label": "Scaleway",          "ip": "51.158.0.1",    "tag": "AS12876"},
    ]

    if ip:
        try:
            r = http_requests.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,message,country,countryCode,regionName,city,zip,lat,lon,isp,org,as,asname,query"},
                timeout=5
            )
            data = r.json()
            if data.get("status") == "fail":
                error = data.get("message", "IP invalide")
                data  = None
        except Exception as e:
            error = "Service ip-api.com inaccessible"

    return render_template_string("""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>IP Manager — Free Mobile FAI</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root{--red:#E2001A;--dark:#0f1117;--surface:#161b22;--border:#21262d;
          --text:#c9d1d9;--muted:#8b949e;--green:#22c55e;--orange:#f97316;
          --blue:#3b82f6;--blue-dim:#1d3a5f;--code:#1c2128}
    *{margin:0;padding:0;box-sizing:border-box}
    body{background:var(--dark);color:var(--text);font-family:'Inter',sans-serif;font-size:.88rem;min-height:100vh}
    .topbar{background:#0d1117ee;backdrop-filter:blur(12px);border-bottom:1px solid var(--border);
            padding:12px 28px;display:flex;align-items:center;gap:14px;position:sticky;top:0;z-index:100}
    .logo{background:var(--red);color:#fff;font-weight:700;font-size:.85rem;padding:5px 14px;border-radius:5px}
    .topbar-title{color:var(--muted);font-size:.8rem}
    .topbar-right{margin-left:auto;display:flex;gap:8px;align-items:center}
    .badge{font-size:.65rem;padding:3px 10px;border-radius:20px;border:1px solid var(--border);color:var(--muted);background:var(--surface)}
    .badge-red{background:#1a0808;border-color:#7a1a1a;color:#ff9999}
    /* CONTENT */
    .container{max-width:900px;margin:0 auto;padding:32px 24px}
    h1{font-size:1.3rem;font-weight:700;color:#fff;margin-bottom:6px}
    .desc{color:var(--muted);font-size:.82rem;margin-bottom:28px;line-height:1.7}
    /* ALERT */
    .alert{background:#1a0600;border:1px solid #7a2a00;border-left:4px solid var(--red);
           padding:14px 18px;border-radius:0 8px 8px 0;font-size:.78rem;color:#ffb899;margin-bottom:24px;display:flex;gap:12px}
    .alert strong{color:var(--red)}
    .alert-key{font-family:'JetBrains Mono',monospace;background:var(--code);padding:2px 8px;
               border-radius:4px;color:#ff9999;font-size:.73rem;display:inline-block;margin-top:4px}
    /* SEARCH */
    .search-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:24px;margin-bottom:20px}
    .search-label{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:10px}
    .search-row{display:flex;gap:10px}
    .search-input{flex:1;background:var(--code);border:1px solid var(--border);border-radius:8px;
                  padding:11px 16px;color:var(--text);font-family:'JetBrains Mono',monospace;
                  font-size:.85rem;outline:none;transition:border .2s}
    .search-input:focus{border-color:var(--blue)}
    .search-btn{background:var(--red);color:#fff;border:none;padding:11px 22px;border-radius:8px;
                font-weight:600;font-size:.82rem;cursor:pointer;font-family:inherit;transition:opacity .2s}
    .search-btn:hover{opacity:.85}
    /* QUICK IPS */
    .quick-label{font-size:.68rem;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin:14px 0 8px}
    .quick-row{display:flex;flex-wrap:wrap;gap:8px}
    .quick-btn{background:var(--code);border:1px solid var(--border);color:var(--text);
               padding:6px 14px;border-radius:6px;cursor:pointer;font-size:.73rem;
               font-family:'JetBrains Mono',monospace;transition:all .15s;display:flex;flex-direction:column;align-items:flex-start;gap:1px}
    .quick-btn:hover{border-color:var(--blue);color:#fff;background:#1d3a5f}
    .quick-btn .qip{font-size:.7rem}
    .quick-btn .qtag{font-size:.6rem;color:var(--muted)}
    /* RESULT */
    .result-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:20px}
    .result-header{padding:16px 20px;border-bottom:1px solid var(--border);background:#0d1117;
                   display:flex;justify-content:space-between;align-items:center}
    .result-ip{font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:600;color:#fff}
    .result-asn{font-size:.72rem;color:var(--muted);font-family:'JetBrains Mono',monospace}
    .result-grid{display:grid;grid-template-columns:1fr 1fr;gap:0}
    .result-row{padding:13px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
    .result-row:last-child{border-bottom:none}
    .result-row:nth-child(odd){background:#ffffff04}
    .result-label{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
    .result-val{font-size:.82rem;color:#fff;font-family:'JetBrains Mono',monospace;text-align:right;max-width:60%}
    .result-val.isp-free{color:#E2001A;font-weight:600}
    .isp-badge{background:#E2001A22;border:1px solid #E2001A55;color:#ff9999;
               font-size:.65rem;padding:2px 8px;border-radius:4px;margin-left:8px}
    /* ERROR */
    .error-box{background:#1a0808;border:1px solid #7a1a1a;border-radius:8px;
               padding:16px 20px;color:#ff9999;font-size:.82rem;margin-bottom:20px;display:flex;gap:10px}
    /* API SECTION */
    .api-card{background:var(--code);border:1px solid var(--border);border-radius:8px;overflow:hidden}
    .api-header{background:#0d1117;padding:10px 16px;border-bottom:1px solid var(--border);
                display:flex;justify-content:space-between}
    .api-header span{font-size:.7rem;color:var(--muted)}
    .api-pre{padding:16px;font-family:'JetBrains Mono',monospace;font-size:.73rem;color:#e6edf3;line-height:1.8;overflow-x:auto}
    .kw{color:#ff7b72}.st{color:#a5d6ff}.cm{color:#8b949e}.fn{color:#d2a8ff}.nu{color:#79c0ff}
    .footer{text-align:center;padding:24px;border-top:1px solid var(--border);
            font-size:.72rem;color:var(--muted);margin-top:32px}
    .footer a{color:#3b82f6;text-decoration:none}
  </style>
</head>
<body>

<div class="topbar">
  <div class="logo">Free Mobile</div>
  <span class="topbar-title">IP Management Platform — FAI Tools</span>
  <div class="topbar-right">
    <span class="badge">ip-api.com · Live</span>
    <span class="badge badge-red">⚠ Clé exposée</span>
    <a href="/" style="color:#3b82f6;font-size:.75rem;text-decoration:none">← Accueil</a>
  </div>
</div>

<div class="container">
  <h1>IP Manager</h1>
  <p class="desc">
    Outil interne Free Mobile — lookup d'adresses IP avec informations ISP, ASN et géolocalisation.<br>
    Utilisé par les équipes NOC pour identifier les opérateurs, déboguer le routage et analyser le trafic.
  </p>

  <div class="alert">
    <div style="margin-top:2px">⚠</div>
    <div>
      <strong>FAILLE #6 — Clé IP Management Platform en dur dans le code</strong>
      <div class="alert-key">IP_MGMT_API_KEY = "{{ api_key }}"</div>
    </div>
  </div>

  <!-- SEARCH -->
  <div class="search-card">
    <div class="search-label">Rechercher une adresse IP</div>
    <form method="get" action="/ip-manager">
      <div class="search-row">
        <input class="search-input" name="ip" type="text" placeholder="ex: 212.27.48.10" value="{{ ip }}" autocomplete="off" spellcheck="false">
        <button class="search-btn" type="submit">Analyser →</button>
      </div>
    </form>

    <div class="quick-label">Raccourcis — opérateurs FAI</div>
    <div class="quick-row">
      {% for q in quick_ips %}
      <button class="quick-btn" onclick="setIp('{{ q.ip }}')">
        <span class="qip">{{ q.label }}</span>
        <span class="qtag">{{ q.ip }} · {{ q.tag }}</span>
      </button>
      {% endfor %}
    </div>
  </div>

  <!-- ERROR -->
  {% if error %}
  <div class="error-box">⚠ {{ error }}</div>
  {% endif %}

  <!-- RESULT -->
  {% if data %}
  {% set is_free = 'Free' in data.get('isp','') or 'Iliad' in data.get('isp','') or '12322' in data.get('as','') %}
  <div class="result-card">
    <div class="result-header">
      <div>
        <div class="result-ip">{{ data.query }}
          {% if is_free %}<span class="isp-badge">Free Mobile</span>{% endif %}
        </div>
        <div class="result-asn">{{ data.get('as','N/A') }}</div>
      </div>
      <div style="text-align:right">
        <div style="font-size:1.2rem">{{ data.get('countryCode','??') }}</div>
        <div style="font-size:.7rem;color:var(--muted)">{{ data.get('country','') }}</div>
      </div>
    </div>
    <div class="result-grid">
      <div class="result-row">
        <span class="result-label">ISP</span>
        <span class="result-val {% if is_free %}isp-free{% endif %}">{{ data.get('isp','N/A') }}</span>
      </div>
      <div class="result-row">
        <span class="result-label">Organisation</span>
        <span class="result-val">{{ data.get('org','N/A') }}</span>
      </div>
      <div class="result-row">
        <span class="result-label">AS Name</span>
        <span class="result-val">{{ data.get('asname','N/A') }}</span>
      </div>
      <div class="result-row">
        <span class="result-label">Ville</span>
        <span class="result-val">{{ data.get('city','N/A') }}, {{ data.get('regionName','') }}</span>
      </div>
      <div class="result-row">
        <span class="result-label">Code postal</span>
        <span class="result-val">{{ data.get('zip','N/A') }}</span>
      </div>
      <div class="result-row">
        <span class="result-label">Coordonnées</span>
        <span class="result-val">{{ data.get('lat','N/A') }}, {{ data.get('lon','N/A') }}</span>
      </div>
    </div>
  </div>
  {% endif %}

  <!-- CODE SOURCE -->
  <div class="api-card">
    <div class="api-header">
      <span>app.py — Faille dans le code source</span>
      <span style="color:#ef4444">⚠ Gitleaks · TruffleHog</span>
    </div>
    <div class="api-pre">
<span class="cm"># FAILLE — clé IP Management Platform Free Mobile en dur</span>
IP_MGMT_API_KEY = <span class="st">"{{ api_key }}"</span>

<span class="cm"># Appel à l'API interne Free avec la clé exposée :</span>
response = requests.get(
    <span class="st">"https://ipmanager.infra.free.fr/v3/lookup"</span>,
    headers={<span class="st">"Authorization"</span>: <span class="st">"Bearer "</span> + IP_MGMT_API_KEY},
    params={<span class="st">"ip"</span>: ip, <span class="st">"fields"</span>: <span class="st">"isp,asn,geo,routing"</span>}
)

<span class="cm"># Source données réelles : ip-api.com (gratuit, sans authentification)</span>
<span class="cm"># En prod Free : API interne avec authentification via IP_MGMT_API_KEY</span>
    </div>
  </div>

  <div class="footer">
    Free Mobile — IP Management Platform · Données : <a href="https://ip-api.com">ip-api.com</a> ·
    <a href="/tp">Lab Guide</a> · <a href="/">Accueil</a>
  </div>
</div>

<script>
function setIp(ip) {
  document.querySelector('.search-input').value = ip;
  document.querySelector('form').submit();
}
</script>
</body>
</html>""", ip=ip, data=data, error=error, api_key=IP_MGMT_API_KEY, quick_ips=QUICK_IPS)


@app.route("/tp")

@app.route("/tp")
def tp():
    return render_template_string("""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lab 1 — Gitleaks | Free Mobile DevSecOps</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root{--red:#E2001A;--dark:#0f1117;--surface:#161b22;--border:#21262d;
          --text:#c9d1d9;--muted:#8b949e;--green:#3fb950;--blue:#58a6ff;--code:#1c2128;--orange:#e3b341}
    *{margin:0;padding:0;box-sizing:border-box}
    body{background:var(--dark);color:var(--text);font-family:'Inter',sans-serif;font-size:.88rem;line-height:1.7;min-height:100vh}
    .topbar{background:#0d1117ee;backdrop-filter:blur(12px);border-bottom:1px solid var(--border);
            padding:12px 28px;display:flex;align-items:center;gap:14px;position:sticky;top:0;z-index:100}
    .logo{background:var(--red);color:#fff;font-weight:700;font-size:.85rem;padding:5px 14px;border-radius:5px;letter-spacing:.3px}
    .topbar-right{margin-left:auto;display:flex;gap:16px;align-items:center}
    .topbar-right a{color:var(--blue);font-size:.78rem;text-decoration:none}
    .container{max-width:860px;margin:0 auto;padding:48px 28px}
    h1{font-size:1.6rem;font-weight:700;color:#fff;margin-bottom:6px}
    .meta{display:flex;gap:20px;margin-bottom:40px;flex-wrap:wrap}
    .meta-item{font-size:.75rem;color:var(--muted);display:flex;align-items:center;gap:6px}
    .meta-item strong{color:var(--text)}
    h2{font-size:1rem;font-weight:600;color:#fff;margin:40px 0 12px;display:flex;align-items:center;gap:10px}
    h2 .step-num{background:var(--red);color:#fff;font-size:.72rem;padding:2px 8px;border-radius:4px;font-weight:700}
    h3{font-size:.88rem;font-weight:600;color:var(--blue);margin:20px 0 10px}
    p{margin-bottom:12px;color:var(--text)}
    ul,ol{margin:0 0 16px 20px}
    li{margin-bottom:6px}
    pre{background:var(--code);border:1px solid var(--border);border-radius:8px;
        padding:16px 20px;overflow-x:auto;margin:12px 0;font-family:'JetBrains Mono',monospace;font-size:.78rem;color:#e6edf3;line-height:1.6}
    code{font-family:'JetBrains Mono',monospace;font-size:.82em;background:var(--code);
         padding:2px 6px;border-radius:4px;color:#a5d6ff;border:1px solid var(--border)}
    .objective-box{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:20px 24px;margin-bottom:32px}
    .objective-box ol{margin:10px 0 0 18px}
    .objective-box li{color:var(--text);margin-bottom:8px}
    .info-box{background:#111d2e;border:1px solid #1f6feb;border-left:4px solid #58a6ff;
              border-radius:0 8px 8px 0;padding:14px 18px;margin:16px 0;font-size:.82rem;color:#a5d6ff}
    .warn-box{background:#1a0e00;border:1px solid #7a4a00;border-left:4px solid var(--orange);
              border-radius:0 8px 8px 0;padding:14px 18px;margin:16px 0;font-size:.82rem;color:var(--orange)}
    .question-box{background:#0d1f0d;border:1px solid #238636;border-radius:8px;
                  padding:16px 20px;margin:16px 0}
    .question-box .q-title{font-size:.72rem;color:var(--green);font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}
    .question-box ul{margin:0 0 0 16px}
    .question-box li{color:var(--text);margin-bottom:6px;font-size:.84rem}
    .section-divider{border:none;border-top:1px solid var(--border);margin:40px 0}
    .livrable-box{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:20px 24px}
    .livrable-box ol{margin:10px 0 0 18px}
    .livrable-box li{margin-bottom:8px}
    .retenir{background:#0f1117;border:1px solid var(--red);border-radius:8px;padding:20px 24px;margin-top:40px;font-size:.84rem;color:var(--text);line-height:1.8}
    .retenir strong{color:var(--red)}
    .footer{text-align:center;padding:40px 0 24px;border-top:1px solid var(--border);
            font-size:.72rem;color:var(--muted);margin-top:48px}
    .footer a{color:var(--blue);text-decoration:none}
  </style>
</head>
<body>
<div class="topbar">
  <div class="logo">Free Mobile</div>
  <span style="color:var(--muted);font-size:.8rem">DevSecOps — Lab 1</span>
  <div class="topbar-right">
    <a href="/">← Accueil</a>
    <a href="/ip-manager">IP Manager</a>
    <a href="https://github.com/RomdhaniYacine/Lab1" target="_blank">GitHub</a>
  </div>
</div>

<div class="container">
  <h1>Lab 1 — Détection de secrets avec Gitleaks</h1>
  <div class="meta">
    <div class="meta-item">⏱ <strong>Durée : 1h00</strong></div>
    <div class="meta-item">🐍 <strong>Stack : Python</strong></div>
    <div class="meta-item">🔍 <strong>Outil principal : Gitleaks</strong></div>
  </div>

  <div class="objective-box">
    <div style="font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:12px;font-weight:600">Objectifs pédagogiques</div>
    <p style="margin-bottom:10px">À la fin de ce TP, vous serez capable de :</p>
    <ol>
      <li>Détecter un secret présent dans le code source avec un scanner automatique.</li>
      <li>Mettre en place un pre-commit hook qui bloque un commit contenant un secret avant qu'il ne soit créé.</li>
      <li>Comprendre qu'un secret supprimé du code reste présent dans l'historique Git, et savoir comment réagir.</li>
    </ol>
  </div>

  <hr class="section-divider">

  <!-- ÉTAPE 0 -->
  <h2><span class="step-num">0</span> Prise en main</h2>
  <p>Clonez le projet et lancez l'API :</p>
  <pre>git clone https://github.com/RomdhaniYacine/Lab1.git
cd Lab1
pip3 install -r requirements.txt
python3 app.py</pre>
  <p>Ouvrez <strong>http://localhost:5000</strong> — vous verrez le tableau de bord de l'API Free Mobile.</p>
  <p>Parcourez <code>app.py</code>. Les premières lignes contiennent le code de production livré par l'équipe externe.</p>

  <!-- ÉTAPE 1 -->
  <h2><span class="step-num">1</span> Détecter les secrets dans le code</h2>
  <p>Des credentials sont écrits en dur dans <code>app.py</code> :</p>
  <pre>PROVISIONING_TOKEN = "freemobile_prov_api_4f8a2c1e9b3d7f05"
JWT_SECRET         = "fm-jwt-s1gn1ng-k3y-pr0d-2024!"
CDR_DB_PASSWORD    = "Fr33M0b!leCDR@Prod2024"
AWS_ACCESS_KEY_ID  = "LAB_AKIAIOSFODNN7FREEMOB"
MVNO_PARTNER_KEY   = "mvno_partner_key_9e8d7c6b5a4f3210"</pre>
  <p>Lancez un scan du dépôt :</p>
  <pre>gitleaks detect --source . --verbose</pre>

  <div class="question-box">
    <div class="q-title">Questions</div>
    <ul>
      <li>Que détecte Gitleaks ? Notez le type de secret, le fichier et le commit incriminé.</li>
      <li>Quel code de sortie renvoie Gitleaks ? (<code>echo $?</code> — 0 = rien trouvé, 1 = secret détecté.)</li>
    </ul>
  </div>

  <div class="info-box">
    💡 Ce code de sortie est exactement ce qu'utilisera un pipeline CI pour faire échouer un build.
  </div>

  <!-- ÉTAPE 2 -->
  <h2><span class="step-num">2</span> Prévenir : bloquer le commit avant qu'il n'arrive</h2>
  <p>Détecter après coup, c'est du nettoyage. L'objectif du <em>shift left</em> est d'empêcher la fuite dès le poste du développeur.</p>

  <h3>2.1 Installer le hook Git</h3>
  <p>Créez le fichier <code>.git/hooks/pre-commit</code> :</p>
  <pre>#!/bin/sh
gitleaks protect --staged --verbose</pre>
  <p>Rendez-le exécutable :</p>
  <pre>chmod +x .git/hooks/pre-commit</pre>
  <p><code>gitleaks protect --staged</code> analyse uniquement ce qui est mis en stage (<code>git add</code>), donc le contenu sur le point d'être committé.</p>

  <h3>2.2 Tester le blocage</h3>
  <p>Ajoutez une nouvelle clé fictive dans <code>app.py</code> :</p>
  <pre>STRIPE_KEY = "sk_live_4eC39HqLyjWDarjtT1zdp7dc"  # fictive</pre>
  <p>Tentez de committer :</p>
  <pre>git add app.py
git commit -m "Add payment integration"</pre>

  <div class="question-box">
    <div class="q-title">Question</div>
    <ul>
      <li>Le commit aboutit-il ? Que se passe-t-il ? Notez le message renvoyé par le hook.</li>
    </ul>
  </div>

  <p>Retirez ensuite la ligne sans la committer.</p>

  <div class="info-box">
    💡 <strong>Variante recommandée en entreprise :</strong> utiliser le framework <code>pre-commit</code> avec un <code>.pre-commit-config.yaml</code> qui appelle Gitleaks. C'est plus portable — le hook est versionné et partagé par toute l'équipe.
  </div>

  <!-- ÉTAPE 3 -->
  <h2><span class="step-num">3</span> La vérité qui dérange : le secret est toujours dans l'historique</h2>
  <p>Le hook est en place, mais les secrets de l'Étape 1 ont été commités avant que le hook n'existe.</p>

  <h3>3.1 Corriger le code actuel</h3>
  <p>Remplacez les secrets par des variables d'environnement dans <code>app.py</code> :</p>
  <pre>import os

PROVISIONING_TOKEN = os.environ.get("PROVISIONING_TOKEN", "")
JWT_SECRET         = os.environ.get("JWT_SECRET", "")
CDR_DB_PASSWORD    = os.environ.get("CDR_DB_PASSWORD", "")
AWS_ACCESS_KEY_ID  = os.environ.get("AWS_ACCESS_KEY_ID", "")
MVNO_PARTNER_KEY   = os.environ.get("MVNO_PARTNER_KEY", "")</pre>
  <p>Committez ce correctif :</p>
  <pre>git add app.py
git commit -m "Fix: secrets déplacés en variables d'environnement"</pre>

  <h3>3.2 Scanner tout l'historique</h3>
  <pre>gitleaks detect --source . --verbose</pre>
  <p>Par défaut, <code>gitleaks detect</code> parcourt l'ensemble de l'historique Git — pas seulement l'état actuel des fichiers.</p>

  <div class="question-box">
    <div class="q-title">Questions</div>
    <ul>
      <li>Gitleaks trouve-t-il encore les secrets ? Dans quel commit ?</li>
      <li>Pourtant <code>app.py</code> ne contient plus les clés. Comment l'expliquez-vous ?</li>
    </ul>
  </div>

  <!-- ÉTAPE 4 -->
  <h2><span class="step-num">4</span> Remédiation : que faire face à un secret leaké ?</h2>
  <ol style="margin:0 0 16px 20px">
    <li style="margin-bottom:12px"><strong style="color:#fff">La première action est toujours la rotation.</strong> Un secret committé doit être considéré compromis. La seule remédiation fiable est de révoquer et régénérer la clé côté fournisseur. Supprimer du code ne dé-fuite rien.</li>
    <li style="margin-bottom:12px"><strong style="color:#fff">Nettoyer l'historique est possible mais coûteux.</strong> Des outils comme <code>git filter-repo</code> ou BFG Repo-Cleaner permettent de purger un secret, mais ils réécrivent l'historique — tous les clones existants deviennent incohérents.</li>
    <li><strong style="color:#fff">La prévention est la seule option vraiment économique</strong> — d'où l'intérêt du hook de l'Étape 2.</li>
  </ol>

  <hr class="section-divider">

  <!-- LIVRABLES -->
  <h2>Livrables attendus</h2>
  <div class="livrable-box">
    <ol>
      <li>La sortie de <code>gitleaks detect</code> de l'Étape 1 (secrets détectés).</li>
      <li>Une capture du message de blocage du commit à l'Étape 2.</li>
      <li>La sortie de <code>gitleaks detect</code> de l'Étape 3 prouvant que les secrets persistent dans l'historique malgré le correctif.</li>
      <li>Vos réponses aux questions des étapes 1, 2 et 3.</li>
    </ol>
  </div>

  <!-- POUR ALLER PLUS LOIN -->
  <h2>Pour aller plus loin (optionnel)</h2>
  <ul>
    <li>Intégrer Gitleaks dans le pipeline CI GitHub Actions (voir <code>.github/workflows/security.yml</code>).</li>
    <li>Tester <code>trufflehog git file://.</code> et comparer ses résultats à ceux de Gitleaks.</li>
    <li>Mettre en place le framework <code>pre-commit</code> partagé pour toute l'équipe.</li>
  </ul>

  <!-- À RETENIR -->
  <div class="retenir">
    <strong>À retenir —</strong> Supprimer un secret ≠ annuler la fuite. Git n'oublie rien. Une fois poussé, un secret est compromis : on le révoque, on ne se contente pas de le supprimer. Le meilleur secret leaké est celui qui n'a jamais quitté le poste du développeur — grâce à un hook.
  </div>

  <div class="footer">
    Free Mobile — DevSecOps Lab 1 &nbsp;·&nbsp;
    <a href="/">Accueil</a> &nbsp;·&nbsp;
    <a href="https://github.com/RomdhaniYacine/Lab1" target="_blank">GitHub</a>
  </div>
</div>
</body>
</html>""")


if __name__ == "__main__":
    init_db()
    # FAILLE — debug=True en production
    app.run(host="0.0.0.0", port=5000, debug=True)
