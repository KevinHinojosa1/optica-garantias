"""Envíos masivos WhatsApp — plantilla + Excel + enlaces wa.me personalizados."""

from __future__ import annotations

import io
import re
from typing import Any

import pandas as pd

from config import settings
from services.whatsapp_service import WhatsAppService

MAPEO_COLUMNAS: dict[str, tuple[str, ...]] = {
    "nombre": ("nombre", "cliente", "name", "paciente", "contacto_nombre"),
    "telefono": ("telefono", "teléfono", "telefono_cliente", "celular", "whatsapp", "phone", "movil", "móvil", "contacto", "numero", "número"),
    "local": ("local", "tienda", "sucursal", "tienda_compra"),
    "producto": ("producto", "articulo", "artículo", "lente"),
    "cedula": ("cedula", "cédula", "id", "cedula_id", "documento"),
    "factura": ("factura", "numero_factura", "n_factura", "nº_factura", "no_factura"),
}

PLANTILLA_EJEMPLO = """Hola *{nombre}* 👋

Le saluda *Óptica Los Andes*. Le escribimos desde {local} para informarle sobre su pedido.

{producto}

Ante cualquier consulta, con gusto le atendemos."""


def _normalizar_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [
        str(c).strip().lower()
        .replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u")
        .replace("ñ", "n")
        .replace(" ", "_")
        for c in out.columns
    ]
    return out


