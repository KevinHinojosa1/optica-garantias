import io
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from config import settings
from models.cliente import Cliente
from services.descuento_service import DescuentoService
from services.duplicate_service import DuplicateService
from services.tiendas_service import TiendasService

REQUIRED_COLUMNS = [
    "nombre",
    "cedula",
    "telefono",
    "tienda",
    "producto",
    "tipo_producto",
    "fecha_factura",
    "numero_factura",
    "fecha_entrega",
    "tiene_ola_plus",
]


class ImportService:
    @staticmethod
    def parse_file(content: bytes, filename: str) -> pd.DataFrame:
        lower = filename.lower()
        if lower.endswith(".csv"):
            for encoding in ("utf-8", "latin-1", "cp1252"):
                try:
                    return pd.read_csv(io.BytesIO(content), encoding=encoding)
                except UnicodeDecodeError:
                    continue
            raise ValueError("No se pudo decodificar el archivo CSV. Use UTF-8 o Latin-1.")
        if lower.endswith((".xlsx", ".xls")):
            return pd.read_excel(io.BytesIO(content))
        raise ValueError("Formato no soportado. Use CSV o Excel (.xlsx).")

    @staticmethod
    def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        return df

    @staticmethod
    def parse_date(value) -> datetime.date | None:
        if pd.isna(value) or value == "" or value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        text = str(value).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}", text):
            parsed = pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")
        else:
            parsed = pd.to_datetime(text, dayfirst=True, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.date()

    @staticmethod
    def parse_bool(value) -> bool:
        if pd.isna(value):
            return False
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        return text in ("true", "1", "si", "sí", "yes", "y", "verdadero")

    @classmethod
    def import_to_db(cls, db: Session, content: bytes, filename: str) -> dict:
        df = cls.parse_file(content, filename)
        df = cls.normalize_columns(df)

        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Columnas faltantes: {', '.join(missing)}")

        total = len(df)
        insertados = 0
        errores = 0
        duplicados = 0
        detalle: list[str] = []
        detalle_duplicados: list[str] = []

        facturas_archivo: set[str] = set()

        for idx, row in df.iterrows():
            fila = int(idx) + 2
            try:
                numero_factura = str(row["numero_factura"]).strip()
                cedula = str(row["cedula"]).strip()
                tienda = str(row["tienda"]).strip()

                if not numero_factura:
                    raise ValueError("numero_factura vacío")

                clave = numero_factura.upper()

                if clave in facturas_archivo:
                    duplicados += 1
                    detalle_duplicados.append(
                        f"Fila {fila}: Factura {numero_factura} duplicada dentro del mismo archivo"
                    )
                    continue

                if DuplicateService.existe_factura(db, numero_factura):
                    duplicados += 1
                    detalle_duplicados.append(
                        f"Fila {fila}: ⛔ BLOQUEADO — Factura {numero_factura} ya registrada (cédula {cedula})"
                    )
                    continue

                if not TiendasService.validar_tienda(tienda):
                    raise ValueError(
                        f"Tienda '{tienda}' no reconocida. Use un nombre del catálogo oficial."
                    )

                fecha_factura = cls.parse_date(row["fecha_factura"])
                if not fecha_factura:
                    raise ValueError("fecha_factura inválida o vacía")

                fecha_entrega = cls.parse_date(row.get("fecha_entrega"))

                codigo_raw = row.get("codigo_descuento")
                pct_raw = row.get("porcentaje_descuento")
                codigo_desc = None
                pct_desc = None
                if codigo_raw is not None and str(codigo_raw).strip() not in ("", "nan"):
                    codigo_desc = int(float(codigo_raw))
                if pct_raw is not None and str(pct_raw).strip() not in ("", "nan"):
                    pct_desc = int(float(pct_raw))
                codigo_desc, pct_desc = DescuentoService.validar(codigo_desc, pct_desc)

                cliente = Cliente(
                    nombre=str(row["nombre"]).strip(),
                    cedula=cedula,
                    telefono=str(row["telefono"]).strip().replace(" ", ""),
                    tienda=tienda,
                    producto=str(row["producto"]).strip(),
                    tipo_producto=str(row["tipo_producto"]).strip(),
                    fecha_factura=fecha_factura,
                    numero_factura=numero_factura,
                    fecha_entrega=fecha_entrega,
                    tiene_ola_plus=cls.parse_bool(row["tiene_ola_plus"]),
                    codigo_descuento=codigo_desc,
                    porcentaje_descuento=pct_desc,
                )

                if not cliente.nombre or not cliente.cedula or not cliente.telefono:
                    raise ValueError("nombre, cedula o telefono vacíos")

                db.add(cliente)
                facturas_archivo.add(clave)
                insertados += 1
            except Exception as exc:
                errores += 1
                detalle.append(f"Fila {fila}: {exc}")

        if insertados > 0:
            db.commit()
        else:
            db.rollback()

        return {
            "total_filas": total,
            "registros_insertados": insertados,
            "errores": errores,
            "duplicados": duplicados,
            "detalle_errores": detalle[:50],
            "detalle_duplicados": detalle_duplicados[:50],
        }

    @classmethod
    def ruta_archivo_base(cls) -> Path:
        return Path(settings.base_datos_dir) / settings.base_datos_archivo

    @classmethod
    def limpiar_todos(cls, db: Session) -> int:
        total = db.query(Cliente).count()
        db.query(Cliente).delete()
        db.commit()
        return total

    @classmethod
    def importar_desde_carpeta(cls, db: Session, reemplazar: bool = True) -> dict:
        ruta = cls.ruta_archivo_base()
        if not ruta.exists():
            raise FileNotFoundError(
                f"No se encontró el archivo en {ruta}. Coloque un Excel con el nombre '{settings.base_datos_archivo}'."
            )

        eliminados = 0
        if reemplazar:
            eliminados = cls.limpiar_todos(db)

        with open(ruta, "rb") as f:
            resultado = cls.import_to_db(db, f.read(), ruta.name)

        resultado["archivo"] = str(ruta)
        resultado["registros_eliminados"] = eliminados
        resultado["modo"] = "reemplazar" if reemplazar else "agregar"
        return resultado