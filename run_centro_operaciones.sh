#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ -d "venv" ]; then
  source venv/bin/activate
fi
pip install -q -r centro_operaciones/requirements.txt
streamlit run centro_operaciones/app.py --server.port 8501