def _limpiar_celda(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    if s.endswith(".0") and s[:-2].replace(".", "").isdigit():
        s = s[:-2]
    return "" if s.lower() in ("nan", "none", "nat") else s


def _resolver_columna(columnas: list[str], claves: tuple[str, ...]) -> str | None:
    for col in columnas:
        norm = col.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        if norm in claves or col in claves:
            return col
    return None


class WhatsAppEnviosService:
    @classmethod
    def parsear_excel(cls, content: bytes, filename: str) -> dict[str, Any]:
        lower = (filename or "").lower()
        if lower.endswith(".csv"):
            df = None
            for enc in ("utf-8", "latin-1", "cp1252"):
                try:
                    df = pd.read_csv(io.BytesIO(content), encoding=enc, dtype=str)
                    break
                except UnicodeDecodeError:
                    continue
            if df is None:
                raise ValueError("No se pudo leer el CSV. Use UTF-8.")
        elif lower.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content), dtype=str)
        else:
            raise ValueError("Formato no soportado. Suba Excel (.xlsx) o CSV.")

        df = _normalizar_cols(df)
        cols = list(df.columns)
        advertencias: list[str] = []

        col_tel = _resolver_columna(cols, MAPEO_COLUMNAS["telefono"])
        if not col_tel:
            raise ValueError(
                "No se encontró columna de teléfono. Use encabezados como: telefono, contacto, celular o whatsapp."
            )

        mapeo = {campo: _resolver_columna(cols, aliases) for campo, aliases in MAPEO_COLUMNAS.items()}
        if not mapeo.get("nombre"):
            advertencias.append("No se detectó columna 'nombre' — se usará 'Estimado/a cliente'.")

        contactos: list[dict[str, Any]] = []
        vistos: set[str] = set()

        for i, row in df.iterrows():
            tel = _limpiar_celda(row.get(col_tel))
            if not tel:
                continue
            tel_key = WhatsAppService.limpiar_telefono(tel)
            if not tel_key or len(tel_key) < 9:
                advertencias.append(f"Fila {int(i) + 2}: teléfono inválido «{tel}» — omitido.")
                continue
            if tel_key in vistos:
                continue
            vistos.add(tel_key)

            nombre = _limpiar_celda(row.get(mapeo["nombre"], "")) if mapeo.get("nombre") else ""
            contacto = {
                "nombre": nombre or "Estimado/a cliente",
                "telefono": tel,
                "local": _limpiar_celda(row.get(mapeo["local"], "")) if mapeo.get("local") else "",
                "producto": _limpiar_celda(row.get(mapeo["producto"], "")) if mapeo.get("producto") else "",
                "cedula": _limpiar_celda(row.get(mapeo["cedula"], "")) if mapeo.get("cedula") else "",
                "factura": _limpiar_celda(row.get(mapeo["factura"], "")) if mapeo.get("factura") else "",
                "extra": {},
            }
            for col in cols:
                if col in (mapeo.get("telefono"), mapeo.get("nombre"), mapeo.get("local"),
                           mapeo.get("producto"), mapeo.get("cedula"), mapeo.get("factura")):
                    continue
                val = _limpiar_celda(row.get(col))
                if val:
                    contacto["extra"][col] = val
            contactos.append(contacto)

        if not contactos:
            raise ValueError("No se extrajeron contactos válidos. Revise que el Excel tenga números en la columna de teléfono.")

        return {
            "total": len(contactos),
            "columnas_detectadas": cols,
            "contactos": contactos,
            "advertencias": advertencias[:20],
        }

    @classmethod
    def _variables_contacto(cls, contacto: dict, asesor: str, indice: int) -> dict[str, str]:
        local = contacto.get("local") or contacto.get("tienda") or "su tienda Óptica Los Andes"
        producto = contacto.get("producto") or ""
        vars_map = {
            "nombre": contacto.get("nombre") or "Estimado/a cliente",
            "telefono": contacto.get("telefono") or "",
            "local": local,
            "tienda": local,
            "producto": producto if producto else "su compra en Óptica Los Andes",
            "cedula": contacto.get("cedula") or "",
            "factura": contacto.get("factura") or "",
            "asesor": asesor or settings.default_asesor,
            "n": str(indice),
        }
        for k, v in (contacto.get("extra") or {}).items():
            key = re.sub(r"[^a-z0-9_]", "_", k.lower())
            vars_map[key] = str(v)
        return vars_map

    @classmethod
    def personalizar_plantilla(cls, plantilla: str, contacto: dict, asesor: str, indice: int) -> str:
        vars_map = cls._variables_contacto(contacto, asesor, indice)
        texto = plantilla
        for key, val in vars_map.items():
            texto = texto.replace("{" + key + "}", val)
        return texto.strip()

    @classmethod
    def armar_mensaje_completo(cls, cuerpo: str, asesor: str, contacto: dict) -> str:
        bloques = ["💬 *ÓPTICA LOS ANDES — MENSAJE AL CLIENTE*"]
        if contacto.get("local"):
            bloques.append(f"📍 *Tienda:* {contacto['local']}")
        bloques.append("━━━━━━━━━━━━━━━━━━━━")
        bloques.append(cuerpo)
        bloques.append(WhatsAppService.pie_scripts(asesor))
        return "\n\n".join(bloques)

    @classmethod
    def generar_lote(
        cls,
        plantilla: str,
        contactos: list[dict],
        *,
        asesor: str = "",
        incluir_pie: bool = True,
    ) -> dict[str, Any]:
        asesor_f = (asesor or "").strip() or settings.default_asesor
        items: list[dict[str, Any]] = []

        for i, c in enumerate(contactos, start=1):
            tel_raw = c.get("telefono", "")
            tel_limpio = WhatsAppService.limpiar_telefono(tel_raw)
            error = None
            valido = True

            if not tel_limpio or len(tel_limpio) < 11:
                valido = False
                error = "Teléfono inválido"

            cuerpo = cls.personalizar_plantilla(plantilla, c, asesor_f, i)
            mensaje = cls.armar_mensaje_completo(cuerpo, asesor_f, c) if incluir_pie else cuerpo
            wa_link = WhatsAppService.generar_enlace(tel_limpio, mensaje) if valido else ""

            items.append({
                "indice": i,
                "nombre": c.get("nombre") or "Sin nombre",
                "telefono": tel_raw,
                "telefono_limpio": tel_limpio,
                "mensaje": mensaje,
                "wa_link": wa_link,
                "valido": valido,
                "error": error,
            })

        validos = sum(1 for x in items if x["valido"])
        return {
            "total": len(items),
            "validos": validos,
            "invalidos": len(items) - validos,
            "items": items,
        }

    @classmethod
    def exportar_excel(cls, items: list[dict]) -> bytes:
        filas = []
        for it in items:
            filas.append({
                "N°": it.get("indice"),
                "Nombre": it.get("nombre"),
                "Teléfono": it.get("telefono"),
                "Teléfono limpio": it.get("telefono_limpio"),
                "Válido": "Sí" if it.get("valido") else "No",
                "Error": it.get("error") or "",
                "Mensaje": it.get("mensaje"),
                "Enlace WhatsApp": it.get("wa_link"),
            })
        df = pd.DataFrame(filas)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Envios WhatsApp")
            ws = writer.sheets["Envios WhatsApp"]
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)
        buf.seek(0)
        return buf.getvalue()