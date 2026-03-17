#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
DB_PATH="${DB_PATH:-$ROOT_DIR/data/ecg_analysis.db}"

python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -e "$ROOT_DIR"

mkdir -p "$ROOT_DIR/data/raw" "$ROOT_DIR/data/processed" "$ROOT_DIR/reports"
PYTHONPATH="$ROOT_DIR/src" python "$ROOT_DIR/scripts/init_db.py" --db-path "$DB_PATH"

echo "Install/setup complete"
echo "- virtualenv: $VENV_DIR"
echo "- database:   $DB_PATH"
