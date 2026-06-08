# Lab 1 — Détection de Secrets & Pipeline CI/CD

> **Contexte** : Vous êtes développeur chez Free Mobile.
> Une API interne de gestion des abonnés et du réseau vient d'être livrée par une équipe externe.
> En faisant la code review, vous découvrez que **5 credentials de production** ont été commités
> directement dans le code. Votre mission : les détecter, construire le pipeline CI, et corriger.

---

## Objectifs pédagogiques

- Identifier des secrets dans du code source (tokens, passwords, clés AWS)
- Comprendre la différence entre **Gitleaks** (patterns) et **TruffleHog** (entropie + historique git)
- Comprendre pourquoi **supprimer un secret ne suffit pas** — il faut le révoquer
- Compléter un pipeline CI/CD de 5 jobs et le faire passer au vert

---

## Prérequis

| Outil | Vérification |
|-------|-------------|
| Git | `git --version` |
| Python 3.10+ | `python3 --version` |
| pip | `pip3 --version` |
| Compte GitHub | accès à l'onglet Actions |

---

## Démarrage rapide

```bash
# 1. Cloner le projet
git clone https://github.com/RomdhaniYacine/Lab1.git
cd Lab1

# 2. Installer les dépendances
pip3 install -r requirements.txt

# 3. Lancer l'application
python3 app.py
```

Ouvrez **http://localhost:5000** dans votre navigateur.

---

## Endpoints

| Route | Exemple | Vulnérabilité |
|-------|---------|---------------|
| `/` | — | Dashboard |
| `/subscriber/search` | `?msisdn=0612345678` | SQL Injection |
| `/sim/info` | `?iccid=8933150319080167234` | — |
| `/network/cell` | `?id=FR-5G-75001` | — |
| `/auth/token` | `?msisdn=0612345678` | JWT secret exposé |
| `/internal/config` | — | Tous les credentials |
| `/cdr/storage` | — | Clés AWS exposées |
| `/health` | — | Fuite RGPD |
| `/ip-manager` | — | Clé API hardcodée |
| `/tp` | — | Guide du lab |

---

## Structure du projet

```
Lab1/
├── app.py                          ← API Flask vulnérable (point de départ)
├── Dockerfile                      ← Image Docker (utilisée par Trivy dans le CI)
├── requirements.txt                ← Dépendances avec CVE connues
├── .github/workflows/
│   └── security.yml                ← Pipeline CI à compléter (5 TODO)
└── solution/
    ├── app.py                      ← Code corrigé
    ├── Dockerfile
    └── requirements.txt
```

---

## Acte 1 — Audit du code (20 min)

### 1.1 Identifier les 5 secrets

Ouvrez `app.py`. Cherchez les commentaires `# FAILLE`.

