# Lab DevSecOps Pipeline — 2h

> **Contexte** : vous êtes développeur chez Free. Cette API REST gère les abonnés en interne —
> consultation d'abonnés, statut de ligne Freebox, facturation.  
> Le code vient d'être livré par une équipe externe. Votre mission : l'auditer, corriger les failles,
> et faire passer la CI de rouge au vert.

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

# 2. Installer Flask et les dépendances
pip3 install flask
pip3 install -r requirements.txt

# 3. Lancer l'application
python3 app.py
```

L'API tourne sur **http://localhost:5000**

> Si `pip3` n'est pas reconnu, essayez `pip` à la place.

---

## Endpoints disponibles

| Endpoint | Exemple | Description |
|----------|---------|-------------|
| `/subscriber` | `/subscriber?phone=0612345678` | Recherche abonné par numéro |
| `/line-status` | `/line-status?id=FBX-29471` | Statut d'une ligne Freebox |
| `/invoice` | `/invoice?account=1` | Consultation de facture |
| `/health` | `/health` | Healthcheck interne |

---

## Structure du projet

```
Lab1/
├── app.py               ← API Flask (vulnérable — point de départ)
├── Dockerfile           ← Image Docker (vulnérable)
├── requirements.txt     ← Dépendances (versions vulnérables)
├── docker-compose.yml   ← Lancement via Docker
├── solution/            ← Code corrigé (à ouvrir APRÈS avoir essayé)
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
└── .github/
    └── workflows/
        └── security.yml ← Pipeline CI (4 outils de sécurité)
```

---

## Acte 1 — Découverte (20 min)

### 1.1 Lancer l'application

```bash
pip3 install -r requirements.txt
python3 app.py
```

### 1.2 Tester les endpoints normaux

```bash
# Recherche d'un abonné
curl "http://localhost:5000/subscriber?phone=0612345678"

# Statut d'une ligne Freebox
curl "http://localhost:5000/line-status?id=FBX-29471"

# Facture
curl "http://localhost:5000/invoice?account=1"
```

### 1.3 Exploiter la faille SQL — extraire TOUS les abonnés

```bash
curl "http://localhost:5000/subscriber?phone=0612345678' OR '1'='1"
```

**Résultat** : les 5 abonnés s'affichent au lieu d'un seul.  
En production chez Free, cette requête retourne **des millions de lignes** : noms, emails, numéros de téléphone.  
C'est un **incident de sécurité majeur** et une violation directe du RGPD.

### 1.4 Exploiter la fuite de données dans /health

```bash
curl "http://localhost:5000/health"
```

**Résultat** : le healthcheck expose en clair :
- Le token API interne Free
- Le mot de passe de la base de production
- Le nom, email et IBAN du dernier abonné enregistré

Un simple scan automatisé de ports peut découvrir cet endpoint. **Amende RGPD potentielle : jusqu'à 4% du chiffre d'affaires annuel.**

### 1.5 Lire le code source

Ouvrez `app.py` et repérez les 4 commentaires `# ── FAILLE`.

| # | Faille | Risque |
|---|--------|--------|
| 1 | Credentials en dur dans le code | Compromission de la prod si le repo est exposé |
| 2 | Injection SQL sur `/subscriber` | Exfiltration de toute la base abonnés |
| 3 | RGPD + secrets dans `/health` | Violation RGPD, credentials prod exposés |
| 4 | `debug=True` en production | Console Werkzeug = exécution de code arbitraire |

Ouvrez `Dockerfile`. La faille #5 est l'image de base `python:3.9`, criblée de CVE.

---

## Acte 2 — CI au rouge (25 min)

Le pipeline GitHub Actions se déclenche à chaque `push`.

### 2.1 Observer les 4 jobs en échec

Rendez-vous sur **https://github.com/RomdhaniYacine/Lab1/actions**

| Job | Outil | Ce qu'il détecte |
|-----|-------|-----------------|
| 1 — Scan de secrets | **Gitleaks** | `INTERNAL_API_TOKEN` et `DB_PASSWORD` en dur |
| 2 — SAST | **Semgrep** | Injection SQL dans `/subscriber` |
| 3 — Dépendances | **pip-audit** | CVE dans flask 2.0.1, requests 2.19.1, PyYAML 5.1 |
| 4 — Image conteneur | **Trivy** | CVE HIGH/CRITICAL dans python:3.9 |

### 2.2 Analyser chaque rapport

Pour chaque job en rouge, ouvrez les logs et répondez :
- Qu'est-ce qui a été détecté ?
- Quel est l'impact métier pour Free ?
- Comment le corriger ?

