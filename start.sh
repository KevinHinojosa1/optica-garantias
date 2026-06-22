#!/bin/sh
set -e

PORT="${PORT:-8000}"

python -c "
from pathlib import Path
from database import SessionLocal, init_db
from models.cliente import Cliente
from services.import_service import ImportService

init_db()
ruta = ImportService.ruta_archivo_base()
if not ruta.exists():
    script = Path('scripts/generar_base_datos.py')
    if script.exists():
        import subprocess
        subprocess.run(['python', str(script)], check=False)
db = SessionLocal()
try:
    if db.query(Cliente).count() == 0 and ImportService.ruta_archivo_base().exists():
        ImportService.importar_desde_carpeta(db, reemplazar=True)
        print('Base inicial cargada desde Excel de prueba')
finally:
    db.close()
"

exec uvicorn main:app --host 0.0.0.0 --port "$PORT"