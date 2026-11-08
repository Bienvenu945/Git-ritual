#!/usr/bin/env bash
# Git-Ritual installer — made for Termux, also fine on Linux and macOS.
#
#   bash install.sh                 install from this folder (zip / USB stick / checkout)
#   bash install.sh --pypi          install the published release from PyPI
#   bash install.sh --git URL       install from a Git repository
#   bash install.sh --with-gh       also install the GitHub CLI (Termux only)
#   bash install.sh --alias         create a shell alias instead of a symlink
#   bash install.sh --no-pkg        never touch the system package manager
#   bash install.sh --uninstall     remove Git-Ritual (settings and SSH keys are kept)
#
# Re-running the script upgrades an existing installation.
# Offline / USB wheelhouse:
#   GIT_RITUAL_PIP_ARGS="--no-index --find-links /path/to/wheelhouse" bash install.sh --pypi
# Overrides: GIT_RITUAL_VENV (virtualenv path), GIT_RITUAL_BIN (where `ritual` is linked).
set -euo pipefail

APP="git-ritual"
CMD="ritual"
MARK="# >>> git-ritual >>>"
MARK_END="# <<< git-ritual <<<"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MODE="auto"; GIT_URL=""; WITH_GH=0; USE_ALIAS=0; USE_PKG=1; UNINSTALL=0

if [ -t 1 ]; then B=$'\033[1m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; N=$'\033[0m'; else B=""; G=""; Y=""; R=""; N=""; fi
info() { printf '%s==>%s %s\n' "$B" "$N" "$*"; }
ok()   { printf '%s ok%s %s\n' "$G" "$N" "$*"; }
warn() { printf '%s !!%s %s\n' "$Y" "$N" "$*" >&2; }
die()  { printf '%s xx%s %s\n' "$R" "$N" "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --pypi) MODE="pypi" ;;
    --git) MODE="git"; shift; GIT_URL="${1:-}"; [ -n "$GIT_URL" ] || die "--git demande une adresse." ;;
    --with-gh) WITH_GH=1 ;;
    --alias) USE_ALIAS=1 ;;
    --no-pkg) USE_PKG=0 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help) sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "Option inconnue : $1 (voir --help)" ;;
  esac
  shift
done

# ---------------------------------------------------------------- environment
is_termux() { [ -n "${TERMUX_VERSION:-}" ] || [ -d /data/data/com.termux/files/usr ]; }

if is_termux; then
  PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
  BIN_DIR="${GIT_RITUAL_BIN:-$PREFIX/bin}"   # always on PATH in Termux
else
  BIN_DIR="${GIT_RITUAL_BIN:-$HOME/.local/bin}"
fi
VENV="${GIT_RITUAL_VENV:-${XDG_DATA_HOME:-$HOME/.local/share}/$APP/venv}"
LINK="$BIN_DIR/$CMD"
ALIAS_FILES=("$HOME/.bashrc" "$HOME/.zshrc")

# ---------------------------------------------------------------- uninstall
remove_alias_blocks() {
  local f
  for f in "${ALIAS_FILES[@]}"; do
    [ -f "$f" ] && grep -qF "$MARK" "$f" && sed -i.bak "/$MARK/,/$MARK_END/d" "$f" && rm -f "$f.bak"
  done
  return 0
}

if [ "$UNINSTALL" -eq 1 ]; then
  info "Désinstallation de Git-Ritual"
  if [ -L "$LINK" ] && [ "$(readlink "$LINK")" = "$VENV/bin/$CMD" ]; then rm -f "$LINK"; ok "lien $LINK supprimé"; fi
  [ -d "$VENV" ] && rm -rf "$VENV" && ok "environnement $VENV supprimé"
  remove_alias_blocks
  ok "Terminé. Vos réglages (~/.git-ritual) et vos clés SSH (~/.ssh) n'ont pas été touchés."
  exit 0
fi

