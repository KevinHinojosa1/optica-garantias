"""Registro de reprogramaciones en base de datos (SQLite / PostgreSQL)."""

from __future__ import annotations

import json
import threading
from datetime import date, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models.reprogramacion import ReprogramacionEnvio

_lock = threading.Lock()
LOG_PATH = settings.base_dir / "data" / "reprogramaciones_envios.json"
_migrado_json = False


class ReprogramacionLogService:
    @classmethod
    def _hoy(cls) -> date:
        return date.today()

    @classmethod
    def _parse_fecha(cls, dia: str | date | None) -> date:
        if isinstance(dia, date):
            return dia
        if not dia:
            return cls._hoy()
        try:
            return datetime.strptime(str(dia)[:10], "%Y-%m-%d").date()
        except ValueError:
            return cls._hoy()

    @classmethod
    def _clave_local(cls, local: str) -> str:
        return (local or "Sin tienda").strip() or "Sin tienda"

    @classmethod
    def _session(cls, db: Session | None) -> tuple[Session, bool]:
        if db is not None:
            return db, False
        return SessionLocal(), True

    @classmethod
    def migrar_json_si_existe(cls, db: Session | None = None) -> int:
        """Importa una vez el JSON antiguo a la BD (si aún hay archivo)."""
        global _migrado_json
        if _migrado_json or not LOG_PATH.exists():
            return 0

        with _lock:
            if _migrado_json:
                return 0
            try:
                data = json.loads(LOG_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                _migrado_json = True
                return 0

            session, own = cls._session(db)
            insertados = 0
            try:
                if session.query(ReprogramacionEnvio).count() > 0:
                    # Ya hay datos en BD: solo renombrar JSON y no reimportar
                    bak = LOG_PATH.with_suffix(".json.bak")
                    try:
                        LOG_PATH.rename(bak)
                    except OSError:
                        pass
                    _migrado_json = True
                    return 0

                for dia_str, locales in (data or {}).items():
                    fecha = cls._parse_fecha(dia_str)
                    if not isinstance(locales, dict):
                        continue
                    for local, bloque in locales.items():
                        for e in (bloque or {}).get("enviados") or []:
                            session.add(
                                ReprogramacionEnvio(
                                    fecha=fecha,
                                    local=cls._clave_local(local),
                                    nombre=str(e.get("nombre") or ""),
                                    producto=str(e.get("producto") or ""),
                                    factura=str(e.get("factura") or ""),
                                    telefono=str(e.get("telefono") or ""),
                                    canal=str(e.get("canal") or "cliente"),
                                    estado=str(e.get("estado") or "Mensaje enviado"),
                                    asesor="",
                                    mensaje=None,
                                    email_tienda="",
                                    motivo="",
                                    fecha_reprogramada="",
                                    fecha_anterior="",
                                    lote_id="migracion-json",
                                )
                            )
                            insertados += 1
                session.commit()
                bak = LOG_PATH.with_suffix(".json.bak")
                try:
                    LOG_PATH.rename(bak)
                except OSError:
                    pass
                _migrado_json = True
                return insertados
            except Exception:
                session.rollback()
                raise
            finally:
                if own:
                    session.close()

    @classmethod
    def registrar_envio(
        cls,
        *,
        local: str,
        nombre: str,
        producto: str = "",
        factura: str = "",
        telefono: str = "",
        canal: str = "cliente",
        estado: str = "Mensaje enviado",
        asesor: str = "",
        mensaje: str = "",
        email_tienda: str = "",
        motivo: str = "",
        fecha_reprogramada: str = "",
        fecha_anterior: str = "",
        lote_id: str = "",
        db: Session | None = None,
    ) -> dict[str, Any]:
        """Upsert por día + local + canal + factura + nombre. Guarda en BD."""
        cls.migrar_json_si_existe(db)
        fecha = cls._hoy()
        clave = cls._clave_local(local)
        session, own = cls._session(db)

        try:
            q = (
                session.query(ReprogramacionEnvio)
                .filter(
                    ReprogramacionEnvio.fecha == fecha,
                    ReprogramacionEnvio.local == clave,
                    ReprogramacionEnvio.canal == (canal or "cliente"),
                    func.lower(ReprogramacionEnvio.factura) == (factura or "").strip().lower(),
                    func.lower(ReprogramacionEnvio.nombre) == (nombre or "").strip().lower(),
                )
            )
            row = q.first()
            now = datetime.utcnow()
            if row:
                row.producto = producto or row.producto
                row.telefono = telefono or row.telefono
                row.estado = estado or row.estado
                if asesor:
                    row.asesor = asesor
                if mensaje:
                    row.mensaje = mensaje
                if email_tienda:
                    row.email_tienda = email_tienda
                if motivo:
                    row.motivo = motivo
                if fecha_reprogramada:
                    row.fecha_reprogramada = fecha_reprogramada
                if fecha_anterior:
                    row.fecha_anterior = fecha_anterior
                if lote_id:
                    row.lote_id = lote_id
                row.updated_at = now
            else:
                session.add(
                    ReprogramacionEnvio(
                        fecha=fecha,
                        local=clave,
                        nombre=nombre or "",
                        producto=producto or "",
                        factura=factura or "",
                        telefono=telefono or "",
                        canal=canal or "cliente",
                        estado=estado or "Mensaje generado",
                        asesor=asesor or "",
                        mensaje=mensaje or None,
                        email_tienda=email_tienda or "",
                        motivo=motivo or "",
                        fecha_reprogramada=fecha_reprogramada or "",
                        fecha_anterior=fecha_anterior or "",
                        lote_id=lote_id or "",
                        created_at=now,
                        updated_at=now,
                    )
                )
            session.commit()
            return cls.resumen_local(local, dia=fecha, db=session)
        except Exception:
            session.rollback()
            raise
        finally:
            if own:
                session.close()

    @classmethod
    def resumen_local(
        cls,
        local: str,
        *,
        dia: str | date | None = None,
        db: Session | None = None,
        data: dict | None = None,  # compat; ignorado
    ) -> dict[str, Any]:
        del data
        cls.migrar_json_si_existe(db)
        fecha = cls._parse_fecha(dia)
        clave = cls._clave_local(local)
        session, own = cls._session(db)
        try:
            rows = (
                session.query(ReprogramacionEnvio)
                .filter(
                    ReprogramacionEnvio.fecha == fecha,
                    ReprogramacionEnvio.local == clave,
                    ReprogramacionEnvio.canal == "cliente",
                )
                .order_by(ReprogramacionEnvio.id.asc())
                .all()
            )
            enviados = [cls._row_to_dict(r) for r in rows]
            return {
                "fecha": fecha.isoformat(),
                "local": clave,
                "total_cliente": len(enviados),
                "enviados": enviados,
            }
        finally:
            if own:
                session.close()

    @classmethod
    def resumen_dia(cls, dia: str | date | None = None, db: Session | None = None) -> dict[str, Any]:
        cls.migrar_json_si_existe(db)
        fecha = cls._parse_fecha(dia)
        session, own = cls._session(db)
        try:
            rows = (
                session.query(ReprogramacionEnvio)
                .filter(
                    ReprogramacionEnvio.fecha == fecha,
                    ReprogramacionEnvio.canal == "cliente",
                )
                .order_by(ReprogramacionEnvio.local.asc(), ReprogramacionEnvio.id.asc())
                .all()
            )
            por_local_map: dict[str, list[dict]] = {}
            for r in rows:
                por_local_map.setdefault(r.local, []).append(cls._row_to_dict(r))
            por_local = [
                {
                    "local": local,
                    "total_cliente": len(items),
                    "enviados": items,
                }
                for local, items in sorted(por_local_map.items())
            ]
            return {
                "fecha": fecha.isoformat(),
                "total_cliente": len(rows),
                "por_local": por_local,
                "fuente": "base_de_datos",
            }
        finally:
            if own:
                session.close()

    @classmethod
    def listar(
        cls,
        *,
        fecha: str | date | None = None,
        local: str | None = None,
        limit: int = 200,
        db: Session | None = None,
    ) -> dict[str, Any]:
        cls.migrar_json_si_existe(db)
        session, own = cls._session(db)
        try:
            q = session.query(ReprogramacionEnvio).order_by(
                ReprogramacionEnvio.fecha.desc(),
                ReprogramacionEnvio.id.desc(),
            )
            if fecha:
                q = q.filter(ReprogramacionEnvio.fecha == cls._parse_fecha(fecha))
            if local and local.strip():
                q = q.filter(ReprogramacionEnvio.local == cls._clave_local(local))
            total = q.count()
            rows = q.limit(max(1, min(limit, 1000))).all()
            return {
                "total": total,
                "items": [cls._row_to_dict(r, completo=True) for r in rows],
                "fuente": "base_de_datos",
            }
        finally:
            if own:
                session.close()

    @classmethod
    def _row_to_dict(cls, r: ReprogramacionEnvio, *, completo: bool = False) -> dict[str, Any]:
        base = {
            "id": r.id,
            "hora": (r.updated_at or r.created_at or datetime.utcnow()).strftime("%H:%M"),
            "nombre": r.nombre,
            "producto": r.producto,
            "factura": r.factura,
            "telefono": r.telefono,
            "canal": r.canal,
            "estado": r.estado,
            "local": r.local,
            "fecha": r.fecha.isoformat() if r.fecha else "",
        }
        if completo:
            base.update({
                "asesor": r.asesor,
                "mensaje": r.mensaje or "",
                "email_tienda": r.email_tienda,
                "motivo": r.motivo,
                "fecha_reprogramada": r.fecha_reprogramada,
                "fecha_anterior": r.fecha_anterior,
                "lote_id": r.lote_id,
                "created_at": r.created_at.isoformat() if r.created_at else "",
                "updated_at": r.updated_at.isoformat() if r.updated_at else "",
            })
        return base
