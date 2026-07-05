"""Servicio Alertas Telegram — integración FastAPI del módulo centro_operaciones."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

import pandas as pd

from centro_operaciones.constants import (
    AREAS,
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
)
from centro_operaciones.services.exportacion import exportar_matriz_seguimiento
from centro_operaciones.services.graficos import (
    donut_estado,
    heatmap_local_area,
    tendencia_mensual,
    top_problemas,
)


def _fig_a_dict(fig) -> dict[str, Any]:
    return json.loads(fig.to_json())


def _df_a_filas(df: pd.DataFrame) -> list[dict[str, Any]]:
    out = df.copy()
    if "fecha_alerta" in out.columns:
        out["fecha_alerta"] = pd.to_datetime(out["fecha_alerta"], errors="coerce").dt.strftime("%d/%m/%Y %H:%M")
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
        if pd.notna(max_f):
            fecha_hasta = max_f.date() if hasattr(max_f, "date") else date.today()
        else:
            fecha_hasta = date.today()
    if not fecha_desde:
        min_f = df["fecha_alerta"].min()
        if pd.notna(min_f):
            fecha_desde = min_f.date() if hasattr(min_f, "date") else date.today() - timedelta(days=30)
        else:
            fecha_desde = date.today() - timedelta(days=30)

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
    )
    if filtros.get("solo_pendientes"):
        filtrado = filtrado[
            (filtrado["estado_gestion"] == "Sin gestión")
            | (filtrado["solucion"].fillna("").astype(str).str.strip() == "")
        ]
    return filtrado


class AlertasService:
    @staticmethod
    def metadata() -> dict[str, Any]:
        df = cargar_alertas()
        min_f = df["fecha_alerta"].min()
        max_f = df["fecha_alerta"].max()
        return {
            "opciones_llamada": OPCIONES_LLAMADA,
            "opciones_contesto": OPCIONES_CONTESTO,
            "opciones_estado": OPCIONES_ESTADO,
            "opciones_clasificacion": OPCIONES_CLASIFICACION,
            "areas": AREAS,
            "locales": sorted(df["local"].dropna().unique().tolist()),
            "fecha_min": min_f.date().isoformat() if pd.notna(min_f) and hasattr(min_f, "date") else None,
            "fecha_max": max_f.date().isoformat() if pd.notna(max_f) and hasattr(max_f, "date") else None,
            "total_casos": len(df),
            "pendientes": contar_pendientes(df),
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
            "sin_gestion": int((filtrado["estado_gestion"] == "Sin gestión").sum()),
            "resueltos": int((filtrado["estado_gestion"] == "Resuelto").sum()),
            "contesto_si": int((filtrado["contesto"] == "Sí").sum()),
            "pendientes": contar_pendientes(filtrado),
        }

    @classmethod
    def graficos(cls, filtros: dict | None = None) -> dict[str, Any]:
        df = cargar_alertas()
        filtrado = _aplicar_filtros(df, filtros or {})
        return {
            "tendencia": _fig_a_dict(tendencia_mensual(filtrado)),
            "top_problemas": _fig_a_dict(top_problemas(filtrado)),
            "heatmap": _fig_a_dict(heatmap_local_area(filtrado)),
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
                if col in df.columns and col != "id":
                    df.loc[mask, col] = row[col]
            actualizados += 1
        guardar_alertas(df)
        return {"ok": True, "actualizados": actualizados}

    @classmethod
    def clasificar_reglas(cls, ids: list[int]) -> dict[str, Any]:
        df = cargar_alertas()
        if not ids:
            ids = df["id"].tolist()
        indices = df.index[df["id"].isin(ids)].tolist()
        df = clasificar_dataframe_reglas(df, indices)
        guardar_alertas(df)
        actualizadas = df[df["id"].isin(ids)]
        return {"ok": True, "clasificadas": len(indices), "filas": _df_a_filas(actualizadas)}

    @classmethod
    def clasificar_ia(cls, ids: list[int]) -> dict[str, Any]:
        df = cargar_alertas()
        if not ids:
            ids = df["id"].tolist()
        indices = df.index[df["id"].isin(ids)].tolist()
        if not indices:
            return {"ok": True, "clasificadas": 0, "filas": []}
        df = clasificar_dataframe_ia_sync(df, indices)
        guardar_alertas(df)
        actualizadas = df[df["id"].isin(ids)]
        return {"ok": True, "clasificadas": len(indices), "filas": _df_a_filas(actualizadas)}

    @classmethod
    def exportar_excel(cls, filtros: dict | None = None) -> bytes:
        df = cargar_alertas()
        filtrado = _aplicar_filtros(df, filtros or {})
        return exportar_matriz_seguimiento(filtrado)

    @classmethod
    def importar_csv(cls, content: bytes) -> dict[str, Any]:
        import io

        nuevo = pd.read_csv(io.BytesIO(content))
        guardar_alertas(nuevo)
        return {"ok": True, "importados": len(nuevo)}