# ---------------------------------------------------------------- system packages
if is_termux && [ "$USE_PKG" -eq 1 ]; then
  info "Paquets Termux : python, git, openssh"
  pkg install -y python git openssh || die "pkg a échoué. Essayez « termux-change-repo » puis relancez."
  python -m pip --version >/dev/null 2>&1 || pkg install -y python-pip
  if [ "$WITH_GH" -eq 1 ]; then pkg install -y gh || warn "Installation de gh impossible (facultatif)."; fi
elif ! is_termux && [ "$WITH_GH" -eq 1 ]; then
  warn "--with-gh ne concerne que Termux : installez gh avec votre gestionnaire de paquets."
fi

PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
    PY="$candidate"; break
  fi
done
[ -n "$PY" ] || die "Python 3.9 ou plus récent est introuvable."
command -v git >/dev/null 2>&1 || warn "git est introuvable : Git-Ritual en a besoin pour fonctionner."
command -v ssh-keygen >/dev/null 2>&1 || warn "openssh est introuvable : l'assistant de clé SSH ne marchera pas."

# ---------------------------------------------------------------- what to install
case "$MODE" in
  auto) if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then MODE="local"; else MODE="pypi"; fi ;;
esac
case "$MODE" in
  local) SPEC="$SCRIPT_DIR" ;;
  pypi)  SPEC="$APP" ;;
  git)   SPEC="git+$GIT_URL" ;;
esac

EXTRA=()
if [ -n "${GIT_RITUAL_PIP_ARGS:-}" ]; then read -r -a EXTRA <<<"$GIT_RITUAL_PIP_ARGS"; fi

# ---------------------------------------------------------------- virtualenv + install
# A private virtualenv works around PEP 668 ("externally-managed-environment") and never
# touches the system Python. Dependencies are pure Python: nothing is compiled on the phone.
info "Installation ($MODE) dans $VENV"
if [ ! -x "$VENV/bin/python" ]; then
  mkdir -p "$(dirname "$VENV")"
  if ! "$PY" -m venv "$VENV" 2>/dev/null; then
    rm -rf "$VENV"
    if command -v pipx >/dev/null 2>&1; then
      warn "venv indisponible (sous Debian/Ubuntu : paquet python3-venv) — repli sur pipx."
      pipx install --force ${EXTRA[@]+"${EXTRA[@]}"} "$SPEC"
      ok "Installé avec pipx. Lancez : $CMD"
      exit 0
    fi
    die "Impossible de créer l'environnement virtuel (Debian/Ubuntu : sudo apt install python3-venv)."
  fi
fi
"$VENV/bin/python" -m pip --version >/dev/null 2>&1 || "$VENV/bin/python" -m ensurepip --upgrade
"$VENV/bin/python" -m pip install --upgrade ${EXTRA[@]+"${EXTRA[@]}"} "$SPEC"

[ -x "$VENV/bin/$CMD" ] || die "Installation incomplète : $VENV/bin/$CMD est absent."

# ---------------------------------------------------------------- command on PATH
if [ "$USE_ALIAS" -eq 1 ]; then
  remove_alias_blocks
  for f in "${ALIAS_FILES[@]}"; do
    { [ -f "$f" ] || [ "$f" = "$HOME/.bashrc" ]; } || continue
    printf '%s\nalias %s=%q\n%s\n' "$MARK" "$CMD" "$VENV/bin/$CMD" "$MARK_END" >>"$f"
  done
  ok "Alias ajouté. Ouvrez un nouveau terminal (ou : source ~/.bashrc), puis tapez : $CMD"
else
  mkdir -p "$BIN_DIR"
  if [ -e "$LINK" ] && [ ! -L "$LINK" ]; then die "$LINK existe et n'est pas un lien : je ne l'écrase pas."; fi
  ln -sf "$VENV/bin/$CMD" "$LINK"
  ok "Commande installée : $LINK"
  case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) warn "$BIN_DIR n'est pas dans votre PATH. Ajoutez à ~/.bashrc : export PATH=\"$BIN_DIR:\$PATH\"   (ou relancez avec --alias)" ;;
  esac
fi

"$VENV/bin/$CMD" --version
ok "Prêt. Tapez « $CMD » puis choisissez 5 (assistant) au premier lancement."
