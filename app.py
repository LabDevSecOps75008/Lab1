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

@app.route("/tp")
def tp():
    return render_template_string("""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lab 1 — Secrets Detection | Free Mobile DevSecOps</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --red:#E2001A; --dark:#0f1117; --surface:#161b22;
      --border:#21262d; --text:#c9d1d9; --muted:#8b949e;
      --green:#238636; --green-text:#3fb950;
      --blue:#1f6feb; --blue-text:#58a6ff;
      --yellow:#9e6a03; --yellow-text:#e3b341;
      --code-bg:#1c2128;
    }
    *{margin:0;padding:0;box-sizing:border-box}
    html{scroll-behavior:smooth}
    body{background:var(--dark);color:var(--text);font-family:'Inter',sans-serif;font-size:.9rem;line-height:1.7}
    /* TOPBAR */
    .topbar{position:sticky;top:0;z-index:100;background:#0d1117ee;backdrop-filter:blur(12px);
            border-bottom:1px solid var(--border);padding:12px 32px;
            display:flex;align-items:center;gap:16px}
    .logo{background:var(--red);color:#fff;font-weight:700;font-size:.85rem;
          padding:5px 14px;border-radius:5px;letter-spacing:.3px;white-space:nowrap}
    .topbar-sep{color:var(--border);font-size:1.2rem}
    .topbar-title{color:var(--muted);font-size:.82rem}
    .topbar-meta{margin-left:auto;display:flex;gap:10px;align-items:center}
    .chip{background:var(--surface);border:1px solid var(--border);color:var(--muted);
          font-size:.7rem;padding:3px 10px;border-radius:20px;white-space:nowrap}
    .chip-red{background:#1a0a0a;border-color:#7a1a1a;color:#ff9999}
    /* LAYOUT */
    .layout{display:flex;min-height:calc(100vh - 53px)}
    /* SIDEBAR */
    .sidebar{width:260px;min-width:260px;border-right:1px solid var(--border);
             padding:28px 0;position:sticky;top:53px;height:calc(100vh - 53px);overflow-y:auto}
    .sidebar-section{font-size:.65rem;font-weight:600;color:var(--muted);
                     text-transform:uppercase;letter-spacing:.8px;
                     padding:0 20px;margin-bottom:6px;margin-top:20px}
    .sidebar-section:first-child{margin-top:0}
    .sidebar a{display:block;padding:7px 20px;font-size:.78rem;color:var(--muted);
               text-decoration:none;border-left:3px solid transparent;
               transition:all .15s}
    .sidebar a:hover{color:var(--text);background:#ffffff06;border-left-color:var(--border)}
    .sidebar a.active{color:var(--red);border-left-color:var(--red);background:#E2001A11}
    /* CONTENT */
    .content{flex:1;max-width:860px;padding:40px 48px;overflow-x:hidden}
    /* HEADER */
    .page-header{margin-bottom:40px;padding-bottom:28px;border-bottom:1px solid var(--border)}
    .page-tag{display:inline-flex;align-items:center;gap:6px;background:#E2001A18;
              border:1px solid #E2001A44;color:#ff9999;font-size:.7rem;font-weight:600;
              padding:4px 12px;border-radius:20px;margin-bottom:16px}
    .page-tag span{width:6px;height:6px;background:var(--red);border-radius:50%;display:inline-block}
    h1{font-size:1.7rem;font-weight:700;color:#fff;line-height:1.3;margin-bottom:12px}
    .page-desc{color:var(--muted);font-size:.88rem;line-height:1.8;max-width:640px}
    /* META CARDS */
    .meta-row{display:flex;gap:12px;margin-bottom:36px;flex-wrap:wrap}
    .meta-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;
               padding:14px 18px;flex:1;min-width:130px}
    .meta-label{font-size:.65rem;color:var(--muted);text-transform:uppercase;
                letter-spacing:.6px;margin-bottom:4px}
    .meta-value{font-size:.88rem;font-weight:600;color:var(--text)}
    /* OBJECTIVES */
    .objectives{background:var(--surface);border:1px solid var(--border);
                border-radius:8px;padding:20px 24px;margin-bottom:32px}
    .objectives h3{font-size:.75rem;color:var(--muted);text-transform:uppercase;
                   letter-spacing:.6px;margin-bottom:14px}
    .obj-item{display:flex;align-items:flex-start;gap:10px;
              padding:8px 0;border-bottom:1px solid var(--border);font-size:.82rem}
    .obj-item:last-child{border-bottom:none;padding-bottom:0}
    .obj-num{background:var(--red);color:#fff;font-size:.65rem;font-weight:700;
             width:20px;height:20px;border-radius:4px;display:flex;align-items:center;
             justify-content:center;flex-shrink:0;margin-top:1px}
    /* STEPS */
    .step{margin-bottom:48px}
    .step-header{display:flex;align-items:center;gap:14px;margin-bottom:20px}
    .step-num{background:var(--surface);border:2px solid var(--border);color:var(--muted);
              font-size:.75rem;font-weight:700;width:36px;height:36px;border-radius:8px;
              display:flex;align-items:center;justify-content:center;flex-shrink:0}
    .step-num.active{background:#E2001A22;border-color:var(--red);color:var(--red)}
    h2{font-size:1.1rem;font-weight:600;color:#fff}
    .step-desc{color:var(--muted);font-size:.83rem;margin-bottom:20px;line-height:1.8}
    /* CODE BLOCKS */
    .code-block{background:var(--code-bg);border:1px solid var(--border);border-radius:8px;
                overflow:hidden;margin:16px 0;font-family:'JetBrains Mono',monospace}
    .code-header{display:flex;align-items:center;justify-content:space-between;
                 padding:8px 14px;border-bottom:1px solid var(--border);background:#0d1117}
    .code-lang{font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
    .code-copy{font-size:.65rem;color:var(--muted);cursor:pointer;background:none;border:none;
               font-family:inherit;padding:2px 8px;border-radius:4px;transition:all .15s}
    .code-copy:hover{background:var(--border);color:var(--text)}
    pre{padding:16px 18px;overflow-x:auto;font-size:.78rem;line-height:1.7;color:#e6edf3}
    .kw{color:#ff7b72}.st{color:#a5d6ff}.cm{color:#8b949e;font-style:italic}
    .fn{color:#d2a8ff}.nu{color:#79c0ff}.op{color:#ff7b72}
    /* CALLOUTS */
    .callout{border-radius:8px;padding:14px 18px;margin:16px 0;
             font-size:.8rem;line-height:1.8;display:flex;gap:12px;align-items:flex-start}
    .callout-icon{font-size:1rem;flex-shrink:0;margin-top:1px}
    .callout-tip{background:#0d2818;border:1px solid #238636}
    .callout-warn{background:#1a1100;border:1px solid #9e6a03}
    .callout-info{background:#0d1b2a;border:1px solid #1f6feb}
    /* QUESTIONS */
    .questions{background:#0d1b2a;border:1px solid #1f6feb;border-left:4px solid var(--blue);
               border-radius:0 8px 8px 0;padding:16px 20px;margin:16px 0}
    .questions h4{color:var(--blue-text);font-size:.75rem;font-weight:600;
                  text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}
    .questions li{font-size:.82rem;color:var(--text);margin-bottom:6px;margin-left:16px}
    /* DELIVERABLES */
    .deliverables{background:var(--surface);border:1px solid var(--border);
                  border-radius:8px;padding:20px 24px;margin:24px 0}
    .deliverables h3{font-size:.75rem;color:var(--muted);text-transform:uppercase;
                     letter-spacing:.6px;margin-bottom:14px}
    .deliverable-item{display:flex;align-items:flex-start;gap:10px;
                      padding:8px 0;border-bottom:1px solid var(--border);font-size:.82rem}
    .deliverable-item:last-child{border-bottom:none}
    .check{width:18px;height:18px;border:2px solid var(--border);border-radius:4px;
           flex-shrink:0;margin-top:2px}
    /* FOOTER */
    .footer{margin-top:48px;padding-top:24px;border-top:1px solid var(--border);
            display:flex;justify-content:space-between;align-items:center;
            font-size:.72rem;color:var(--muted)}
    .footer a{color:var(--blue-text);text-decoration:none}
    h3{font-size:.88rem;font-weight:600;color:var(--text);margin:20px 0 10px}
    hr{border:none;border-top:1px solid var(--border);margin:28px 0}
    /* PREREQ */
    .prereq-table{width:100%;border-collapse:collapse;margin:12px 0}
    .prereq-table th{text-align:left;font-size:.7rem;color:var(--muted);
                     text-transform:uppercase;letter-spacing:.5px;
                     padding:8px 12px;border-bottom:1px solid var(--border)}
    .prereq-table td{padding:9px 12px;border-bottom:1px solid var(--border);font-size:.8rem}
    .prereq-table tr:last-child td{border-bottom:none}
    code{background:var(--code-bg);border:1px solid var(--border);padding:1px 6px;
         border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:.78rem;color:#a5d6ff}
    @media(max-width:768px){
      .sidebar{display:none}
      .content{padding:24px 20px}
    }
  </style>
</head>
<body>

<div class="topbar">
  <div class="logo">Free Mobile</div>
  <span class="topbar-sep">|</span>
  <span class="topbar-title">DevSecOps Training — Lab 1</span>
  <div class="topbar-meta">
    <span class="chip">Gitleaks</span>
    <span class="chip">TruffleHog</span>
    <span class="chip chip-red">⚠ Code vulnérable</span>
  </div>
</div>

<div class="layout">
  <nav class="sidebar">
    <div class="sidebar-section">Navigation</div>
    <a href="#intro" class="active">Introduction</a>
    <a href="#prereqs">Prérequis</a>
    <div class="sidebar-section">Étapes</div>
    <a href="#step0">0 — Initialisation</a>
    <a href="#step1">1 — Détecter un secret</a>
    <a href="#step2">2 — Pre-commit hook</a>
    <a href="#step3">3 — Historique Git</a>
    <a href="#step4">4 — Remédiation</a>
    <div class="sidebar-section">Ressources</div>
    <a href="#deliverables">Livrables</a>
    <a href="#further">Pour aller plus loin</a>
    <a href="/api" style="margin-top:8px">← API vulnérable</a>
  </nav>

  <main class="content">

    <!-- HEADER -->
    <div class="page-header" id="intro">
      <div class="page-tag"><span></span>Lab 1 / 2 — Secrets Detection</div>
      <h1>Détecter et prévenir les fuites de secrets dans Git</h1>
      <p class="page-desc">
        Vous développez un service Python interne chez Free Mobile. Comme beaucoup de développeurs,
        vous allez commettre l'erreur classique : écrire une clé d'API en dur dans le code.
        L'objectif est de voir ce qui se passe, puis d'apprendre à l'empêcher.
      </p>
    </div>

    <!-- META -->
    <div class="meta-row">
      <div class="meta-card">
        <div class="meta-label">Durée estimée</div>
        <div class="meta-value">1 heure</div>
      </div>
      <div class="meta-card">
        <div class="meta-label">Stack</div>
        <div class="meta-value">Python / Flask</div>
      </div>
      <div class="meta-card">
        <div class="meta-label">Outil principal</div>
        <div class="meta-value">Gitleaks</div>
      </div>
      <div class="meta-card">
        <div class="meta-label">Niveau</div>
        <div class="meta-value">Débutant</div>
      </div>
    </div>

    <!-- OBJECTIVES -->
    <div class="objectives">
      <h3>Objectifs pédagogiques</h3>
      <div class="obj-item">
        <div class="obj-num">1</div>
        Détecter un secret présent dans le code source avec un scanner automatique.
      </div>
      <div class="obj-item">
        <div class="obj-num">2</div>
        Mettre en place un pre-commit hook qui bloque un commit contenant un secret.
      </div>
      <div class="obj-item">
        <div class="obj-num">3</div>
        Comprendre qu'un secret supprimé reste dans l'historique Git — et savoir comment réagir.
      </div>
    </div>

    <div class="callout callout-warn">
      <div class="callout-icon">⚠</div>
      <div>Les clés utilisées dans ce lab sont <strong>fictives</strong>. N'utilisez jamais de vraie clé d'API dans un exercice ou un dépôt public.</div>
    </div>

    <!-- PREREQS -->
    <hr>
    <div id="prereqs">
      <h2>Prérequis</h2>
      <table class="prereq-table">
        <tr><th>Outil</th><th>Vérification</th><th>Installation</th></tr>
        <tr>
          <td>Git</td>
          <td><code>git --version</code></td>
          <td>Inclus dans la plupart des OS</td>
        </tr>
        <tr>
          <td>Python 3.10+</td>
          <td><code>python3 --version</code></td>
          <td><code>python.org</code></td>
        </tr>
        <tr>
          <td>Gitleaks</td>
          <td><code>gitleaks version</code></td>
          <td>macOS : <code>brew install gitleaks</code> · Linux : binaire GitHub releases</td>
        </tr>
      </table>
    </div>

    <!-- STEP 0 -->
    <hr>
    <div class="step" id="step0">
      <div class="step-header">
        <div class="step-num active">0</div>
        <h2>Initialisation du projet</h2>
      </div>
      <p class="step-desc">Créez un dépôt Git vierge et une application Flask propre, sans aucun secret.</p>

      <div class="code-block">
        <div class="code-header"><span class="code-lang">bash</span></div>
        <pre>mkdir tp-secrets && cd tp-secrets
git init
pip3 install flask</pre>
      </div>

      <h3>Créez un fichier <code>app.py</code> propre</h3>
      <div class="code-block">
        <div class="code-header"><span class="code-lang">python — app.py</span></div>
        <pre><span class="kw">from</span> flask <span class="kw">import</span> Flask, jsonify

app <span class="op">=</span> Flask(__name__)

<span class="op">@</span>app.route(<span class="st">"/"</span>)
<span class="kw">def</span> <span class="fn">health</span>():
    <span class="kw">return</span> jsonify({<span class="st">"status"</span>: <span class="st">"ok"</span>, <span class="st">"service"</span>: <span class="st">"Free Mobile Internal API"</span>})

<span class="kw">if</span> __name__ <span class="op">==</span> <span class="st">"__main__"</span>:
    app.run(port=<span class="nu">5000</span>)</pre>
      </div>

      <div class="code-block">
        <div class="code-header"><span class="code-lang">bash</span></div>
        <pre>git add .
git commit -m <span class="st">"init: service Flask Free Mobile"</span></pre>
      </div>
    </div>

    <!-- STEP 1 -->
    <hr>
    <div class="step" id="step1">
      <div class="step-header">
        <div class="step-num active">1</div>
        <h2>Détecter un secret dans le code</h2>
      </div>
      <p class="step-desc">
        Vous ajoutez une intégration à un service externe AWS et, par habitude,
        vous mettez la clé directement dans le code.
      </p>

      <h3>Ajoutez cette ligne dans <code>app.py</code></h3>
      <div class="code-block">
        <div class="code-header"><span class="code-lang">python</span></div>
        <pre><span class="cm"># Clé fictive style AWS — NE PAS utiliser en prod</span>
AWS_ACCESS_KEY <span class="op">=</span> <span class="st">"AKIAIOSFODNN7EXAMPLE"</span></pre>
      </div>

      <div class="code-block">
        <div class="code-header"><span class="code-lang">bash</span></div>
        <pre>git add app.py
git commit -m <span class="st">"feat: intégration service AWS"</span></pre>
      </div>

      <h3>Lancez le scan Gitleaks</h3>
      <div class="code-block">
        <div class="code-header"><span class="code-lang">bash</span></div>
        <pre>gitleaks detect --source . --verbose
echo <span class="st">"Code de sortie : $?"</span></pre>
      </div>

      <div class="questions">
        <h4>Questions</h4>
        <ul>
          <li>Que détecte Gitleaks ? Notez le type de secret, le fichier et le commit incriminé.</li>
          <li>Quel code de sortie renvoie Gitleaks ? (0 = rien trouvé, 1 = secret trouvé)</li>
        </ul>
      </div>

      <div class="callout callout-tip">
        <div class="callout-icon">💡</div>
        <div>Ce code de sortie est exactement ce qu'utilisera un pipeline CI pour faire échouer un build automatiquement.</div>
      </div>
    </div>

    <!-- STEP 2 -->
    <hr>
    <div class="step" id="step2">
      <div class="step-header">
        <div class="step-num active">2</div>
        <h2>Prévenir — bloquer le commit avant qu'il n'arrive</h2>
      </div>
      <p class="step-desc">
        Détecter après coup, c'est du nettoyage. Le <strong>shift-left</strong> consiste à bloquer
        la fuite au plus tôt : directement sur le poste du développeur, avant le commit.
      </p>

      <h3>2.1 — Installer le pre-commit hook</h3>
      <div class="code-block">
        <div class="code-header"><span class="code-lang">bash</span></div>
        <pre><span class="cm"># Créer le hook</span>
cat &gt; .git/hooks/pre-commit &lt;&lt; <span class="st">'EOF'</span>
<span class="cm">#!/bin/sh</span>
gitleaks protect --staged --verbose
EOF

<span class="cm"># Le rendre exécutable</span>
chmod +x .git/hooks/pre-commit</pre>
      </div>

      <div class="callout callout-info">
        <div class="callout-icon">ℹ</div>
        <div><code>gitleaks protect --staged</code> analyse uniquement ce qui est en stage (git add), c'est-à-dire le contenu sur le point d'être committé.</div>
      </div>

      <h3>2.2 — Tester le blocage</h3>
      <p class="step-desc">Ajoutez une nouvelle clé fictive dans <code>app.py</code> :</p>

      <div class="code-block">
        <div class="code-header"><span class="code-lang">python</span></div>
        <pre>STRIPE_KEY <span class="op">=</span> <span class="st">"sk_live_4eC39HqLyjWDarjtT1zdp7dc"</span>  <span class="cm"># clé fictive</span></pre>
      </div>

      <div class="code-block">
        <div class="code-header"><span class="code-lang">bash</span></div>
        <pre>git add app.py
git commit -m <span class="st">"feat: intégration paiement"</span></pre>
      </div>

      <div class="questions">
        <h4>Question</h4>
        <ul>
          <li>Le commit aboutit-il ? Quel message le hook renvoie-t-il ?</li>
        </ul>
      </div>

      <div class="callout callout-tip">
        <div class="callout-icon">💡</div>
        <div>
          <strong>Variante recommandée en entreprise</strong> : utiliser le framework
          <code>pre-commit</code> avec un <code>.pre-commit-config.yaml</code>.
          Le hook est versionné et partagé par toute l'équipe, contrairement à
          <code>.git/hooks/</code> qui reste local.
        </div>
      </div>

      <p style="margin-top:12px;font-size:.82rem;color:var(--muted)">
        Retirez la ligne fautive avant de continuer — sans la committer.
      </p>
    </div>

    <!-- STEP 3 -->
    <hr>
    <div class="step" id="step3">
      <div class="step-header">
        <div class="step-num active">3</div>
        <h2>La vérité qui dérange — le secret est toujours dans l'historique</h2>
      </div>
      <p class="step-desc">
        Le hook est en place, le code actuel est propre. Mais la clé de l'Étape 1
        a bel et bien été committée. Voyons ce que Git a retenu.
      </p>

      <h3>3.1 — Corriger le code actuel</h3>
      <div class="code-block">
        <div class="code-header"><span class="code-lang">python</span></div>
        <pre><span class="kw">import</span> os
AWS_ACCESS_KEY <span class="op">=</span> os.environ.get(<span class="st">"AWS_ACCESS_KEY"</span>, <span class="st">""</span>)</pre>
      </div>

      <div class="code-block">
        <div class="code-header"><span class="code-lang">bash</span></div>
        <pre>git add app.py
git commit -m <span class="st">"fix: clé AWS chargée depuis variable d'environnement"</span></pre>
      </div>

      <h3>3.2 — Scanner tout l'historique</h3>
      <div class="code-block">
        <div class="code-header"><span class="code-lang">bash</span></div>
        <pre>gitleaks detect --source . --verbose</pre>
      </div>

      <div class="callout callout-info">
        <div class="callout-icon">ℹ</div>
        <div>Par défaut, <code>gitleaks detect</code> parcourt <strong>l'ensemble de l'historique Git</strong>, pas seulement le dernier état des fichiers.</div>
      </div>

      <div class="questions">
        <h4>Questions</h4>
        <ul>
          <li>Gitleaks trouve-t-il encore un secret ? Dans quel commit ?</li>
          <li>Le fichier <code>app.py</code> actuel ne contient plus la clé. Comment l'expliquez-vous ?</li>
        </ul>
      </div>
    </div>

    <!-- STEP 4 -->
    <hr>
    <div class="step" id="step4">
      <div class="step-header">
        <div class="step-num active">4</div>
        <h2>Remédiation — que faire face à un secret leaké ?</h2>
      </div>

      <h3>① Rotation du secret — action prioritaire</h3>
      <p class="step-desc">
        Un secret committé puis poussé est <strong>compromis</strong>, qu'il soit encore présent ou non dans le code.
        La seule remédiation fiable est de <strong>révoquer et régénérer la clé</strong> côté fournisseur.
        Supprimer le fichier ne dé-fuite rien.
      </p>

      <h3>② Nettoyage de l'historique — possible mais coûteux</h3>
      <p class="step-desc">
        Des outils comme <code>git filter-repo</code> ou <code>BFG Repo-Cleaner</code> permettent
        de purger un secret de tout l'historique. Mais ils <strong>réécrivent l'historique</strong> :
        tous les clones existants deviennent incohérents. C'est de la limitation de dégâts, pas une solution.
      </p>

      <h3>③ Prévention — la seule option vraiment économique</h3>
      <p class="step-desc">
        Le pre-commit hook de l'Étape 2 + un pipeline CI avec Gitleaks = aucun secret ne quitte le poste
        du développeur. C'est ce que vous avez mis en place.
      </p>

      <div class="callout callout-warn">
        <div class="callout-icon">⚠</div>
        <div><strong>Règle d'or :</strong> Supprimer un secret ≠ annuler la fuite. Git n'oublie rien. On révoque, on ne supprime pas.</div>
      </div>
    </div>

    <!-- DELIVERABLES -->
    <hr>
    <div class="deliverables" id="deliverables">
      <h3>Livrables attendus</h3>
      <div class="deliverable-item">
        <div class="check"></div>
        Sortie de <code>gitleaks detect</code> de l'Étape 1 (secret détecté + commit).
      </div>
      <div class="deliverable-item">
        <div class="check"></div>
        Capture du message de blocage du commit à l'Étape 2.
      </div>
      <div class="deliverable-item">
        <div class="check"></div>
        Sortie de <code>gitleaks detect</code> de l'Étape 3 (secret persistant dans l'historique).
      </div>
      <div class="deliverable-item">
        <div class="check"></div>
        Réponses aux questions des étapes 1, 2 et 3.
      </div>
    </div>

    <!-- FURTHER -->
    <hr>
    <div id="further">
      <h2>Pour aller plus loin</h2>
      <div class="callout callout-tip" style="margin-top:16px">
        <div class="callout-icon">🚀</div>
        <div>
          Intégrer Gitleaks dans le pipeline CI de ce projet (voir <code>.github/workflows/security.yml</code>).<br>
          Tester <code>trufflehog git file://.</code> et comparer ses résultats à Gitleaks.<br>
          Mettre en place le framework <code>pre-commit</code> partagé pour toute l'équipe.
        </div>
      </div>
    </div>

    <!-- FOOTER -->
    <div class="footer">
      <span>Free Mobile — DevSecOps Training · Lab 1</span>
      <span>Formateur : Yacine Romdhani &nbsp;·&nbsp; <a href="/">← Accueil</a></span>
    </div>

  </main>
</div>

<script>
  // Sidebar active on scroll
  const sections = document.querySelectorAll('[id]')
  const links = document.querySelectorAll('.sidebar a')
  window.addEventListener('scroll', () => {
    let current = ''
    sections.forEach(s => { if (window.scrollY >= s.offsetTop - 80) current = s.id })
    links.forEach(l => {
      l.classList.remove('active')
      if (l.getAttribute('href') === '#' + current) l.classList.add('active')
    })
  })
</script>
</body>
</html>""")


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
