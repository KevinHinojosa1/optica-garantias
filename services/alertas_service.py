"""Servicio Alertas Telegram — integración FastAPI del módulo centro_operaciones."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

import httpx
import pandas as pd

from config import settings

from centro_operaciones.constants import (
    AREAS,
    COLUMNAS_EDITABLES,
    COLUMNAS_EXCEL_EXPORTE,
    OPCIONES_CLASIFICACION,
    OPCIONES_CONTESTO,
    OPCIONES_ESTADO,
    OPCIONES_LLAMADA,
)
from centro_operaciones.services.clasificacion import clasificar_dataframe_reglas
from centro_operaciones.services.clasificacion_ia_alertas import clasificar_dataframe_completo
from centro_operaciones.services.datastore import (
    cargar_alertas,
    contar_pendientes,
    filtrar_df,
    fusionar_incremental,
    guardar_alertas,
    importar_excel_bytes,
    recargar_desde_excel,
)
from centro_operaciones.services.exportacion import exportar_matriz_seguimiento
from centro_operaciones.services.graficos import (
    donut_estado,
    heatmap_local_clasificacion,
    heatmap_mes_local,
    tendencia_mensual,
    top_problemas,
)


def _fig_a_dict(fig) -> dict[str, Any]:
    return json.loads(fig.to_json())


def _df_a_filas(df: pd.DataFrame) -> list[dict[str, Any]]:
    out = df.copy()
    if "fecha_alerta" in out.columns:
        out["fecha_alerta"] = pd.to_datetime(out["fecha_alerta"], errors="coerce").dt.strftime("%d/%m/%Y")
    return out.where(pd.notnull(out), "").to_dict(orient="records")


def _aplicar_filtros(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    fecha_desde = filtros.get("fecha_desde")
    fecha_hasta = filtros.get("fecha_hasta")
    if fecha_desde:
        fecha_desde = date.fromisoformat(fecha_desde) if isinstance(fecha_desde, str) else fecha_desde
    if fecha_hasta:
        fecha_hasta = date.fromisoformat(fecha_hasta) if isinstance(fecha_hasta, str) else fecha_hasta
    else:
        max_f = df["fecha_alerta"].max()
        fecha_hasta = max_f.date() if pd.notna(max_f) and hasattr(max_f, "date") else date.today()
    if not fecha_desde:
        min_f = df["fecha_alerta"].min()
        fecha_desde = min_f.date() if pd.notna(min_f) and hasattr(min_f, "date") else date.today() - timedelta(days=90)

    filtrado = filtrar_df(
        df,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        locales=filtros.get("locales") or [],
        areas=filtros.get("areas") or [],
        clasificaciones=filtros.get("clasificaciones") or [],
        estados=filtros.get("estados") or [],
        contesto=filtros.get("contesto") or [],
        texto=filtros.get("texto") or "",
        meses=filtros.get("meses") or [],
    )
    if filtros.get("solo_pendientes"):
        sin_sol = filtrado["solucion"].fillna("").astype(str).str.strip() == ""
        sin_obs = filtrado["observacion_gestion"].fillna("").astype(str).str.strip() == ""
        pend = filtrado["estado_gestion"].isin(["Sin gestión", "Pendiente llamada", ""])
        filtrado = filtrado[sin_sol & sin_obs & pend]
    return filtrado


class AlertasService:
    @staticmethod
    def metadata() -> dict[str, Any]:
        df = cargar_alertas()
        min_f = df["fecha_alerta"].min()
        max_f = df["fecha_alerta"].max()
        meses = sorted(df["mes"].replace("", pd.NA).dropna().unique().tolist())
        return {
            "opciones_llamada": OPCIONES_LLAMADA,
            "opciones_contesto": OPCIONES_CONTESTO,
            "opciones_estado": OPCIONES_ESTADO,
            "opciones_clasificacion": OPCIONES_CLASIFICACION,
            "columnas_editables": COLUMNAS_EDITABLES,
            "columnas_display": [{"field": c, "header": h} for c, h in COLUMNAS_EXCEL_EXPORTE],
            "areas": sorted(df["area"].replace("", pd.NA).dropna().unique().tolist()) or AREAS,
            "meses": meses,
            "locales": sorted(df["local"].dropna().unique().tolist()),
            "fecha_min": min_f.date().isoformat() if pd.notna(min_f) and hasattr(min_f, "date") else None,
            "fecha_max": max_f.date().isoformat() if pd.notna(max_f) and hasattr(max_f, "date") else None,
            "total_casos": len(df),
            "pendientes": contar_pendientes(df),
            "fuente": "ALERTAS TELEGRAM 2026.xlsx — hoja GENERAL",
        }

    @classmethod
    def listar(cls, filtros: dict | None = None) -> dict[str, Any]:
        df = cargar_alertas()
        filtrado = _aplicar_filtros(df, filtros or {})
        return {
            "total": len(df),
            "filtrado": len(filtrado),
            "pendientes": contar_pendientes(filtrado),
            "filas": _df_a_filas(filtrado),
        }

    @classmethod
    def kpis(cls, filtros: dict | None = None) -> dict[str, int]:
        df = cargar_alertas()
        filtrado = _aplicar_filtros(df, filtros or {})
        return {
            "total_filtrado": len(filtrado),
            "sin_gestion": int(filtrado["estado_gestion"].isin(["Sin gestión", "Pendiente llamada", ""]).sum()),
            "resueltos": int((filtrado["estado_gestion"] == "Resuelto").sum()),
            "contesto_si": int(filtrado["contesto"].isin(["Sí", "si", "SI", "Si"]).sum()),
            "pendientes": contar_pendientes(filtrado),
        }

    @classmethod
    def graficos(cls, filtros: dict | None = None) -> dict[str, Any]:
        df = cargar_alertas()
        filtrado = _aplicar_filtros(df, filtros or {})
        return {
            "tendencia": _fig_a_dict(tendencia_mensual(filtrado)),
            "top_problemas": _fig_a_dict(top_problemas(filtrado)),
            "heatmap": _fig_a_dict(heatmap_local_clasificacion(filtrado)),
            "heatmap_mes_local": _fig_a_dict(heatmap_mes_local(filtrado)),
            "donut": _fig_a_dict(donut_estado(filtrado)),
        }

    @classmethod
    def guardar_filas(cls, filas: list[dict]) -> dict[str, Any]:
        df = cargar_alertas()
        if not filas:
            return {"ok": True, "actualizados": 0}
        incoming = pd.DataFrame(filas)
        if "id" not in incoming.columns:
            raise ValueError("Las filas deben incluir el campo id.")
        actualizados = 0
        for _, row in incoming.iterrows():
            rid = int(row["id"])
            mask = df["id"] == rid
            if not mask.any():
                continue
            for col in row.index:
                if col in df.columns and col not in ("id",):
                    df.loc[mask, col] = row[col]
            actualizados += 1
        guardar_alertas(df)
        return {"ok": True, "actualizados": actualizados}

    @classmethod
    def clasificar_reglas(cls, ids: list[int]) -> dict[str, Any]:
        df = cargar_alertas()
        indices = df.index[df["id"].isin(ids)].tolist() if ids else df.index.tolist()
        df = clasificar_dataframe_reglas(df, indices)
        guardar_alertas(df)
        ids_out = ids or df["id"].tolist()
        return {"ok": True, "clasificadas": len(indices), "filas": _df_a_filas(df[df["id"].isin(ids_out)])}

    @classmethod
    def clasificar_ia(cls, ids: list[int]) -> dict[str, Any]:
        df = cargar_alertas()
        indices = df.index[df["id"].isin(ids)].tolist() if ids else df.index.tolist()
        if not indices:
            return {"ok": True, "clasificadas": 0, "filas": []}
        df = clasificar_dataframe_completo(df, indices)
        guardar_alertas(df)
        ids_out = ids if ids else [int(df.at[i, "id"]) for i in indices]
        return {"ok": True, "clasificadas": len(indices), "filas": _df_a_filas(df[df["id"].isin(ids_out)])}

    @classmethod
    def subir_excel(
        cls,
        content: bytes,
        *,
        modo: str = "reemplazar",
    ) -> dict[str, Any]:
        nuevo = importar_excel_bytes(content)
        if modo == "incremental":
            existente = cargar_alertas()
            ids_antes = set(int(i) for i in existente["id"].tolist())
            df = fusionar_incremental(nuevo, existente)
            ids_nuevos = [int(i) for i in df["id"].tolist() if int(i) not in ids_antes]
            ids_clasificar = ids_nuevos
        else:
            df = nuevo
            ids_nuevos = [int(i) for i in df["id"].tolist()]
            ids_clasificar = ids_nuevos

        guardar_alertas(df)

        return {
            "ok": True,
            "total": len(df),
            "nuevas": len(ids_nuevos),
            "pendientes": contar_pendientes(df),
            "ids_pendientes_ia": ids_clasificar,
        }

    @classmethod
    def exportar_excel(cls, filtros: dict | None = None) -> bytes:
        df = cargar_alertas()
        filtrado = _aplicar_filtros(df, filtros or {})
        return exportar_matriz_seguimiento(filtrado)

    @classmethod
    def recargar_excel(cls) -> dict[str, Any]:
        df = recargar_desde_excel()
        return {"ok": True, "total": len(df), "pendientes": contar_pendientes(df)}

    @classmethod
    def importar_csv(cls, content: bytes) -> dict[str, Any]:
        import io

        nuevo = pd.read_csv(io.BytesIO(content))
        guardar_alertas(nuevo)
        return {"ok": True, "importados": len(nuevo)}

    @classmethod
    def ingresar_alerta(cls, datos: dict) -> dict[str, Any]:
        """Crea una nueva fila de alerta ingresada manualmente y la persiste."""
        df = cargar_alertas()
        nuevo_id = int(df["id"].max() + 1) if len(df) and "id" in df.columns else 1
        nuevo_n = int(df["n"].max() + 1) if len(df) and "n" in df.columns else 1

        # Fecha de alerta: hoy si no se proporciona
        fecha_str = datos.get("fecha_alerta") or ""
        try:
            fecha_parsed = date.fromisoformat(fecha_str) if fecha_str else date.today()
        except ValueError:
            fecha_parsed = date.today()

        mes = datos.get("mes") or fecha_parsed.strftime("%B %Y")

        nueva_fila: dict[str, Any] = {
            "id": nuevo_id,
            "n": nuevo_n,
            "mes": mes,
            "fecha_alerta": pd.Timestamp(fecha_parsed),
            "canal": datos.get("canal") or "Manual",
            "local": datos.get("local") or "",
            "area": datos.get("area") or "",
            "optometra": datos.get("optometra") or "",
            "asesor": datos.get("asesor") or "",
            "momento": datos.get("momento") or "",
            "calificacion": datos.get("calificacion") or "",
            "pregunta": datos.get("pregunta") or "",
            "responde": datos.get("responde") or "",
            "comentario": datos.get("comentario") or "",
            "cliente": datos.get("cliente") or "",
            "cedula_id": datos.get("cedula_id") or "",
            "contacto": datos.get("contacto") or "",
            "correos_disculpa": datos.get("correos_disculpa") or "",
            "llamada_cliente": datos.get("llamada_cliente") or "Pendiente",
            "contesto": datos.get("contesto") or "Pendiente",
            "observacion_gestion": datos.get("observacion_gestion") or "",
            "solucion": datos.get("solucion") or "",
            "quien_llama": datos.get("quien_llama") or "",
            "clasificacion": datos.get("clasificacion") or "",
            "estado_gestion": datos.get("estado_gestion") or "Sin gestión",
            "dialogo_ia": "",
            "canal_dialogo": "",
            "clasificado_por": "",
            "justificacion_ia": "",
            "telefono": datos.get("contacto") or "",
            "mensaje_telegram": datos.get("comentario") or "",
            "problema": datos.get("clasificacion") or "",
            "descripcion": datos.get("comentario") or "",
        }
        nueva_df = pd.DataFrame([nueva_fila])
        df = pd.concat([df, nueva_df], ignore_index=True)
        guardar_alertas(df)
        return {"ok": True, "id": nuevo_id, "n": nuevo_n, "fila": _df_a_filas(nueva_df)[0]}

    @classmethod
    async def generar_reporte_ia(cls, fila: dict, contexto_extra: str = "") -> dict[str, Any]:
        """Genera un reporte completo con Claude sobre una alerta: hallazgos, acciones, desglose."""
        cliente = fila.get("cliente") or "No especificado"
        local = fila.get("local") or "No especificado"
        area = fila.get("area") or "No especificada"
        optometra = fila.get("optometra") or "No especificado"
        asesor = fila.get("asesor") or "No especificado"
        comentario = fila.get("comentario") or fila.get("mensaje_telegram") or ""
        clasificacion = fila.get("clasificacion") or "Sin clasificar"
        estado = fila.get("estado_gestion") or "Sin gestión"
        calificacion = fila.get("calificacion") or ""
        solucion = fila.get("solucion") or ""
        observacion = fila.get("observacion_gestion") or ""
        fecha = fila.get("fecha_alerta") or str(date.today())
        contacto = fila.get("contacto") or fila.get("telefono") or ""
        pregunta = fila.get("pregunta") or ""

        if not settings.anthropic_api_key:
            return {
                "ok": False,
                "error": "API de Claude no configurada. Configure ANTHROPIC_API_KEY en .env",
                "reporte": None,
            }

        prompt = f"""Eres el Director de Calidad y Customer Experience de Óptica Los Andes Ecuador.
