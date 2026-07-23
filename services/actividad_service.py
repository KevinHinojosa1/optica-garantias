"""Log de actividad / cambios en el sistema."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from database import SessionLocal
from models.cuaderno import ActividadLog


class ActividadService:
    @classmethod
    def registrar(
        cls,
        *,
        modulo: str,
        accion: str,
        detalle: str = "",
        usuario: str = "",
        entidad: str = "",
        entidad_id: str = "",
        db: Session | None = None,
    ) -> None:
        own = False
        if db is None:
            db = SessionLocal()
            own = True
        try:
            db.add(
                ActividadLog(
                    modulo=modulo,
                    accion=accion,
                    detalle=(detalle or "")[:4000],
                    usuario=usuario or "",
                    entidad=entidad or "",
                    entidad_id=str(entidad_id or ""),
                    created_at=datetime.utcnow(),
                )
            )
            db.commit()
        except Exception:
            db.rollback()
        finally:
            if own:
                db.close()

    @classmethod
    def listar(cls, *, limit: int = 50, modulo: str = "", db: Session | None = None) -> list[dict]:
        own = False
        if db is None:
            db = SessionLocal()
            own = True
        try:
            q = db.query(ActividadLog).order_by(ActividadLog.id.desc())
            if modulo:
                q = q.filter(ActividadLog.modulo == modulo)
            rows = q.limit(max(1, min(limit, 200))).all()
            return [
                {
                    "id": r.id,
                    "modulo": r.modulo,
                    "accion": r.accion,
                    "detalle": r.detalle,
                    "usuario": r.usuario,
                    "entidad": r.entidad,
                    "entidad_id": r.entidad_id,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                }
                for r in rows
            ]
        finally:
            if own:
                db.close()
