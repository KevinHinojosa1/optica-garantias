#!/usr/bin/env bash
set -euo pipefail

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY=python
fi

echo "==> Actualizando pip ($PY)..."
"$PY" -m pip install --upgrade pip setuptools wheel

echo "==> Instalando dependencias (sin caché, wheels preferidos)..."
"$PY" -m pip install --no-cache-dir --prefer-binary -r requirements.txt

echo "==> Verificando importación de la aplicación..."
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
"$PY" scripts/verify_build.py

echo "==> Build completado."