---

## Acte 3 — Fix progressif (55 min)

Corrigez faille par faille et pushez après chaque correction pour voir la CI évoluer.

---

### Fix #1 — Supprimer les credentials du code

Dans `app.py`, remplacez les valeurs en dur par des variables d'environnement :

```python
# Avant
INTERNAL_API_TOKEN = "freetelecom_internal_api_x7k9m2p4q1"
DB_PASSWORD = "FreeProd@MySQL2024!"

# Après
INTERNAL_API_TOKEN = os.environ.get("INTERNAL_API_TOKEN", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
```

Dans `docker-compose.yml`, décommentez la section `environment`.

```bash
git add app.py docker-compose.yml
git commit -m "fix: supprimer les credentials du code source"
git push
```

Attendez la CI → **Gitleaks passe au vert**.

---

### Fix #2 — Corriger l'injection SQL

Dans `app.py`, remplacez la concaténation par une requête paramétrée :

```python
# Avant
query = "SELECT id, phone, name, email, plan, data_used_gb FROM subscribers WHERE phone = '" + phone + "'"
rows = conn.execute(query).fetchall()

# Après
rows = conn.execute(
    "SELECT id, phone, name, email, plan, data_used_gb FROM subscribers WHERE phone = ?",
    (phone,)
).fetchall()
```

Vérifiez que l'exploit ne fonctionne plus :

```bash
curl "http://localhost:5000/subscriber?phone=0612345678' OR '1'='1"
# Doit retourner [] — aucun résultat
```

```bash
git add app.py
git commit -m "fix: requête paramétrée sur /subscriber — injection SQL corrigée"
git push
```

Attendez la CI → **Semgrep passe au vert**.

---

### Fix #3 — Nettoyer le healthcheck

Dans `app.py`, supprimez toute donnée sensible du `/health` :

```python
@app.route("/health")
def health():
    return jsonify({"status": "ok"})
```

---

### Fix #4 — Désactiver le mode debug

```python
# Avant
app.run(host="0.0.0.0", port=5000, debug=True)

# Après
app.run(host="0.0.0.0", port=5000, debug=False)
```

```bash
git add app.py
git commit -m "fix: désactiver debug mode et supprimer fuite RGPD dans /health"
git push
```

---

### Fix #5 — Mettre à jour les dépendances

Dans `requirements.txt` :

```
flask>=3.0.0
requests>=2.31.0
PyYAML>=6.0.1
Werkzeug>=3.0.0
```

```bash
git add requirements.txt
git commit -m "fix: dépendances mises à jour — suppression des CVE connues"
git push
```

Attendez la CI → **pip-audit passe au vert**.

---

### Fix #6 — Moderniser l'image Docker

Dans `Dockerfile` :

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

### Milestone — Pipeline 100% vert

Rendez-vous sur **https://github.com/RomdhaniYacine/Lab1/actions**

Les 4 jobs sont verts. Cette API peut désormais être déployée en toute confiance.

---

## Acte 4 — Durcir le pipeline (20 min)

### 4.1 Simuler un credential committé par erreur

```bash
# Ajoutez dans app.py :
# STRIPE_SECRET = "sk_live_abc123FreeTelecom"

git add app.py && git commit -m "feat: ajout passerelle paiement" && git push
```

**Résultat** : Gitleaks bloque immédiatement. Le credential n'atteint jamais la production.

Supprimez la ligne et re-pushez.

### 4.2 Créer une Pull Request bloquée par la CI

```bash
git checkout -b feature/nouvelle-api
# Réintroduire la concaténation SQL dans /subscriber
git add app.py
git commit -m "perf: optimisation requête abonnés"
git push origin feature/nouvelle-api
```

Ouvrez une Pull Request sur GitHub.  
Semgrep détecte la régression et **bloque le merge automatiquement**.

---

## Bilan

| Ce que vous avez mis en place | Équivalent en production chez Free |
|-------------------------------|-----------------------------------|
| Gitleaks sur chaque push | Empêche les credentials de fuiter dans le dépôt |
| Semgrep (SAST) | Détecte les injections SQL avant le déploiement |
| pip-audit | Veille CVE sur les dépendances Python |
| Trivy | Scan des images avant mise en production |
| PR bloquée par CI | Aucune régression sécurité ne peut être mergée |

> Ce pipeline est représentatif de ce qui est déployé dans les équipes DevSecOps en production.

---

## En cas de blocage

Les fichiers corrigés sont disponibles dans `solution/`.