Analiza el siguiente caso de alerta operativa y genera un reporte ejecutivo completo.

DATO DEL CASO:
- Fecha: {fecha}
- Local/Tienda: {local}
- Área: {area}
- Optómetra involucrado: {optometra}
- Asesor responsable: {asesor}
- Cliente: {cliente}
- Contacto: {contacto}
- Calificación cliente: {calificacion}
- Pregunta encuesta: {pregunta}
- Comentario del cliente: {comentario}
- Clasificación del problema: {clasificacion}
- Estado actual de gestión: {estado}
- Solución aplicada: {solucion}
- Observación de gestión: {observacion}
- Contexto adicional: {contexto_extra}

Genera un reporte estructurado. Responde SOLO JSON válido:
{{
  "resumen_ejecutivo": "Párrafo de 2-3 oraciones resumiendo el caso",
  "hallazgos": [
    {{"titulo": "...", "descripcion": "...", "severidad": "alta|media|baja"}}
  ],
  "acciones_recomendadas": [
    {{"responsable": "local|optometra|asesor|call_center", "accion": "...", "plazo": "inmediato|24h|esta_semana"}}
  ],
  "analisis_local": "Análisis enfocado en la tienda {local} y qué debe mejorar",
  "analisis_optometra": "Análisis sobre el rol del optómetra {optometra} en este caso",
  "analisis_asesor": "Análisis sobre la gestión del asesor {asesor}",
  "nivel_riesgo": "alto|medio|bajo",
  "requiere_escalamiento": true|false,
  "nota_cxd": "Consejo final del Director CX para cerrar este caso correctamente"
}}"""

        try:
            payload = {
                "model": settings.anthropic_model,
                "max_tokens": 3000,
                "system": (
                    "Eres Director de CX de Óptica Los Andes Ecuador. "
                    "Generas reportes ejecutivos precisos, accionables y en español. "
                    "Solo JSON válido sin markdown."
                ),
                "messages": [{"role": "user", "content": prompt}],
            }
            headers = {
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    f"{settings.anthropic_api_base}/messages",
                    headers=headers,
                    json=payload,
                )
            if resp.status_code != 200:
                raise RuntimeError(resp.text[:300])

            raw_text = resp.json()["content"][0]["text"].strip()
            # Limpiar markdown si Claude lo agrega
            import re
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)
            match = re.search(r"\{[\s\S]*\}", raw_text)
            if not match:
                raise RuntimeError("Sin JSON válido en respuesta")
            reporte = json.loads(match.group())
            return {"ok": True, "reporte": reporte, "generado_por": "claude", "caso": {
                "cliente": cliente, "local": local, "optometra": optometra,
                "asesor": asesor, "clasificacion": clasificacion, "fecha": fecha,
            }}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "reporte": None}