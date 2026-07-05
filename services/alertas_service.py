"""Servicio Alertas Telegram — integración FastAPI del módulo centro_operaciones."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

import pandas as pd

from centro_operaciones.constants import (
    AREAS,
    COLUMNAS_EDITABLES,
    COLUMNAS_EXCEL_EXPORTE,
    OPCIONES_CLASIFICACION,
    OPCIONES_CONTESTO,
    OPCIONES_ESTADO,
    OPCIONES_LLAMADA,
)
from centro_operaciones.services.clasificacion import (
    clasificar_dataframe_ia_sync,
    clasificar_dataframe_reglas,
)
from centro_operaciones.services.datastore import (
    cargar_alertas,
    contar_pendientes,
    filtrar_df,
    guardar_alertas,
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
        df = clasificar_dataframe_ia_sync(df, indices)
        guardar_alertas(df)
        ids_out = ids or df["id"].tolist()
        return {"ok": True, "clasificadas": len(indices), "filas": _df_a_filas(df[df["id"].isin(ids_out)])}

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