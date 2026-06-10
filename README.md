# Lab 1 — Détection de secrets avec Gitleaks

**Durée estimée : 1h30** &nbsp;|&nbsp; **Stack : Python / Flask** &nbsp;|&nbsp; **Outil : Gitleaks**

---

## Contexte

L'équipe sécurité de Free Mobile a reçu une alerte : le dépôt `freemobile-api` contient des credentials exposés dans le code source.

Votre mission : détecter les secrets, mettre en place les garde-fous automatiques (pipeline CI et pre-commit hook), puis corriger le code.

**Impact potentiel d'une fuite :** accès aux données abonnés, compromission AWS, facturation frauduleuse.

---

## Prérequis

| Outil | Vérification |
|-------|-------------|
| Docker | `docker --version` |
| Gitleaks | `gitleaks version` |
| pre-commit | `pre-commit --version` |
| Compte GitHub | accès à l'onglet Actions |

**Installer Gitleaks :**

```bash
# macOS
brew install gitleaks

# Linux / WSL
GITLEAKS_VERSION=$(curl -s https://api.github.com/repos/gitleaks/gitleaks/releases/latest | grep '"tag_name"' | cut -d'"' -f4 | sed 's/v//')
curl -sSfL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" | tar -xz
mkdir -p ~/.local/bin && mv gitleaks ~/.local/bin/
export PATH="$HOME/.local/bin:$PATH"

# Vérification
gitleaks version
```

**Installer pre-commit :**

```bash
pip install pre-commit
pre-commit --version
```

---

## Structure du projet

```
Lab1/
├── app.py                        ← API Flask (secrets hardcodés)
├── requirements.txt
├── docker-compose.yml
├── .env.example                  ← Template pour les variables d'environnement
└── .github/
    └── workflows/
        └── security.yml          ← Pipeline CI à compléter
```

---

## Étape 1 — Scanner avec Gitleaks

Gitleaks détecte les secrets en comparant le code à des patterns regex connus. Il scanne le code **et** l'historique git complet.

```bash
gitleaks detect --source . --verbose
echo "Exit code: $?"
```

> `0` = aucun secret détecté &nbsp;|&nbsp; `1` = secret(s) détecté(s)

**Questions :**
- Combien de secrets Gitleaks a-t-il détectés ?
- Dans quel fichier et à quelles lignes ?
- Quel serait l'impact métier si chacun était compromis ?

---

## Étape 2 — Construire la pipeline CI

Complétez `.github/workflows/security.yml` pour que la pipeline lance un scan Gitleaks à chaque push.

> **Référence :** [github.com/gitleaks/gitleaks-action](https://github.com/gitleaks/gitleaks-action)

```bash
git add .github/workflows/security.yml
git commit -m "ci: pipeline Gitleaks"
git push
```

Observez le résultat sur l'onglet **Actions**. La pipeline doit échouer — des secrets sont présents dans le code.

---

## Étape 3 — Corriger le code

Remplacez tous les secrets hardcodés par des variables d'environnement.

```python
import os
from dotenv import load_dotenv

load_dotenv()

FREEMOBILE_API_KEY = os.environ.get("FREEMOBILE_API_KEY")
# … idem pour les autres secrets
```

Configurez votre fichier `.env` local :

```bash
cp .env.example .env
# Remplir .env avec des valeurs fictives
# Ce fichier est dans .gitignore — ne jamais le committer
```

Committez et poussez :

```bash
git add app.py
git commit -m "fix: secrets déplacés en variables d'environnement"
git push
```

Observez l'onglet **Actions** — la pipeline échoue encore.

> **Pourquoi ?** Un secret présent dans un commit **persiste dans l'historique git** même après suppression du code. Gitleaks scanne tous les commits, pas seulement l'état actuel. La seule garantie réelle : révoquer et remplacer le secret compromis.

---

## Étape 4 — Pre-commit hook

Un pre-commit hook bloque le commit **avant** que le secret n'atteigne le repo.

Créez un fichier `.pre-commit-config.yaml` à la racine du projet et configurez-le pour lancer Gitleaks à chaque commit.

> **Référence :** [github.com/gitleaks/gitleaks#pre-commit](https://github.com/gitleaks/gitleaks#pre-commit)

```bash
pre-commit install
```

**Tester le blocage :**

```bash
echo 'TOKEN = "test-secret-value-fakek3y-12345abc"' >> test_hook.py
git add test_hook.py
git commit -m "test: vérification du hook"
# → Le commit doit être bloqué par Gitleaks

# Nettoyer
rm test_hook.py
git reset HEAD test_hook.py 2>/dev/null || true
```

**Questions :**
- À quel moment du cycle de développement ce hook intervient-il ?
- Peut-il être contourné ? Si oui, comment ?
- Quelle est la différence entre ce hook et la pipeline CI ?

---

## Livrables attendus

- La sortie de `gitleaks detect` avec les secrets détectés.
- La pipeline CI en échec (screenshot GitHub Actions).
- Le hook pre-commit en action (screenshot du commit bloqué).
- Réponses aux questions des étapes 1 et 4.

---

## Pour aller plus loin

- **TruffleHog** — combine regex et analyse d'entropie pour détecter des secrets sans pattern connu
- **detect-secrets** — crée une baseline des secrets existants pour ne signaler que les nouveaux
- **Remédiation de l'historique** — `git filter-repo` pour réécrire les commits contenant des secrets (⚠ force push requis)