| # | Variable | Type | Impact si compromis |
|---|----------|------|---------------------|
| 1 | `PROVISIONING_TOKEN` | Token API réseau | Accès au provisioning SIM en production |
| 2 | `JWT_SECRET` | Clé signature JWT | Forge de sessions abonnés |
| 3 | `CDR_DB_PASSWORD` | Password MySQL | Accès aux CDR (enregistrements d'appels) prod |
| 4 | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` | Credentials AWS | Accès au stockage S3 des CDR |
| 5 | `MVNO_PARTNER_KEY` | Clé partenaire | Accès API partenaires MVNO |

### 1.2 Tester les failles en live

```bash
# Voir tous les credentials exposés
curl http://localhost:5000/internal/config

# Voir les clés AWS des CDR
curl http://localhost:5000/cdr/storage

# Générer un JWT signé avec le secret hardcodé
curl "http://localhost:5000/auth/token?msisdn=0612345678"
```

### 1.3 Exploiter la SQL injection

```bash
# Requête normale — 1 abonné
curl "http://localhost:5000/subscriber/search?msisdn=0612345678"

# SQL injection — tous les abonnés
curl "http://localhost:5000/subscriber/search?msisdn=0612345678' OR '1'='1"
```

En production chez Free Mobile : **28 400 000 abonnés exposés** (nom, email, MSISDN, ICCID, plan).

---

## Acte 2 — Construire le pipeline CI (25 min)

### 2.1 Votre mission

Ouvrez `.github/workflows/security.yml`.

Le fichier contient la structure des **5 jobs avec des `TODO`**.
Complétez chaque job en vous appuyant sur la documentation fournie dans les commentaires.

| # | Job | Outil | Ce qu'il doit détecter |
|---|-----|-------|------------------------|
| 1 | `gitleaks` | Gitleaks | Tokens, passwords, clés AWS dans le code |
| 2 | `trufflehog` | TruffleHog | Secrets dans tout l'historique git |
| 3 | `semgrep` | Semgrep | SQL injection, debug=True, mauvaises pratiques |
| 4 | `pip-audit` | pip-audit | CVE dans les dépendances Python |
| 5 | `trivy` | Trivy | CVE HIGH/CRITICAL dans l'image Docker |

Une fois complété, pushez et observez sur **https://github.com/RomdhaniYacine/Lab1/actions**

### 2.2 Gitleaks vs TruffleHog

| | Gitleaks | TruffleHog |
|---|----------|-----------|
| **Méthode** | Regex sur patterns connus (AWS, GitHub, etc.) | Entropie de Shannon + patterns + vérification |
| **Scope** | Code actuel | Code actuel + **tout l'historique git** |
| **Point fort** | Rapide, peu de faux positifs | Détecte les secrets supprimés dans d'anciens commits |
| **Usage** | Pre-commit hook, CI | Audit complet d'un dépôt |

> **Règle d'or** : un secret dans l'historique git doit être **révoqué**, pas juste supprimé.

---

## Acte 3 — Correction (40 min)

### Fix #1 — Variables d'environnement

```python
# Avant (dangereux)
PROVISIONING_TOKEN = "freemobile_prov_api_4f8a2c1e9b3d7f05"
JWT_SECRET         = "fm-jwt-s1gn1ng-k3y-pr0d-2024!"
CDR_DB_PASSWORD    = "Fr33M0b!leCDR@Prod2024"
AWS_ACCESS_KEY_ID  = "AKIAIOSFODNN7FREEMOB"

# Après (correct)
import os
PROVISIONING_TOKEN = os.environ.get("PROVISIONING_TOKEN", "")
JWT_SECRET         = os.environ.get("JWT_SECRET", "")
CDR_DB_PASSWORD    = os.environ.get("CDR_DB_PASSWORD", "")
AWS_ACCESS_KEY_ID  = os.environ.get("AWS_ACCESS_KEY_ID", "")
```

```bash
git add app.py && git commit -m "fix: secrets déplacés en variables d'environnement" && git push
```

### Fix #2 — Requête paramétrée

```python
# Avant — SQL Injection possible
query = "SELECT * FROM subscribers WHERE msisdn = '" + msisdn + "'"
rows  = conn.execute(query).fetchall()

# Après — requête paramétrée
rows = conn.execute(
    "SELECT id, msisdn, iccid, name, email, plan, data_used_gb FROM subscribers WHERE msisdn = ?",
    (msisdn,)
).fetchall()
```

### Fix #3 — Supprimer les endpoints dangereux

- `/internal/config` : supprimer ou protéger avec authentification
- `/cdr/storage` : ne jamais exposer des credentials AWS
- `/health` : retourner uniquement `{"status": "ok"}`
- `debug=False` dans `app.run()`

### Fix #4 — Mettre à jour les dépendances

```
# requirements.txt corrigé
flask>=3.0.0
requests>=2.31.0
PyYAML>=6.0.1
Werkzeug>=3.0.0
```

---

## Acte 4 — TruffleHog et l'historique git (15 min)

### Démontrer que la suppression ne suffit pas

```bash
# Ajouter un faux token dans le code
echo 'TEMP_TOKEN = "ghp_fakeGitHubToken1234567890abc"' >> app.py
git add app.py && git commit -m "test: token temporaire"

# Le supprimer dans le commit suivant
git revert HEAD --no-edit && git push
```

TruffleHog détecte le token dans l'historique malgré la suppression.
**Conclusion** : il faut révoquer le token sur GitHub, pas juste le supprimer.

---

## Bilan

| Mis en place | Impact chez Free Mobile |
|---|---|
| **Gitleaks** | Bloque les credentials avant le push |
| **TruffleHog** | Audite l'historique, rien ne passe inaperçu |
| **Semgrep** | Stoppe les injections SQL avant la prod |
| **pip-audit** | Veille CVE sur les dépendances en continu |
| **Trivy** | Garantit des images sans CVE critiques |

---

## En cas de blocage

Les fichiers corrigés sont disponibles dans `solution/`.
