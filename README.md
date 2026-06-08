# Lab DevSecOps Pipeline — 2h

> Mini-boutique **volontairement vulnérable** utilisée comme terrain d'entraînement DevSecOps.  
> Objectif : comprendre pourquoi et comment la sécurité s'intègre dans un pipeline CI/CD.

---

## Prérequis

| Outil | Vérification |
|-------|-------------|
| Git | `git --version` |
| Docker Desktop | `docker info` |
| Compte GitHub | pipeline CI via Actions |

---

## Démarrage rapide

```bash
git clone https://github.com/RomdhaniYacine/Lab1.git
cd Lab1
docker compose up --build
```

L'API tourne sur **http://localhost:5000**

---

## Structure du projet

```
Lab1/
├── app.py               ← Application Flask (vulnérable — point de départ)
├── Dockerfile           ← Image Docker (vulnérable)
├── requirements.txt     ← Dépendances (versions vulnérables)
├── docker-compose.yml   ← Lancement local
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
docker compose up --build
```

Ouvrez **http://localhost:5000/product?id=1** → vous voyez un produit.

### 1.2 Exploiter la faille SQL

Remplacez l'URL par :

```
http://localhost:5000/product?id=1 OR 1=1
```

**Résultat** : tous les produits s'affichent au lieu d'un seul.  
C'est une **injection SQL** : l'entrée utilisateur est collée directement dans la requête.

### 1.3 Exploiter la fuite de secrets

```
http://localhost:5000/health
```

**Résultat** : la clé API est visible en clair dans la réponse JSON.

### 1.4 Lire le code

Ouvrez `app.py`. Trouvez les 4 failles marquées `# ── FAILLE` et notez-les.

| # | Faille | Ligne |
|---|--------|-------|
| 1 | Secret en dur dans le code | ~8 |
| 2 | Injection SQL | ~33 |
| 3 | Secret exposé via `/health` | ~40 |
| 4 | `debug=True` en production | ~46 |

Ouvrez `Dockerfile`. Trouvez la faille #5 (image de base ancienne).

---

## Acte 2 — CI au rouge (25 min)

Le pipeline GitHub Actions est déjà configuré. Il se déclenche à chaque `push`.

### 2.1 Observer la CI échouer

Rendez-vous sur : **https://github.com/RomdhaniYacine/Lab1/actions**

Vous verrez 4 jobs :

| Job | Outil | Ce qu'il détecte |
|-----|-------|-----------------|
| 1 - Scan de secrets | **Gitleaks** | Clés API, mots de passe dans le code |
| 2 - SAST | **Semgrep** | Injection SQL, mauvaises pratiques code |
| 3 - Dépendances | **pip-audit** | Bibliothèques avec CVE connues |
| 4 - Image conteneur | **Trivy** | CVE dans l'image Docker de base |

### 2.2 Comprendre chaque échec

Cliquez sur chaque job en rouge et lisez le message d'erreur.  
Pour chaque job, répondez : **qu'est-ce qui a été détecté et pourquoi c'est dangereux ?**

---

## Acte 3 — Fix progressif (55 min)

Objectif : faire passer les 4 jobs au **vert** un par un.  
Commitez et pushez après chaque correction pour voir la CI évoluer en temps réel.

### Fix #1 — Supprimer les secrets du code

Dans `app.py`, remplacez les variables en dur par des variables d'environnement :

```python
# Avant
API_KEY = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
DB_PASSWORD = "SuperPassw0rd!"

# Après
import os
API_KEY = os.environ.get("API_KEY", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
```

Dans `docker-compose.yml`, décommentez la section `environment` et renseignez les valeurs.

```bash
git add app.py docker-compose.yml
git commit -m "fix: supprimer les secrets du code source"
git push
```

Attendez la CI → **Gitleaks passe au vert**.

---

### Fix #2 — Corriger l'injection SQL

Dans `app.py`, remplacez la concaténation par une requête paramétrée :

```python
# Avant
query = "SELECT name, price FROM products WHERE id = " + str(pid)
rows = conn.execute(query).fetchall()

# Après
rows = conn.execute("SELECT name, price FROM products WHERE id = ?", (pid,)).fetchall()
```

```bash
git add app.py
git commit -m "fix: requête paramétrée contre l'injection SQL"
git push
```

Attendez la CI → **Semgrep passe au vert**.

---

### Fix #3 — Supprimer la fuite de secret dans `/health`

Dans `app.py`, modifiez le endpoint `/health` :

```python
# Avant
return {"status": "ok", "api_key": API_KEY}

# Après
return {"status": "ok"}
```

---

### Fix #4 — Désactiver le mode debug

Dans `app.py`, modifiez le lancement de l'app :

```python
# Avant
app.run(host="0.0.0.0", port=5000, debug=True)

# Après
app.run(host="0.0.0.0", port=5000, debug=False)
```

```bash
git add app.py
git commit -m "fix: désactiver debug mode et supprimer fuite API key"
git push
```

---

### Fix #5 — Mettre à jour les dépendances

Dans `requirements.txt`, remplacez les versions vulnérables :

```
flask>=3.0.0
requests>=2.31.0
PyYAML>=6.0.1
Werkzeug>=3.0.0
```

```bash
git add requirements.txt
git commit -m "fix: mettre à jour les dépendances vers des versions sans CVE"
git push
```

Attendez la CI → **pip-audit passe au vert**.

---

### Fix #6 — Moderniser l'image Docker

Dans `Dockerfile`, remplacez l'image de base et ajoutez un utilisateur non-root :

```dockerfile
# Avant
FROM python:3.9

# Après
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

### Milestone final

Rendez-vous sur **https://github.com/RomdhaniYacine/Lab1/actions**

Les 4 jobs sont verts. Vous avez un pipeline DevSecOps fonctionnel.

---

## Acte 4 — Durcir le pipeline (20 min)

### 4.1 Simuler un nouveau secret accidentel

Ajoutez temporairement une ligne dans `app.py` :

```python
STRIPE_KEY = "sk_live_abc123xyz"
```

```bash
git add app.py && git commit -m "test: ajout accidentel d'un secret" && git push
```

Observez : **Gitleaks bloque immédiatement le merge**. C'est exactement le comportement voulu en production.

Supprimez la ligne et re-pushez.

### 4.2 Créer une Pull Request bloquée

```bash
git checkout -b feature/test-pr
# Réintroduire la faille SQL dans app.py
git add app.py && git commit -m "regression: retour injection SQL" && git push origin feature/test-pr
```

Ouvrez une Pull Request sur GitHub.  
Observez : la CI bloque la PR → **aucun code vulnérable ne peut être mergé sans que la CI valide**.

---

## Bilan

| Ce que vous avez mis en place | Équivalent en production |
|-------------------------------|--------------------------|
| Gitleaks sur chaque push | Empêche les secrets d'entrer dans le dépôt |
| Semgrep (SAST) | Détecte les failles de code avant la prod |
| pip-audit | Veille sur les CVE dans les dépendances |
| Trivy | Scan des images avant déploiement |
| PR bloquée par CI | Enforcement de la qualité sécurité sur la review |

> Ce pipeline est représentatif de ce qui est utilisé dans les équipes DevSecOps en production.

---

## En cas de blocage

Les fichiers corrigés sont disponibles dans le dossier `solution/`.
