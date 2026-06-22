import io
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from config import settings
from models.historial import HistorialConsulta
from schemas.historial import HistorialCreate


class HistorialService:
    @staticmethod
    def registrar(db: Session, data: HistorialCreate) -> HistorialConsulta:
        registro = HistorialConsulta(**data.model_dump())
        db.add(registro)
        db.commit()
        db.refresh(registro)
        return registro

    @staticmethod
    def actualizar_imagen(db: Session, registro_id: int, imagen_path: str) -> HistorialConsulta | None:
        registro = db.query(HistorialConsulta).filter(HistorialConsulta.id == registro_id).first()
        if not registro:
            return None
        registro.imagen_path = imagen_path
        db.commit()
        db.refresh(registro)
        return registro

    @staticmethod
    def obtener(db: Session, registro_id: int) -> HistorialConsulta | None:
        return db.query(HistorialConsulta).filter(HistorialConsulta.id == registro_id).first()

    @staticmethod
    def actualizar_mensaje(db: Session, registro_id: int, mensaje: str) -> HistorialConsulta | None:
        registro = db.query(HistorialConsulta).filter(HistorialConsulta.id == registro_id).first()
        if not registro:
            return None
        registro.mensaje_enviado = mensaje
        db.commit()
        db.refresh(registro)
        return registro

    @staticmethod
    def ultimo_por_cliente(db: Session, cliente_id: int) -> HistorialConsulta | None:
        return (
            db.query(HistorialConsulta)
            .filter(HistorialConsulta.cliente_id == cliente_id)
            .order_by(HistorialConsulta.created_at.desc())
            .first()
        )

    @staticmethod
    def _borrar_imagen(registro: HistorialConsulta) -> None:
        if not registro.imagen_path:
            return
        ruta = Path(registro.imagen_path)
        if not ruta.is_absolute():
            ruta = settings.base_dir / ruta
        if ruta.exists():
            ruta.unlink(missing_ok=True)

    @staticmethod
    def eliminar(db: Session, registro_id: int) -> bool:
        registro = db.query(HistorialConsulta).filter(HistorialConsulta.id == registro_id).first()
        if not registro:
            return False
        HistorialService._borrar_imagen(registro)
        db.delete(registro)
        db.commit()
        return True

    @staticmethod
    def eliminar_todos(db: Session) -> int:
        total = db.query(HistorialConsulta).count()
        db.query(HistorialConsulta).delete()
        db.commit()
        return total

    @staticmethod
    def listar(db: Session, limit: int = 100) -> list[HistorialConsulta]:
        return (
            db.query(HistorialConsulta)
            .order_by(HistorialConsulta.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def exportar_excel(db: Session) -> bytes:
        registros = (
            db.query(HistorialConsulta)
            .order_by(HistorialConsulta.created_at.desc())
            .all()
        )
        rows = [
            {
                "Fecha": r.created_at.strftime("%Y-%m-%d %H:%M"),
                "Cliente": r.cliente_nombre,
                "Veredicto": r.veredicto,
                "Motivo": r.motivo or "",
                "Fundamento": r.fundamento or "",
                "Confianza %": r.confianza or "",
                "Asesor": r.asesor,
                "Código descuento %": r.codigo_descuento or "",
                "Descuento aplicado %": r.porcentaje_descuento or "",
                "Mensaje": r.mensaje_enviado or "",
            }
            for r in registros
        ]
        df = pd.DataFrame(rows)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Historial")
        buffer.seek(0)
        return buffer.getvalue()