"""Verificación post-build para Render — falla el deploy si la app no importa."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from main import app  # noqa: F401
    print("verify_build: OK")
except Exception as exc:
    print(f"verify_build: FAILED — {exc}", file=sys.stderr)
    sys.exit(1)