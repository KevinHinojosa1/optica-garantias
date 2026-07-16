"""Reprogramaciones WhatsApp — plantilla + Excel + wa.me / WhatsApp Business."""

from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any

import pandas as pd

from config import settings
from services.whatsapp_service import WhatsAppService

MAPEO_COLUMNAS: dict[str, tuple[str, ...]] = {
    "nombre": ("nombre", "cliente", "name", "paciente", "contacto_nombre"),
    "telefono": (
        "telefono", "teléfono", "telefono_cliente", "celular", "whatsapp",
        "phone", "movil", "móvil", "contacto", "numero", "número",
    ),
    "local": ("local", "tienda", "sucursal", "tienda_compra"),
    "producto": ("producto", "articulo", "artículo", "lente", "pedido"),
    "cedula": ("cedula", "cédula", "id", "cedula_id", "documento"),
    "factura": ("factura", "numero_factura", "n_factura", "nº_factura", "no_factura"),
    "fecha_reprogramada": (
        "fecha_reprogramada", "nueva_fecha", "fecha_nueva", "fecha_cita",
        "fecha_entrega", "fecha_prometida_nueva", "reprogramacion",
    ),
    "fecha_anterior": (
        "fecha_anterior", "fecha_original", "fecha_previa", "fecha_prometida",
        "fecha_cita_anterior", "cita_anterior",
    ),
    "hora": ("hora", "horario", "hora_cita", "hora_entrega", "time"),
    "motivo": ("motivo", "razon", "razón", "causa", "detalle", "observacion", "observación"),
}

CAMPOS_MAPEADOS = frozenset(MAPEO_COLUMNAS.keys())

PLANTILLA_EJEMPLO = """Hola *{nombre}* 👋

Te escribimos desde *{local}* de *Óptica Los Andes* para avisarte de un cambio en tu cita 📅

👓 *Tu pedido:* {producto}

🗓️ *Fecha anterior:* {fecha_anterior}
✅ *Nueva fecha:* {fecha_reprogramada}
🕐 *Hora:* {hora}

ℹ️ *Motivo:* {motivo}

Si esta fecha no te funciona, cuéntanos y buscamos otra opción que te quede mejor 😊

¡Gracias por tu comprensión! 💙"""


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


