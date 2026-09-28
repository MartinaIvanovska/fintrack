#!/usr/bin/env bash
# Create/update the backend virtual environment at backend/.venv with the
# Python version pinned in backend/.python-version, install the app + test
# dependencies, and download the Playwright browser used by the e2e tests.
#
# Usage:  ./scripts/setup-venv.sh [--no-browsers]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$REPO_ROOT/backend"
VENV="$BACKEND/.venv"
PY_VERSION="$(tr -d '[:space:]' < "$BACKEND/.python-version")"

INSTALL_BROWSERS=1
for arg in "$@"; do
  case "$arg" in
    --no-browsers) INSTALL_BROWSERS=0 ;;
    -h|--help) sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

log() { printf '\n==> %s\n' "$*"; }

find_uv() {
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return
  fi
  local tools_dir="${XDG_CACHE_HOME:-$HOME/.cache}/fintrack/uv-bootstrap"
  if [ ! -x "$tools_dir/bin/uv" ]; then
    log "uv not found; bootstrapping it into $tools_dir" >&2
    python3 -m venv "$tools_dir" >&2
    "$tools_dir/bin/pip" install --quiet --disable-pip-version-check uv >&2
  fi
  echo "$tools_dir/bin/uv"
}

if command -v uv >/dev/null 2>&1 || ! command -v "python$PY_VERSION" >/dev/null 2>&1; then
  UV="$(find_uv)"
  log "Creating $VENV with Python $PY_VERSION (uv: $UV)"
  "$UV" venv --allow-existing --python "$PY_VERSION" "$VENV"
  log "Installing backend/requirements-dev.txt"
  "$UV" pip install --python "$VENV/bin/python" -r "$BACKEND/requirements-dev.txt"
else
  log "Creating $VENV with python$PY_VERSION"
  "python$PY_VERSION" -m venv "$VENV"
  log "Installing backend/requirements-dev.txt"
  "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check --upgrade pip
  "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r "$BACKEND/requirements-dev.txt"
fi

if [ "$INSTALL_BROWSERS" -eq 1 ]; then
  log "Installing Playwright Chromium (for tests/e2e)"
  "$VENV/bin/playwright" install chromium
fi

log "Done: $("$VENV/bin/python" --version) in backend/.venv"
cat <<EOF

Next steps:
  source backend/.venv/bin/activate
  cd backend
  pytest tests/unit          # no services needed
  pytest                     # unit + integration (needs: docker compose up -d mongo)
EOF
