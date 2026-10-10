import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_alertas.db")
os.environ["ANTHROPIC_API_KEY"] = ""

import pandas as pd  # noqa: E402

FILAS_BASE = [
    {"id": 1, "n": 1, "mes": "Enero", "fecha_alerta": "2026-01-02", "local": "SAN MARINO", "area": "Ventas",
     "pregunta": "¿El tiempo de entrega fue acorde?", "comentario": "Se demoraron dos semanas", "cliente": "Cliente A"},
    {"id": 2, "n": 2, "mes": "Enero", "fecha_alerta": "2026-01-03", "local": "POLICENTRO", "area": "Ventas",
     "pregunta": "Atención", "comentario": "Trato malo del asesor", "cliente": "Cliente B"},
    {"id": 3, "n": 3, "mes": "Febrero", "fecha_alerta": "2026-02-10", "local": "CCI 2", "area": "Optometría",
     "pregunta": "Lunas", "comentario": "Medidas mal hechas", "cliente": "Cliente C"},
]


@pytest.fixture()
def alertas_env(tmp_path, monkeypatch):
    """Aísla CSV/Parquet/BD de alertas en un directorio temporal."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import centro_operaciones.services.datastore as ds
    import database
    import services.alertas_db_service as dbs

    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    from models import alerta, catalogo, cuaderno  # noqa: F401

    database.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(database, "SessionLocal", Session)
    monkeypatch.setattr(dbs, "SessionLocal", Session)
    try:
        import services.actividad_service as act

        monkeypatch.setattr(act, "SessionLocal", Session, raising=False)
    except Exception:
        pass

    monkeypatch.setattr(ds, "ALERTAS_CSV", tmp_path / "alertas.csv")
    monkeypatch.setattr(ds, "ALERTAS_PARQUET", tmp_path / "alertas.parquet")
    monkeypatch.setattr(ds, "ALERTAS_EXCEL", tmp_path / "no_existe.xlsx")
    if hasattr(ds, "invalidar_cache"):
        ds.invalidar_cache()
    ds.guardar_alertas(pd.DataFrame(FILAS_BASE))
    yield {"ds": ds, "Session": Session, "tmp": tmp_path}
    if hasattr(ds, "invalidar_cache"):
        ds.invalidar_cache()


@pytest.fixture()
def client(alertas_env):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from routers.alertas_router import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)
