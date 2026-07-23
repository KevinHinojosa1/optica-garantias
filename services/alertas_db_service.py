"""Persistencia de Alertas Telegram en SQLAlchemy (además de CSV/Parquet)."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from database import SessionLocal
from models.alerta import AlertaTelegram


def _parse_fecha(val) -> date | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        ts = pd.to_datetime(val, errors="coerce", dayfirst=True)
        if pd.isna(ts):
            return None
        return ts.date()
    except Exception:
        return None


def _row_dict(row: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in row.items():
        if v is None or (isinstance(v, float) and pd.isna(v)):
            out[k] = ""
        elif isinstance(v, (datetime, pd.Timestamp)):
            out[k] = v.isoformat()
        elif isinstance(v, date):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


class AlertasDbService:
    @classmethod
    def contar(cls, db: Session | None = None) -> int:
        own = False
        if db is None:
            db = SessionLocal()
            own = True
        try:
            return db.query(AlertaTelegram).count()
        finally:
            if own:
                db.close()

    @classmethod
    def guardar_dataframe(cls, df: pd.DataFrame, db: Session | None = None) -> int:
        """Reemplaza el set completo en BD a partir del DataFrame normalizado."""
        own = False
        if db is None:
            db = SessionLocal()
            own = True
        try:
            # Upsert por id; borrar ids que ya no existen
            existentes = {r.id: r for r in db.query(AlertaTelegram).all()}
            vistos: set[int] = set()
            n = 0
            for _, series in df.iterrows():
                row = _row_dict(series.to_dict())
                rid = int(pd.to_numeric(row.get("id") or row.get("n") or 0, errors="coerce") or 0)
                if rid <= 0:
                    continue
                vistos.add(rid)
                payload = json.dumps(row, ensure_ascii=False, default=str)
                fecha = _parse_fecha(row.get("fecha_alerta"))
                fields = dict(
                    n=int(pd.to_numeric(row.get("n") or rid, errors="coerce") or rid),
                    mes=str(row.get("mes") or "")[:40],
                    fecha_alerta=fecha,
                    local=str(row.get("local") or "")[:200],
                    area=str(row.get("area") or "")[:120],
                    cliente=str(row.get("cliente") or "")[:200],
                    contacto=str(row.get("contacto") or row.get("telefono") or "")[:60],
                    estado_gestion=str(row.get("estado_gestion") or "Sin gestión")[:80],
                    clasificacion=str(row.get("clasificacion") or "")[:120],
                    asesor=str(row.get("asesor") or "")[:120],
                    payload_json=payload,
                    updated_at=datetime.utcnow(),
                )
                if rid in existentes:
                    obj = existentes[rid]
                    for k, v in fields.items():
                        setattr(obj, k, v)
                else:
                    db.add(AlertaTelegram(id=rid, **fields))
                n += 1
            for rid, obj in existentes.items():
                if rid not in vistos:
                    db.delete(obj)
            db.commit()
            return n
        except Exception:
            db.rollback()
            raise
        finally:
            if own:
                db.close()

    @classmethod
    def cargar_dataframe(cls, db: Session | None = None) -> pd.DataFrame | None:
        own = False
        if db is None:
            db = SessionLocal()
            own = True
        try:
            rows = db.query(AlertaTelegram).order_by(AlertaTelegram.id.asc()).all()
            if not rows:
                return None
            filas = []
            for r in rows:
                try:
                    d = json.loads(r.payload_json or "{}")
                except json.JSONDecodeError:
                    d = {
                        "id": r.id,
                        "n": r.n,
                        "local": r.local,
                        "cliente": r.cliente,
                        "estado_gestion": r.estado_gestion,
                    }
                d["id"] = r.id
                filas.append(d)
            return pd.DataFrame(filas)
        finally:
            if own:
                db.close()
