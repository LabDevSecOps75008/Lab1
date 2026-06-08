# Lab 1 — Secrets Detection & Pipeline CI

> **Contexte** : Un développeur Free a livré une API interne de gestion des abonnés.
> En faisant la code review, vous découvrez que **5 types de credentials** ont été
> commités directement dans le code source. Votre mission : les détecter avec les
> outils CI, comprendre leur impact, et les corriger proprement.

---

## Objectifs

- Identifier des secrets dans du code source
- Comprendre la différence entre **Gitleaks** (patterns) et **TruffleHog** (entropie + historique)
- Comprendre pourquoi **supprimer un secret ne suffit pas** — il faut le révoquer
- Faire passer un pipeline de 5 jobs du rouge au vert

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
pip3 install flask
pip3 install -r requirements.txt

# 3. Lancer l'application
python3 app.py
```

> Si `pip3` n'est pas reconnu, utilisez `pip` à la place.

L'API tourne sur **http://localhost:5000**

---

## Endpoints

| Route | Exemple | Faille |
|-------|---------|--------|
| `/subscriber` | `/subscriber?phone=0612345678` | SQL Injection |
| `/auth/token` | `/auth/token?user_id=1` | JWT Secret exposé |
| `/admin/config` | `/admin/config` | Tous les credentials en clair |
| `/backup/status` | `/backup/status` | Clés AWS S3 exposées |
| `/line-status` | `/line-status?id=FBX-29471` | OK |
| `/health` | `/health` | Fuite RGPD |

---

## Structure du projet

```
Lab1/
├── app.py                      ← API Flask vulnérable (point de départ)
├── Dockerfile                  ← Image Docker vulnérable
├── requirements.txt            ← Dépendances avec CVE
├── docker-compose.yml          ← Lancement via Docker
├── solution/                   ← Code corrigé (à ouvrir APRÈS avoir essayé)
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
└── .github/workflows/
    └── security.yml            ← Pipeline CI (5 jobs de sécurité)
```

---

## Acte 1 — Découverte des secrets (20 min)

### 1.1 Inspecter le code source

Ouvrez `app.py` et cherchez les lignes marquées `# FAILLE`.

Identifiez les **5 secrets** présents dans le code :

| # | Variable | Type de secret | Impact si compromis |
|---|----------|---------------|---------------------|
| 1 | `FREE_INTERNAL_TOKEN` | Token API interne | Accès aux systèmes internes Free |
| 2 | `JWT_SECRET` | Clé de signature JWT | Forge de sessions abonnés |
| 3 | `DB_PASSWORD` | Mot de passe MySQL prod | Accès direct à la base de production |
| 4 | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` | Credentials AWS | Accès aux backups de facturation S3 |
| 5 | `OAUTH2_CLIENT_SECRET` | Secret OAuth2 | Compromission du SSO Free |

### 1.2 Tester l'exposition des secrets

```bash
# Voir tous les credentials exposés dans /admin/config
curl http://localhost:5000/admin/config

# Voir les clés AWS dans /backup/status
curl http://localhost:5000/backup/status

# Générer un JWT signé avec le secret hardcodé
curl "http://localhost:5000/auth/token?user_id=1"
```

### 1.3 Exploiter la faille SQL

```bash
# Requête normale — retourne 1 abonné
curl "http://localhost:5000/subscriber?phone=0612345678"

# Injection SQL — retourne TOUS les abonnés
curl "http://localhost:5000/subscriber?phone=0612345678' OR '1'='1"
```

En production chez Free, cette requête exposerait des **millions d'abonnés** : noms, emails, plans, consommation data.

---

## Acte 2 — Observer le pipeline en échec (20 min)

### 2.1 Les 5 jobs CI

Rendez-vous sur **https://github.com/RomdhaniYacine/Lab1/actions**

| # | Job | Outil | Ce qu'il détecte |
|---|-----|-------|-----------------|
| 1 | Secrets (Gitleaks) | **Gitleaks** | Patterns connus : tokens, passwords, clés AWS |
| 2 | Secrets historique (TruffleHog) | **TruffleHog** | Entropie élevée + scan de tout l'historique git |
| 3 | SAST (Semgrep) | **Semgrep** | Injection SQL, debug=True, mauvaises pratiques |
| 4 | Dépendances (pip-audit) | **pip-audit** | CVE dans flask 2.0.1, requests 2.19.1, PyYAML 5.1 |
| 5 | Image conteneur (Trivy) | **Trivy** | CVE HIGH/CRITICAL dans python:3.9 |

### 2.2 Gitleaks vs TruffleHog — quelle différence ?

| | Gitleaks | TruffleHog |
|---|----------|-----------|
| **Méthode** | Patterns regex connus (AWS, GitHub, etc.) | Entropie de Shannon + patterns + vérification |
| **Scope** | Code actuel | Code actuel + **tout l'historique git** |
| **Force** | Rapide, peu de faux positifs | Détecte les secrets supprimés dans d'anciens commits |
| **Cas d'usage** | Empêcher un commit | Auditer un repo existant |

> **Règle d'or** : un secret committé dans git, même supprimé ensuite, reste dans l'historique.
> Il faut **révoquer le secret** (changer le mot de passe, invalider le token), pas juste le supprimer.

---

## Acte 3 — Correction des secrets (40 min)

### Fix #1 — Remplacer tous les secrets par des variables d'environnement

Dans `app.py`, remplacez les valeurs en dur :

```python
# Avant
FREE_INTERNAL_TOKEN   = "freetelecom_internal_api_x7k9m2p4q1"
JWT_SECRET            = "fr33-s3cr3t-jwt-pr0d-2024!"
DB_PASSWORD           = "FreeProd@MySQL2024!"
AWS_ACCESS_KEY_ID     = "AKIAIOSFODNN7FREETEL"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYFREETELECOM"
OAUTH2_CLIENT_SECRET  = "oauth2_free_9f8e7d6c5b4a3210abcdef1234567890"

