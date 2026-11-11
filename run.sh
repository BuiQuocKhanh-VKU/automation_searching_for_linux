#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR=".venv"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[ERROR] Không tìm thấy python3."
  exit 1
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[SETUP] Tạo môi trường ảo tại $VENV_DIR ..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -c 'import flet, selenium' >/dev/null 2>&1; then
  echo "[SETUP] Cài dependencies ..."
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/python" -m pip install -r requirements.txt
fi

exec "$VENV_DIR/bin/python" main.py
