"""Lectura/escritura de catálogos JSON en BD con seed desde archivos."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models.catalogo import CatalogoJson


class CatalogoService:
    @classmethod
    def _session(cls, db: Session | None) -> tuple[Session, bool]:
        if db is not None:
            return db, False
        return SessionLocal(), True

    @classmethod
    def obtener(cls, clave: str, db: Session | None = None) -> dict | None:
        session, own = cls._session(db)
        try:
            row = session.query(CatalogoJson).filter(CatalogoJson.clave == clave).first()
            if not row:
                return None
            try:
                return json.loads(row.contenido or "{}")
            except json.JSONDecodeError:
                return None
        finally:
            if own:
                session.close()

    @classmethod
    def guardar(
        cls,
        clave: str,
        data: dict,
        *,
        version: str = "1",
        db: Session | None = None,
    ) -> None:
        session, own = cls._session(db)
        try:
            row = session.query(CatalogoJson).filter(CatalogoJson.clave == clave).first()
            payload = json.dumps(data, ensure_ascii=False)
            if row:
                row.contenido = payload
                row.version = version
                row.updated_at = datetime.utcnow()
            else:
                session.add(
                    CatalogoJson(
                        clave=clave,
                        version=version,
                        contenido=payload,
                        updated_at=datetime.utcnow(),
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if own:
                session.close()

    @classmethod
    def seed_desde_archivo(
        cls,
        clave: str,
        path: Path,
        *,
        db: Session | None = None,
        forzar: bool = False,
    ) -> bool:
        """Si no hay fila en BD (o forzar), importa el JSON del disco."""
        if not path.exists():
            return False
        session, own = cls._session(db)
        try:
            existe = session.query(CatalogoJson).filter(CatalogoJson.clave == clave).first()
            if existe and not forzar:
                return False
            data = json.loads(path.read_text(encoding="utf-8"))
            version = str(data.get("version") or "1")
            payload = json.dumps(data, ensure_ascii=False)
            if existe:
                existe.contenido = payload
                existe.version = version
                existe.updated_at = datetime.utcnow()
            else:
                session.add(
                    CatalogoJson(
                        clave=clave,
                        version=version,
                        contenido=payload,
                        updated_at=datetime.utcnow(),
                    )
                )
            session.commit()
            return True
        except Exception as exc:
            session.rollback()
            print(f"Seed catalogo {clave}: {exc}", flush=True)
            return False
        finally:
            if own:
                session.close()

    @classmethod
    def seed_scripts(cls, db: Session | None = None) -> bool:
        path = settings.base_dir / "data" / "scripts_atencion.json"
        return cls.seed_desde_archivo("scripts_atencion", path, db=db)

    @classmethod
    def seed_plantillas_archivo(cls, db: Session | None = None) -> bool:
        path = settings.base_dir / "data" / "plantillas_respuesta_ia.json"
        return cls.seed_desde_archivo("plantillas_respuesta_ia_legacy", path, db=db)
