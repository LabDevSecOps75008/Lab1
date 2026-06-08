# Lab 1 — Détection de secrets avec Gitleaks

**Durée estimée :** 1h00  
**Stack :** Python  
**Outil principal :** Gitleaks

---

## Objectifs pédagogiques

À la fin de ce TP, vous serez capable de :

1. Détecter un secret présent dans le code source avec un scanner automatique.
2. Mettre en place un pre-commit hook qui bloque un commit contenant un secret avant qu'il ne soit créé.
3. Comprendre qu'un secret supprimé du code reste présent dans l'historique Git, et savoir comment réagir.

---

## Prérequis

- `git` installé (`git --version`)
- `gitleaks` installé :
  - macOS : `brew install gitleaks`
  - Linux : télécharger le binaire depuis les [releases GitHub](https://github.com/gitleaks/gitleaks/releases)
  - Vérifier : `gitleaks version`
- Python 3.10+ (`python3 --version`)

---

## Contexte

Vous êtes développeur chez Free Mobile. Une API interne de gestion des abonnés vient d'être livrée par une équipe externe. En faisant la code review, vous remarquez que des credentials de production ont été écrits directement dans le code source — une erreur classique.

L'objectif est de voir comment les détecter automatiquement, puis d'apprendre à l'empêcher.

> ⚠️ Les credentials utilisés dans ce TP sont fictifs. N'utilisez jamais de vrais secrets dans un exercice.

---

## Étape 0 — Prise en main

Clonez le projet et lancez l'API :

```bash
git clone https://github.com/RomdhaniYacine/Lab1.git
cd Lab1
pip3 install -r requirements.txt
python3 app.py
```

Ouvrez **http://localhost:5000** — vous verrez le tableau de bord de l'API Free Mobile.

Parcourez `app.py`. Les premières lignes contiennent le code de production livré par l'équipe externe.

---

## Étape 1 — Détecter les secrets dans le code

Les credentials sont écrits en dur dans `app.py` :

```python
PROVISIONING_TOKEN = "freemobile_prov_api_4f8a2c1e9b3d7f05"
JWT_SECRET         = "fm-jwt-s1gn1ng-k3y-pr0d-2024!"
CDR_DB_PASSWORD    = "Fr33M0b!leCDR@Prod2024"
AWS_ACCESS_KEY_ID  = "LAB_AKIAIOSFODNN7FREEMOB"
MVNO_PARTNER_KEY   = "mvno_partner_key_9e8d7c6b5a4f3210"
```

Lancez un scan du dépôt :

```bash
gitleaks detect --source . --verbose
```

**Questions :**
- Que détecte Gitleaks ? Notez le type de secret, le fichier et le commit incriminé.
- Quel code de sortie renvoie Gitleaks ? (`echo $?` — 0 = rien trouvé, 1 = secret détecté.)

> 💡 Ce code de sortie est exactement ce qu'utilisera un pipeline CI pour faire échouer un build.

---

## Étape 2 — Prévenir : bloquer le commit avant qu'il n'arrive

Détecter après coup, c'est du nettoyage. L'objectif du *shift left* est d'empêcher la fuite dès le poste du développeur.

### 2.1 Installer le hook Git

Créez le fichier `.git/hooks/pre-commit` :

```bash
#!/bin/sh
gitleaks protect --staged --verbose
```

Rendez-le exécutable :

```bash
chmod +x .git/hooks/pre-commit
```

`gitleaks protect --staged` analyse uniquement ce qui est mis en stage (`git add`), donc le contenu sur le point d'être committé.

### 2.2 Tester le blocage

Ajoutez une nouvelle clé fictive dans `app.py` :

```python
STRIPE_KEY = "sk_live_4eC39HqLyjWDarjtT1zdp7dc"  # fictive
```

Tentez de committer :

```bash
git add app.py
git commit -m "Add payment integration"
```

**Question :** Le commit aboutit-il ? Que se passe-t-il ? Notez le message renvoyé par le hook.

Retirez ensuite la ligne sans la committer.

> 💡 Variante recommandée en entreprise : utiliser le framework `pre-commit` avec un `.pre-commit-config.yaml` qui appelle Gitleaks. C'est plus portable — le hook est versionné et partagé par toute l'équipe, contrairement à `.git/hooks/` qui reste local.

---

## Étape 3 — La vérité qui dérange : le secret est toujours dans l'historique

Le hook est en place, mais les secrets de l'Étape 1 ont été commités avant que le hook n'existe. Le code actuel semble propre — vérifions.

### 3.1 Corriger le code actuel

Remplacez les secrets hardcodés par des variables d'environnement dans `app.py` :

```python
import os

PROVISIONING_TOKEN = os.environ.get("PROVISIONING_TOKEN", "")
JWT_SECRET         = os.environ.get("JWT_SECRET", "")
CDR_DB_PASSWORD    = os.environ.get("CDR_DB_PASSWORD", "")
AWS_ACCESS_KEY_ID  = os.environ.get("AWS_ACCESS_KEY_ID", "")
MVNO_PARTNER_KEY   = os.environ.get("MVNO_PARTNER_KEY", "")
```

Committez ce correctif :

```bash
git add app.py
git commit -m "Fix: secrets déplacés en variables d'environnement"
```

### 3.2 Scanner tout l'historique

```bash
gitleaks detect --source . --verbose
```

Par défaut, `gitleaks detect` parcourt l'ensemble de l'historique Git — pas seulement l'état actuel des fichiers.

**Questions :**
- Gitleaks trouve-t-il encore les secrets ? Dans quel commit ?
- Pourtant `app.py` ne contient plus les clés. Comment l'expliquez-vous ?

---

## Étape 4 — Remédiation : que faire face à un secret leaké ?

1. **La première action est toujours la rotation.** Un secret committé doit être considéré comme compromis. La seule remédiation fiable est de révoquer et régénérer la clé côté fournisseur. Supprimer du code ne dé-fuite rien.

2. **Nettoyer l'historique est possible mais coûteux.** Des outils comme `git filter-repo` ou BFG Repo-Cleaner permettent de purger un secret, mais ils réécrivent l'historique — tous les clones existants deviennent incohérents. C'est de la limitation de dégâts, pas une solution.

3. **La prévention est la seule option vraiment économique** — d'où l'intérêt du hook de l'Étape 2.

---

## Livrables attendus

- La sortie de `gitleaks detect` de l'Étape 1 (secrets détectés).
- Une capture du message de blocage du commit à l'Étape 2.
- La sortie de `gitleaks detect` de l'Étape 3 prouvant que les secrets persistent dans l'historique malgré le correctif.
- Vos réponses aux questions des étapes 1, 2 et 3.

---

## Pour aller plus loin (optionnel)

- Intégrer Gitleaks dans le pipeline CI GitHub Actions (voir `.github/workflows/security.yml`).
- Tester `trufflehog git file://.` et comparer ses résultats à ceux de Gitleaks.
- Mettre en place le framework `pre-commit` partagé pour toute l'équipe.

---

## À retenir

Supprimer un secret ≠ annuler la fuite. Git n'oublie rien. Une fois poussé, un secret est compromis : on le révoque, on ne se contente pas de le supprimer. Le meilleur secret leaké est celui qui n'a jamais quitté le poste du développeur — grâce à un hook.