# Après
FREE_INTERNAL_TOKEN   = os.environ.get("FREE_INTERNAL_TOKEN", "")
JWT_SECRET            = os.environ.get("JWT_SECRET", "")
DB_PASSWORD           = os.environ.get("DB_PASSWORD", "")
AWS_ACCESS_KEY_ID     = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
OAUTH2_CLIENT_SECRET  = os.environ.get("OAUTH2_CLIENT_SECRET", "")
```

Dans `docker-compose.yml`, décommentez la section `environment`.

```bash
git add app.py docker-compose.yml
git commit -m "fix: remplacer les secrets hardcodés par des variables d'environnement"
git push
```

Attendez la CI → **Gitleaks et TruffleHog passent au vert**.

---

### Fix #2 — Corriger l'injection SQL

```python
# Avant
query = "SELECT ... FROM subscribers WHERE phone = '" + phone + "'"
rows  = conn.execute(query).fetchall()

# Après
rows = conn.execute(
    "SELECT id, phone, name, email, plan, data_used_gb FROM subscribers WHERE phone = ?",
    (phone,)
).fetchall()
```

```bash
git add app.py
git commit -m "fix: requête paramétrée — injection SQL corrigée"
git push
```

Attendez la CI → **Semgrep passe au vert**.

---

### Fix #3 — Nettoyer /admin/config et /health

`/admin/config` ne doit pas exister sans authentification. Supprimez l'endpoint ou protégez-le.

`/health` ne doit retourner que le statut :

```python
@app.route("/health")
def health():
    return jsonify({"status": "ok"})
```

Désactivez aussi le mode debug :

```python
app.run(host="0.0.0.0", port=5000, debug=False)
```

```bash
git add app.py
git commit -m "fix: supprimer exposition config, RGPD et debug mode"
git push
```

---

### Fix #4 — Mettre à jour les dépendances

```
flask>=3.0.0
requests>=2.31.0
PyYAML>=6.0.1
Werkzeug>=3.0.0
```

```bash
git add requirements.txt
git commit -m "fix: dépendances mises à jour — suppression CVE connues"
git push
```

Attendez la CI → **pip-audit passe au vert**.

---

### Fix #5 — Moderniser l'image Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 5000
CMD ["python", "app.py"]
```

```bash
git add Dockerfile
git commit -m "fix: image python:3.12-slim et utilisateur non-root"
git push
```

Attendez la CI → **Trivy passe au vert**.

---

## Acte 4 — TruffleHog et l'historique git (20 min)

### 4.1 Démontrer que la suppression ne suffit pas

```bash
# Créer un commit avec un faux secret
echo 'BACKUP_TOKEN = "ghp_faketoken1234567890abcdef"' >> app.py
git add app.py && git commit -m "test: ajout token temporaire"

# Le supprimer dans le commit suivant
git revert HEAD --no-edit
git push
```

Observez : **TruffleHog détecte le secret dans l'historique** même après suppression.

**Conclusion** : il faut révoquer le token sur GitHub, pas juste le supprimer du code.

### 4.2 Créer une Pull Request bloquée

```bash
git checkout -b feature/nouvelle-api
# Réintroduire une concaténation SQL
git add app.py && git commit -m "perf: refacto requête abonnés"
git push origin feature/nouvelle-api
```

Ouvrez une PR → Semgrep bloque automatiquement le merge.

---

## Bilan

| Ce que vous avez mis en place | Impact en production Free |
|-------------------------------|--------------------------|
| **Gitleaks** | Bloque les tokens/passwords avant le push |
| **TruffleHog** | Audite tout l'historique, détecte les secrets oubliés |
| **Semgrep** | Arrête les injections SQL et les mauvaises pratiques |
| **pip-audit** | Veille CVE en continu sur les dépendances |
| **Trivy** | Garantit que les images déployées sont sans CVE critiques |
| **PR bloquée** | Aucune régression sécurité ne peut être mergée |

---

## En cas de blocage

Les fichiers corrigés sont disponibles dans `solution/`.