def _pie_reprogramacion(asesor: str) -> str:
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    pie = f"━━━━━━━━━━━━━━━━━━━━\n🕐 *Mensaje enviado:* {fecha}"
    if asesor:
        pie += f"\n👨‍💼 *Tu asesor:* {asesor}"
    pie += "\n💙 *Gracias por confiar en Óptica Los Andes*"
    pie += "\n_Si tienes dudas, escríbenos con confianza._"
    return pie


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
            advertencias.append("No se detectó columna 'nombre' — se usará un saludo genérico.")
        if not mapeo.get("fecha_reprogramada"):
            advertencias.append("Sin columna de nueva fecha — puedes definirla en el formulario global.")

        cols_mapeadas = {v for v in mapeo.values() if v}
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
            contacto: dict[str, Any] = {
                "nombre": nombre or "amigo/a",
                "telefono": tel,
                "local": _limpiar_celda(row.get(mapeo["local"], "")) if mapeo.get("local") else "",
                "producto": _limpiar_celda(row.get(mapeo["producto"], "")) if mapeo.get("producto") else "",
                "cedula": _limpiar_celda(row.get(mapeo["cedula"], "")) if mapeo.get("cedula") else "",
                "factura": _limpiar_celda(row.get(mapeo["factura"], "")) if mapeo.get("factura") else "",
                "fecha_reprogramada": (
                    _limpiar_celda(row.get(mapeo["fecha_reprogramada"], ""))
                    if mapeo.get("fecha_reprogramada") else ""
                ),
                "fecha_anterior": (
                    _limpiar_celda(row.get(mapeo["fecha_anterior"], ""))
                    if mapeo.get("fecha_anterior") else ""
                ),
                "hora": _limpiar_celda(row.get(mapeo["hora"], "")) if mapeo.get("hora") else "",
                "motivo": _limpiar_celda(row.get(mapeo["motivo"], "")) if mapeo.get("motivo") else "",
                "extra": {},
            }
            for col in cols:
                if col in cols_mapeadas:
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
    def _variables_contacto(
        cls,
        contacto: dict,
        asesor: str,
        indice: int,
        *,
        fecha_reprogramada: str = "",
        fecha_anterior: str = "",
        hora: str = "",
        motivo: str = "",
    ) -> dict[str, str]:
        local = contacto.get("local") or contacto.get("tienda") or "tu tienda Óptica Los Andes"
        producto = contacto.get("producto") or ""
        vars_map = {
            "nombre": contacto.get("nombre") or "amigo/a",
            "telefono": contacto.get("telefono") or "",
            "local": local,
            "tienda": local,
            "producto": producto if producto else "tu pedido en Óptica Los Andes",
            "cedula": contacto.get("cedula") or "",
            "factura": contacto.get("factura") or "",
            "asesor": asesor or settings.default_asesor,
            "n": str(indice),
            "fecha_reprogramada": (
                contacto.get("fecha_reprogramada") or fecha_reprogramada or "te confirmamos pronto"
            ),
            "fecha_anterior": (
                contacto.get("fecha_anterior") or fecha_anterior or "la fecha acordada"
            ),
            "nueva_fecha": (
                contacto.get("fecha_reprogramada") or fecha_reprogramada or "te confirmamos pronto"
            ),
            "fecha_prometida": (
                contacto.get("fecha_anterior") or fecha_anterior or "la fecha acordada"
            ),
            "hora": contacto.get("hora") or hora or "por confirmar",
            "horario": contacto.get("hora") or hora or "por confirmar",
            "motivo": contacto.get("motivo") or motivo or "ajuste operativo en tienda",
        }
        for k, v in (contacto.get("extra") or {}).items():
            key = re.sub(r"[^a-z0-9_]", "_", k.lower())
            vars_map[key] = str(v)
        return vars_map

    @classmethod
    def personalizar_plantilla(
        cls,
        plantilla: str,
        contacto: dict,
        asesor: str,
        indice: int,
        **globales: str,
    ) -> str:
        vars_map = cls._variables_contacto(contacto, asesor, indice, **globales)
        texto = plantilla
        for key, val in vars_map.items():
            texto = texto.replace("{" + key + "}", val)
        return texto.strip()

    @classmethod
    def armar_mensaje_completo(cls, cuerpo: str, asesor: str, contacto: dict) -> str:
        bloques = ["📅 *ÓPTICA LOS ANDES — REPROGRAMACIÓN DE CITA*"]
        if contacto.get("local"):
            bloques.append(f"📍 *Tienda:* {contacto['local']}")
        bloques.append("━━━━━━━━━━━━━━━━━━━━")
        bloques.append(cuerpo)
        bloques.append(_pie_reprogramacion(asesor))
        return "\n\n".join(bloques)

    @classmethod
    def generar_lote(
        cls,
        plantilla: str,
        contactos: list[dict],
        *,
        asesor: str = "",
        incluir_pie: bool = True,
        fecha_reprogramada: str = "",
        fecha_anterior: str = "",
        hora: str = "",
        motivo: str = "",
    ) -> dict[str, Any]:
        asesor_f = (asesor or "").strip() or settings.default_asesor
        globales = {
            "fecha_reprogramada": fecha_reprogramada.strip(),
            "fecha_anterior": fecha_anterior.strip(),
            "hora": hora.strip(),
            "motivo": motivo.strip(),
        }
        items: list[dict[str, Any]] = []

        for i, c in enumerate(contactos, start=1):
            tel_raw = c.get("telefono", "")
            tel_limpio = WhatsAppService.limpiar_telefono(tel_raw)
            error = None
            valido = True

            if not tel_limpio or len(tel_limpio) < 11:
                valido = False
                error = "Teléfono inválido"

            cuerpo = cls.personalizar_plantilla(plantilla, c, asesor_f, i, **globales)
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
            df.to_excel(writer, index=False, sheet_name="Reprogramaciones WA")
            ws = writer.sheets["Reprogramaciones WA"]
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)
        buf.seek(0)
        return buf.getvalue()