"""Reprogramación de entregas — mensajes cliente, tienda y correo (matriz diaria)."""

from __future__ import annotations

import io
import re
import uuid
from collections import defaultdict
from typing import Any

import pandas as pd

from config import settings
from services.reprogramacion_log_service import ReprogramacionLogService
from services.tiendas_service import TiendasService
from services.whatsapp_service import WhatsAppService

# Emojis Unicode estándar (compatibles Android / iOS)
MAPEO_COLUMNAS: dict[str, tuple[str, ...]] = {
    "nombre": ("nombre", "cliente", "name", "paciente", "contacto_nombre"),
    "telefono": (
        "telefono", "teléfono", "telefono_cliente", "celular", "whatsapp",
        "phone", "movil", "móvil", "contacto", "numero", "número",
    ),
    "local": ("local", "tienda", "sucursal", "tienda_compra"),
    "producto": ("producto", "articulo", "artículo", "lente", "descripcion", "item"),
    "orden": ("orden", "numero_orden", "n_orden", "no_orden", "pedido", "numero_pedido", "n_pedido"),
    "cedula": ("cedula", "cédula", "id", "cedula_id", "documento"),
    "factura": ("factura", "numero_factura", "n_factura", "nº_factura", "no_factura"),
    "email_tienda": (
        "email_tienda", "correo_tienda", "email_local", "correo_local",
        "email", "correo", "mail_tienda",
    ),
    "fecha_reprogramada": (
        "fecha_reprogramada", "nueva_fecha", "fecha_nueva", "fecha_entrega_nueva",
        "nueva_fecha_entrega", "fecha_entrega", "fecha_prometida_nueva", "reprogramacion",
    ),
    "fecha_anterior": (
        "fecha_anterior", "fecha_original", "fecha_previa", "fecha_prometida",
        "fecha_entrega_prometida", "fecha_prometida_entrega", "entrega_prometida",
    ),
    "hora": ("hora", "horario", "hora_entrega", "hora_retiro", "time"),
    "motivo": ("motivo", "razon", "razón", "causa", "detalle", "observacion", "observación"),
}

# Scripts oficiales CX — emojis SOLO con escapes \U (archivo ASCII-safe, no se corrompe por encoding)
# El frontend recompone el mensaje con String.fromCodePoint al enviar (fuente de verdad para WA).
PLANTILLA_CLIENTE = (
    "\U0001f4c5 REPROGRAMACI\u00d3N DE ENTREGA\n"
    "\U0001f4e6 Producto: {producto}\n"
    "\U0001f3ea Tienda: {local}\n"
    "\U0001f4c4 Factura: {factura}\n"
    "--------------------\n"
    "Hola, {nombre} \U0001f44b\n"
    "\n"
    "Te saluda {asesor}, de Servicio al Cliente de \u00d3ptica Los Andes.\n"
    "Queremos contarte que tu orden no estar\u00e1 lista dentro del plazo que te indicamos inicialmente. "
    "Lamentamos mucho este cambio y las molestias que pueda ocasionarte. \U0001f64f\n"
    "Te enviaremos otro mensaje apenas tu pedido est\u00e9 disponible.\n"
    "Gracias por tu comprensi\u00f3n. \U0001f499\n"
    "--------------------\n"
    "Si tienes alguna duda, escr\u00edbenos con confianza o comun\u00edcate con nosotros al "
    "1800-678-422 opci\u00f3n 2. \U0001f4ac\U0001f60a"
)

PLANTILLA_TIENDA = (
    "\u2705 MENSAJE ENVIADO AL CLIENTE\n"
    "\n"
    "Hola, equipo {local} \U0001f44b\n"
    "Les saluda {asesor}, de Servicio al Cliente.\n"
    "Les confirmo que el mensaje de reprogramaci\u00f3n de entrega ya fue enviado al cliente.\n"
    "\n"
    "\U0001f4cd Tienda: {local}\n"
    "\U0001f4c4 Factura: {factura}\n"
    "\U0001f4e6 Producto: {producto}\n"
    "\U0001f464 Cliente: {nombre}\n"
    "\n"
    "Por favor, mantenerse pendientes del estado de la orden y, en caso de que el cliente se comunique "
    "o se acerque a la tienda, atenderlo con mucha delicadeza, empat\u00eda y predisposici\u00f3n, "
    "brind\u00e1ndole toda la informaci\u00f3n disponible. \U0001f64f\U0001f499"
)

# Alias para UI / restauración
PLANTILLA_EJEMPLO = PLANTILLA_CLIENTE


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


def _aplicar_vars(plantilla: str, vars_map: dict[str, str]) -> str:
    texto = plantilla
    for key, val in vars_map.items():
        texto = texto.replace("{" + key + "}", val)
    return texto.strip()


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

        mapeo = {campo: _resolver_columna(cols, aliases) for campo, aliases in MAPEO_COLUMNAS.items()}
        col_tel = mapeo.get("telefono")
        if not col_tel and not mapeo.get("nombre"):
            raise ValueError(
                "No se encontró columna de teléfono ni nombre. "
                "Use encabezados: telefono, nombre, local, producto, factura."
            )
        if not col_tel:
            advertencias.append("Sin columna de teléfono — se generarán mensajes tienda/correo; WhatsApp cliente quedará pendiente.")
        if not mapeo.get("nombre"):
            advertencias.append("No se detectó columna 'nombre' — se usará un saludo genérico.")

        cols_mapeadas = {v for v in mapeo.values() if v}
        contactos: list[dict[str, Any]] = []
        vistos: set[str] = set()

        for i, row in df.iterrows():
            tel = _limpiar_celda(row.get(col_tel)) if col_tel else ""
            nombre = _limpiar_celda(row.get(mapeo["nombre"], "")) if mapeo.get("nombre") else ""
            if not tel and not nombre:
                continue

            tel_key = WhatsAppService.limpiar_telefono(tel) if tel else ""
            if tel and (not tel_key or len(tel_key) < 9):
                advertencias.append(f"Fila {int(i) + 2}: teléfono inválido «{tel}» — se mantiene sin WA cliente.")
                tel_key = ""
            dedupe = tel_key or f"row-{i}-{nombre}"
            if dedupe in vistos:
                continue
            vistos.add(dedupe)

            contacto: dict[str, Any] = {
                "nombre": nombre or "amigo/a",
                "telefono": tel,
                "local": _limpiar_celda(row.get(mapeo["local"], "")) if mapeo.get("local") else "",
                "producto": _limpiar_celda(row.get(mapeo["producto"], "")) if mapeo.get("producto") else "",
                "orden": _limpiar_celda(row.get(mapeo["orden"], "")) if mapeo.get("orden") else "",
                "cedula": _limpiar_celda(row.get(mapeo["cedula"], "")) if mapeo.get("cedula") else "",
                "factura": _limpiar_celda(row.get(mapeo["factura"], "")) if mapeo.get("factura") else "",
                "email_tienda": (
                    _limpiar_celda(row.get(mapeo["email_tienda"], ""))
                    if mapeo.get("email_tienda") else ""
                ),
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
            raise ValueError("No se extrajeron filas válidas de la matriz. Revise nombres y teléfonos.")

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
        **globales: str,
    ) -> dict[str, str]:
        local = contacto.get("local") or contacto.get("tienda") or "Óptica Los Andes"
        producto = contacto.get("producto") or "Pedido óptico"
        orden = contacto.get("orden") or contacto.get("factura") or "—"
        factura = contacto.get("factura") or contacto.get("orden") or orden
        vars_map = {
            "nombre": contacto.get("nombre") or "amigo/a",
            "telefono": contacto.get("telefono") or "",
            "local": local,
            "tienda": local,
            "producto": producto,
            "orden": orden,
            "pedido": producto,
            "cedula": contacto.get("cedula") or "",
            "factura": factura,
            "asesor": asesor or settings.default_asesor,
            "n": str(indice),
            "fecha_reprogramada": (
                contacto.get("fecha_reprogramada")
                or globales.get("fecha_reprogramada")
                or "te confirmamos pronto"
            ),
            "fecha_anterior": (
                contacto.get("fecha_anterior")
                or globales.get("fecha_anterior")
                or "la fecha que te habíamos prometido"
            ),
            "nueva_fecha": (
                contacto.get("fecha_reprogramada")
                or globales.get("fecha_reprogramada")
                or "te confirmamos pronto"
            ),
            "fecha_prometida": (
                contacto.get("fecha_anterior")
                or globales.get("fecha_anterior")
                or "la fecha que te habíamos prometido"
            ),
            "hora": contacto.get("hora") or globales.get("hora") or "",
            "motivo": (
                contacto.get("motivo")
                or globales.get("motivo")
                or "retraso en la producción del laboratorio"
            ),
            "email_tienda": contacto.get("email_tienda") or "",
        }
        for k, v in (contacto.get("extra") or {}).items():
            key = re.sub(r"[^a-z0-9_]", "_", k.lower())
            vars_map[key] = str(v)
        return vars_map

    @classmethod
    def _wa_tienda(cls, local: str, mensaje: str) -> str:
        tienda = TiendasService.resolver_para_cliente(local)
        num = tienda.get("whatsapp_grupo") or ""
        if not num:
            return ""
        return WhatsAppService.generar_enlace(num, mensaje)

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
        registrar_log: bool = True,
    ) -> dict[str, Any]:
        """Genera mensajes cliente + tienda por fila y correos agrupados por local.

        Si registrar_log=True, contabiliza cada cliente en el log del día por local
        (para la matriz del correo y el histórico).
        """
        del plantilla, incluir_pie  # scripts oficiales fijos; se mantiene firma API
        asesor_f = (asesor or "").strip() or settings.default_asesor
        globales = {
            "fecha_reprogramada": fecha_reprogramada.strip(),
            "fecha_anterior": fecha_anterior.strip(),
            "hora": hora.strip(),
            "motivo": motivo.strip(),
        }
        lote_id = uuid.uuid4().hex[:16]
        items: list[dict[str, Any]] = []
        por_local: dict[str, list[dict]] = defaultdict(list)

        for i, c in enumerate(contactos, start=1):
            vars_map = cls._variables_contacto(c, asesor_f, i, **globales)
            tel_raw = c.get("telefono", "")
            tel_limpio = WhatsAppService.limpiar_telefono(tel_raw) if tel_raw else ""
            error = None
            valido = bool(tel_limpio and len(tel_limpio) >= 11)
            if not valido:
                error = "Teléfono inválido o ausente (solo tienda/correo)"

            msg_cliente = WhatsAppService.normalizar_mensaje_whatsapp(
                _aplicar_vars(PLANTILLA_CLIENTE, vars_map)
            )
            msg_tienda = WhatsAppService.normalizar_mensaje_whatsapp(
                _aplicar_vars(PLANTILLA_TIENDA, vars_map)
            )
            wa_cliente = WhatsAppService.generar_enlace(tel_limpio, msg_cliente) if valido else ""
            wa_tienda = cls._wa_tienda(vars_map["local"], msg_tienda)

            if registrar_log:
                ReprogramacionLogService.registrar_envio(
                    local=vars_map["local"],
                    nombre=vars_map["nombre"],
                    producto=vars_map["producto"],
                    factura=vars_map["factura"],
                    telefono=tel_raw,
                    canal="cliente",
                    estado="Mensaje generado" if valido else "Pendiente (sin teléfono)",
                    asesor=asesor_f,
                    mensaje=msg_cliente,
                    email_tienda=c.get("email_tienda") or "",
                    motivo=vars_map.get("motivo") or "",
                    fecha_reprogramada=vars_map.get("fecha_reprogramada") or "",
                    fecha_anterior=vars_map.get("fecha_anterior") or "",
                    lote_id=lote_id,
                )

            item = {
                "indice": i,
                "nombre": vars_map["nombre"],
                "telefono": tel_raw,
                "telefono_limpio": tel_limpio,
                "local": vars_map["local"],
                "producto": vars_map["producto"],
                "factura": vars_map["factura"],
                "orden": vars_map["orden"],
                "email_tienda": c.get("email_tienda") or "",
                "mensaje": msg_cliente,
                "mensaje_cliente": msg_cliente,
                "mensaje_tienda": msg_tienda,
                "wa_link": wa_cliente,
                "wa_link_cliente": wa_cliente,
                "wa_link_tienda": wa_tienda,
                "valido": valido,
                "error": error,
            }
            items.append(item)
            por_local[vars_map["local"]].append(item)

        correos: list[dict[str, Any]] = []
        for local, filas in por_local.items():
            correo = cls.generar_correo_local(local, filas, asesor=asesor_f)
            correos.append(correo)

        validos = sum(1 for x in items if x["valido"])
        resumen_dia = ReprogramacionLogService.resumen_dia()
        return {
            "total": len(items),
            "validos": validos,
            "invalidos": len(items) - validos,
            "items": items,
            "correos": correos,
            "resumen_dia": resumen_dia,
            "lote_id": lote_id,
            "plantillas": {
                "cliente": PLANTILLA_CLIENTE,
                "tienda": PLANTILLA_TIENDA,
            },
        }

    @classmethod
    def generar_correo_local(
        cls,
        local: str,
        filas: list[dict],
        *,
        asesor: str = "",
        usar_log_dia: bool = True,
    ) -> dict[str, Any]:
        asesor_f = (asesor or "").strip() or settings.default_asesor
        # Preferir matriz del día (acumulada) si hay registros en log
        filas_matriz = filas
        if usar_log_dia:
            resumen = ReprogramacionLogService.resumen_local(local)
            if resumen.get("enviados"):
                filas_matriz = [
                    {
                        "nombre": e.get("nombre", ""),
                        "producto": e.get("producto", ""),
                        "factura": e.get("factura", ""),
                        "estado": e.get("estado", "Mensaje enviado"),
                    }
                    for e in resumen["enviados"]
                ]

        lineas_tabla = [
            "| N.º | Cliente              | Producto           | Orden/Factura   | Estado de comunicación |",
            "| --: | -------------------- | ------------------ | --------------- | ---------------------- |",
        ]
        for i, f in enumerate(filas_matriz, start=1):
            nombre = (f.get("nombre") or "—")[:20].ljust(20)
            producto = (f.get("producto") or "—")[:18].ljust(18)
            factura = (f.get("factura") or f.get("orden") or "—")[:15].ljust(15)
            estado = f.get("estado") or ("Mensaje enviado" if f.get("valido", True) else "Pendiente")
            lineas_tabla.append(
                f"| {i:>3} | {nombre} | {producto} | {factura} | {estado:<22} |"
            )

        cuerpo = f"""Estimado Equipo {local}:

Les saluda {asesor_f}, de Servicio al Cliente.

Por medio del presente, les confirmo que se enviaron los mensajes de reprogramación de entrega a los clientes detallados en la siguiente matriz:

{chr(10).join(lineas_tabla)}

Por favor, mantenerse pendientes del estado de cada orden. En caso de que alguno de los clientes se comunique o se acerque a la tienda, solicitamos atenderlo con delicadeza, empatía y predisposición, brindándole información clara y el acompañamiento necesario.

Agradezco su apoyo y seguimiento en cada caso.

Saludos cordiales,

{asesor_f}
Servicio al Cliente
Óptica Los Andes"""

        email_dest = ""
        for f in filas:
            if f.get("email_tienda"):
                email_dest = f["email_tienda"]
                break

        total_hoy = len(filas_matriz)
        return {
            "local": local,
            "asunto": f"Reprogramación de entregas — {local} ({total_hoy} cliente(s))",
            "cuerpo": cuerpo,
            "email_tienda": email_dest,
            "total_matriz": total_hoy,
            "filas": [
                {
                    "nombre": f.get("nombre"),
                    "producto": f.get("producto"),
                    "factura": f.get("factura") or f.get("orden"),
                    "estado": f.get("estado") or "Mensaje enviado",
                }
                for f in filas_matriz
            ],
        }

    @classmethod
    def marcar_enviado_cliente(cls, item: dict) -> dict[str, Any]:
        return ReprogramacionLogService.registrar_envio(
            local=item.get("local") or "Sin tienda",
            nombre=item.get("nombre") or "",
            producto=item.get("producto") or "",
            factura=item.get("factura") or item.get("orden") or "",
            telefono=item.get("telefono") or "",
            canal="cliente",
            estado="Mensaje enviado",
        )

    @classmethod
    def exportar_excel(cls, items: list[dict]) -> bytes:
        filas = []
        for it in items:
            filas.append({
                "N°": it.get("indice"),
                "Nombre": it.get("nombre"),
                "Teléfono": it.get("telefono"),
                "Local": it.get("local"),
                "Producto": it.get("producto"),
                "Factura": it.get("factura"),
                "Válido WA": "Sí" if it.get("valido") else "No",
                "Error": it.get("error") or "",
                "Mensaje cliente": it.get("mensaje_cliente") or it.get("mensaje"),
                "Mensaje tienda": it.get("mensaje_tienda") or "",
                "Enlace WA cliente": it.get("wa_link_cliente") or it.get("wa_link"),
                "Enlace WA tienda": it.get("wa_link_tienda") or "",
            })
        df = pd.DataFrame(filas)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Entregas reprogramadas")
            ws = writer.sheets["Entregas reprogramadas"]
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)
        buf.seek(0)
        return buf.getvalue()
