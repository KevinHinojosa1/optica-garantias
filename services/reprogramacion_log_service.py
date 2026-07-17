"""Registro diario de mensajes de reprogramación enviados por local."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from config import settings

_lock = threading.Lock()
LOG_PATH = settings.base_dir / "data" / "reprogramaciones_envios.json"


class ReprogramacionLogService:
    @classmethod
    def _leer(cls) -> dict[str, Any]:
        if not LOG_PATH.exists():
            return {}
        try:
            return json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    @classmethod
    def _escribir(cls, data: dict[str, Any]) -> None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def _hoy(cls) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    @classmethod
    def _clave_local(cls, local: str) -> str:
        return (local or "Sin tienda").strip() or "Sin tienda"

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
    ) -> dict[str, Any]:
        """Registra un envío al cliente (o tienda) y devuelve el resumen del día para ese local."""
        with _lock:
            data = cls._leer()
            dia = cls._hoy()
            clave = cls._clave_local(local)
            data.setdefault(dia, {})
            data[dia].setdefault(clave, {"enviados": [], "total": 0})
            entry = {
                "hora": datetime.now().strftime("%H:%M"),
                "nombre": nombre,
                "producto": producto,
                "factura": factura,
                "telefono": telefono,
                "canal": canal,
                "estado": estado,
            }
            # Evitar duplicados del mismo cliente/factura en el mismo día (actualizar estado)
            enviados = data[dia][clave]["enviados"]
            clave_fila = f"{canal}|{(factura or '').strip().lower()}|{(nombre or '').strip().lower()}"
            actualizado = False
            for e in enviados:
                ek = f"{e.get('canal')}|{(e.get('factura') or '').strip().lower()}|{(e.get('nombre') or '').strip().lower()}"
                if ek == clave_fila:
                    e.update(entry)
                    actualizado = True
                    break
            if not actualizado:
                enviados.append(entry)
            clientes = [e for e in enviados if e.get("canal") == "cliente"]
            data[dia][clave]["total"] = len(clientes)
            cls._escribir(data)
            return cls.resumen_local(local, dia=dia, data=data)

    @classmethod
    def resumen_local(
        cls,
        local: str,
        *,
        dia: str | None = None,
        data: dict | None = None,
    ) -> dict[str, Any]:
        data = data if data is not None else cls._leer()
        dia = dia or cls._hoy()
        clave = cls._clave_local(local)
        bloque = (data.get(dia) or {}).get(clave) or {"enviados": [], "total": 0}
        clientes = [e for e in bloque.get("enviados", []) if e.get("canal") == "cliente"]
        return {
            "fecha": dia,
            "local": clave,
            "total_cliente": len(clientes),
            "enviados": clientes,
        }

    @classmethod
    def resumen_dia(cls, dia: str | None = None) -> dict[str, Any]:
        data = cls._leer()
        dia = dia or cls._hoy()
        locales = data.get(dia) or {}
        por_local = []
        total = 0
        for local, bloque in sorted(locales.items()):
            clientes = [e for e in bloque.get("enviados", []) if e.get("canal") == "cliente"]
            total += len(clientes)
            por_local.append({
                "local": local,
                "total_cliente": len(clientes),
                "enviados": clientes,
            })
        return {"fecha": dia, "total_cliente": total, "por_local": por_local}
