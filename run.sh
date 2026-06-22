#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
else
  source venv/bin/activate
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Creado .env — usando SQLite por defecto"
fi

# PostgreSQL opcional (requiere Docker)
if command -v docker &>/dev/null; then
  docker compose up -d 2>/dev/null || true
fi

# Generar Excel de prueba si no existe
if [ ! -f "data/base_datos/pacientes.xlsx" ]; then
  python scripts/generar_base_datos.py
fi

# Inicializar BD e importar si está vacía
python -c "
from database import SessionLocal, init_db
from models.cliente import Cliente
from services.import_service import ImportService
init_db()
db = SessionLocal()
if db.query(Cliente).count() == 0 and ImportService.ruta_archivo_base().exists():
    ImportService.importar_desde_carpeta(db, reemplazar=True)
    print('Base de datos cargada desde data/base_datos/pacientes.xlsx')
db.close()
"

echo ""
echo "========================================="
echo "  Óptica Los Andes — Sistema conectado"
echo "  http://localhost:8000"
echo "  Importar:  http://localhost:8000/importar"
echo "  Atención:  http://localhost:8000/clientes"
echo "========================================="
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload