from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings

_connect_args = {}
if settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _agregar_columna_si_falta(conn, tabla: str, columnas_existentes: set, nombre: str, ddl: str):
    if nombre not in columnas_existentes:
        conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {ddl}"))


def migrate_db():
    inspector = inspect(engine)
    tablas = set(inspector.get_table_names())

    with engine.begin() as conn:
        if "clientes" in tablas:
            cols = {c["name"] for c in inspector.get_columns("clientes")}
            _agregar_columna_si_falta(conn, "clientes", cols, "tienda", "tienda VARCHAR(150) DEFAULT 'Sin asignar'")
            _agregar_columna_si_falta(conn, "clientes", cols, "codigo_descuento", "codigo_descuento INTEGER")
            _agregar_columna_si_falta(conn, "clientes", cols, "porcentaje_descuento", "porcentaje_descuento INTEGER")

        if "historial_consultas" in tablas:
            cols = {c["name"] for c in inspector.get_columns("historial_consultas")}
            _agregar_columna_si_falta(conn, "historial_consultas", cols, "codigo_descuento", "codigo_descuento INTEGER")
            _agregar_columna_si_falta(conn, "historial_consultas", cols, "porcentaje_descuento", "porcentaje_descuento INTEGER")
            _agregar_columna_si_falta(conn, "historial_consultas", cols, "imagen_path", "imagen_path VARCHAR(300)")

        if "ivr_verificaciones" in tablas:
            cols = {c["name"] for c in inspector.get_columns("ivr_verificaciones")}
            _agregar_columna_si_falta(
                conn, "ivr_verificaciones", cols, "comentario_auditoria", "comentario_auditoria TEXT"
            )


def init_db():
    from models import (  # noqa: F401
        alerta,
        catalogo,
        cliente,
        conocimiento,
        cuaderno,
        historial,
        ivr,
        reprogramacion,
    )

    Base.metadata.create_all(bind=engine)
    migrate_db()

    consultas_dir = settings.base_dir / settings.consultas_imagenes_dir
    consultas_dir.mkdir(parents=True, exist_ok=True)
    (settings.base_dir / "data" / "conocimiento").mkdir(parents=True, exist_ok=True)
    (settings.base_dir / "data" / "cuaderno").mkdir(parents=True, exist_ok=True)

    # Importar JSON antiguo de reprogramaciones si existe
    try:
        from services.reprogramacion_log_service import ReprogramacionLogService

        n = ReprogramacionLogService.migrar_json_si_existe()
        if n:
            print(f"Reprogramaciones: migrados {n} registros JSON → BD", flush=True)
    except Exception as exc:
        print(f"Migración reprogramaciones (no crítica): {exc}", flush=True)

    # Scripts CX y plantillas bot → BD
    try:
        from services.catalogo_service import CatalogoService
        from services.respuesta_ia_service import RespuestaIAService

        if CatalogoService.seed_scripts():
            print("Scripts CX importados a BD", flush=True)
        RespuestaIAService._migrar_plantillas_json_a_bd()
    except Exception as exc:
        print(f"Seed catálogos (no crítico): {exc}", flush=True)