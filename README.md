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

## Installation

Git-Ritual est du Python pur (seule dépendance : `rich`, elle aussi 100 % Python). `git` et `ssh` doivent être présents sur la machine ; `gh` reste facultatif.

| Situation | Commande |
|---|---|
| **Termux** (depuis ce dossier ou le zip) | `bash install.sh` |
| **Termux** (version publiée) | `bash install.sh --pypi` |
| Linux / macOS / Windows avec `pipx` | `pipx install git-ritual` |
| Aucune installation (clé USB, zip) | `pip install rich` puis `python main.py` |
| Un seul fichier | `python ritual.pyz` (voir la page des *Releases*) |
| Hors ligne | dossier *wheelhouse* + `GIT_RITUAL_PIP_ARGS="--no-index --find-links wheelhouse" bash install.sh --pypi` |
| Sans Python | binaire de la page des *Releases* (Linux, macOS, Windows ; **pas Termux**) |

### Termux, pas à pas

```bash
pkg update && pkg install python git openssh -y
pkg install gh -y            # facultatif : création de dépôt depuis l'outil

cd ~
unzip ~/storage/downloads/git-ritual.zip
cd git-ritual
bash install.sh              # crée un environnement privé et la commande « ritual »
ritual
```

`install.sh` est relançable : il met à jour une installation existante. `bash install.sh --uninstall` la supprime (vos réglages et vos clés SSH ne sont pas touchés). `--alias` crée un alias au lieu d'un lien dans le PATH.

Au premier lancement, utilisez le menu **5** (assistant) : il configure l'identité et la clé SSH, et mémorise votre pseudo GitHub. Pour `gh` (facultatif) : `gh auth login`.

### Windows

Utilisez **Windows Terminal** (pas l'ancienne console) et installez Git for Windows (qui fournit aussi `ssh`). Puis `pipx install git-ritual`, ou `py -m pip install --user git-ritual`.

## Architecture

```
git-ritual/
├── pyproject.toml           # métadonnées, dépendances, commande `ritual`
├── main.py                  # lanceur sans installation (python main.py)
├── install.sh               # installateur Termux / Linux / macOS
├── src/git_ritual/
│   ├── cli.py               # point d'entrée (ritual, python -m git_ritual)
│   ├── core/                # logique pure, sans interface
│   │   ├── shell.py         # exécution de commandes (sans shell, messages en anglais)
│   │   ├── git_ops.py       # dépôt, commit, remote, push, fusion, conflits
│   │   ├── ssh.py           # clés SSH, test de connexion GitHub
│   │   ├── github.py        # adresses de dépôts, CLI gh, ouverture de liens
│   │   ├── diagnostics.py   # reconnaissance et explication des erreurs
│   │   ├── safety.py        # fichiers sensibles, .gitignore
│   │   └── storage.py       # réglages et projets récents (JSON)
│   ├── interface/           # display.py (Rich), prompts.py, menus.py
│   ├── workflows/           # setup.py, common.py, publish.py, sync.py
│   └── utils/               # validators.py, paths.py
├── tests/
├── packaging/               # build_pyz.py, build_binary.py (PyInstaller, optionnel)
└── .github/workflows/       # ci.yml, release.yml
```

## Tests

```bash
python -m unittest discover -v      # depuis un simple dossier, sans installation
```

Les tests utilisent un vrai Git avec des dépôts locaux temporaires (rejet de push, fusion, conflits). Les appels à SSH et `gh` sont simulés.

## Publier une version (mainteneur)

1. Changer `__version__` dans `src/git_ritual/__init__.py`, committer.
2. `git tag v1.0.1 && git push origin v1.0.1` (le tag doit valoir `v` + la version).
3. Le workflow *Release* teste, construit, publie sur PyPI (Trusted Publishing, à configurer une fois sur pypi.org) et crée la release GitHub avec le `.pyz`, le wheelhouse, les binaires et `SHA256SUMS`.

## Données

Réglages dans `~/.git-ritual/settings.json` (modifiable via `GIT_RITUAL_HOME`).

## Licence

MIT — voir [LICENSE](LICENSE).
