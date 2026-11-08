# 🚀 GIT-RITUAL

> init • commit • push — sans les galères

**Git-Ritual** est un outil interactif en ligne de commande (Python + Rich) qui automatise le « rituel » pour publier un projet sur GitHub depuis Termux : identité Git, clé SSH, dépôt local, commit, adresse distante, envoi, et réparation automatique des erreurs classiques.

## Ce qu'il fait à votre place

| Menu | Action |
|---|---|
| 1 | **Publier un projet** : `git init`, `.gitignore`, commit, branche, adresse du dépôt, push |
| 2 | **Mettre à jour** un projet : `add` + `commit` + `push` |
| 3 | **Statut** : branche, adresse, synchronisation, modifications, derniers commits |
| 4 | **Corriger l'adresse** du dépôt distant (après vérification) |
| 5 | **Assistant** : identité Git, création/test de la clé SSH |
| s | **Réglages** : pseudo, branche, message de commit, couleur… |

### Erreurs gérées automatiquement

| Message de Git | Ce que fait l'outil |
|---|---|
| `Repository not found` | Explique les causes (nom, majuscules, `-` / `_`), propose les dépôts au nom proche (avec `gh`), crée le dépôt (avec `gh`) ou ouvre `github.com/new` |
| `Permission denied (publickey)` | Lance l'assistant SSH (clé, copie, test) |
| `Invalid username or token` (HTTPS) | Convertit les adresses GitHub HTTPS en SSH |
| `rejected … (fetch first)` / `non-fast-forward` | Propose la fusion (`--allow-unrelated-histories --no-rebase`) puis réessaie |
| `divergent branches` | Évité : fusion sans rebase imposée explicitement |
| Conflit de fusion (ex. `README.md`) | Vous laissez choisir : ma version, celle de GitHub, ou annuler |
| `usage: git remote add …` (espace dans l'adresse) | Nettoie les espaces parasites de la saisie |

### Garde-fous

- Détecte les fichiers qui ressemblent à des secrets (`.env`, `*.pem`, `id_ed25519`, …) et propose de les exclure via `.gitignore`.
- Ne fait **jamais** de `git push --force`.
- Vérifie l'adresse (`git ls-remote`) avant d'enregistrer le remote.
- Refuse de publier votre dossier personnel entier.
- Ne remplace jamais une clé SSH existante.
- Accepte aussi d'autres hébergeurs (GitLab, Codeberg…) en collant l'adresse complète.

## Installation (Termux)

```bash
pkg update && pkg install python git openssh -y
pkg install gh -y            # facultatif : création de dépôt depuis l'outil

cd ~
unzip ~/storage/downloads/git-ritual.zip
cd git-ritual
pip install -r requirements.txt
python main.py
```

Raccourci pratique : `echo "alias ritual='python ~/git-ritual/main.py'" >> ~/.bashrc` puis `ritual`.

Au premier lancement, utilisez le menu **5** (assistant) : il configure l'identité et la clé SSH, et mémorise votre pseudo GitHub.

Pour `gh` (facultatif) : `gh auth login`.

## Architecture

```
git-ritual/
├── main.py
├── requirements.txt
├── core/                    # logique pure, sans interface
│   ├── shell.py             # exécution de commandes (sans shell, messages en anglais)
│   ├── git_ops.py           # dépôt, commit, remote, push, fusion, conflits
│   ├── ssh.py               # clés SSH, test de connexion GitHub
│   ├── github.py            # adresses de dépôts, CLI gh, ouverture de liens
│   ├── diagnostics.py       # reconnaissance et explication des erreurs
│   ├── safety.py            # fichiers sensibles, .gitignore
│   └── storage.py           # réglages et projets récents (JSON)
├── interface/
│   ├── display.py           # rendu Rich
│   ├── prompts.py           # saisies
│   └── menus.py             # menu principal, réglages, gestion d'erreurs
├── workflows/               # parcours interactifs
│   ├── setup.py             # identité + SSH
│   ├── common.py            # projet, commit, remote, push avec récupération
│   ├── publish.py           # le rituel complet
│   └── sync.py              # mise à jour, statut, correction du remote
├── utils/
│   ├── validators.py
│   └── paths.py
└── tests/
```

## Tests

```bash
python -m unittest discover -v
```

Les tests utilisent un vrai Git avec des dépôts locaux temporaires (rejet de push, fusion, conflits). Les appels à SSH et `gh` sont simulés.

## Données

Réglages dans `~/.git-ritual/settings.json` (modifiable via `GIT_RITUAL_HOME`).

## Licence

MIT — voir [LICENSE](LICENSE).
