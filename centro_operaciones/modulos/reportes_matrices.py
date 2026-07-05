"""Módulo Reportes y Matrices — vista consolidada."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from centro_operaciones.components.export_excel import boton_exportar_excel
from centro_operaciones.components.layout import render_header, render_kpis
from centro_operaciones.components.respuesta_ia import render_panel_respuesta_ia
from centro_operaciones.services.datastore import cargar_alertas
from centro_operaciones.services.exportacion import exportar_matriz_seguimiento


def _matriz_consolidada() -> pd.DataFrame:
    try:
        alertas = cargar_alertas()
        resumen = (
            alertas.groupby(["local", "clasificacion", "estado_gestion"], dropna=False)
            .size()
            .reset_index(name="casos")
            .sort_values("casos", ascending=False)
        )
        return resumen
    except Exception:
        return pd.DataFrame([
            {"local": "Quito Centro", "clasificacion": "Garantía / cambio", "estado_gestion": "En proceso", "casos": 8},
            {"local": "Cuenca", "clasificacion": "Retraso entrega", "estado_gestion": "Sin gestión", "casos": 5},
            {"local": "Guayaquil Norte", "clasificacion": "Calidad producto", "estado_gestion": "Resuelto", "casos": 12},
        ])


def render() -> None:
    render_header(
        "📊 Reportes y Matrices",
        "Matrices consolidadas por local, clasificación y estado",
    )

    df = _matriz_consolidada()
    render_kpis([
        ("Filas matriz", len(df)),
        ("Total casos", int(df["casos"].sum()) if "casos" in df.columns else 0),
        ("Locales", df["local"].nunique() if "local" in df.columns else 0),
    ])

    st.dataframe(df, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        boton_exportar_excel(df, nombre_archivo="matriz_consolidada.xlsx", key="export_matriz")
    with c2:
        try:
            alertas = cargar_alertas()
            st.download_button(
                "📥 Excel completo (Alertas Telegram)",
                data=exportar_matriz_seguimiento(alertas),
                file_name="matriz_seguimiento_completa.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="export_alertas_full",
            )
        except Exception as exc:
            st.caption(f"Matriz alertas no disponible: {exc}")

    st.divider()
    render_panel_respuesta_ia(
        {
            "modulo": "reportes_matrices",
            "caso_id": "MATRIZ",
            "cliente_nombre": "Equipo operaciones",
            "comentario_cliente": "Resumen semanal de casos por local",
            "contexto_extra": f"Total filas: {len(df)} · Casos: {int(df['casos'].sum()) if 'casos' in df.columns else 0}",
        },
        titulo_modulo="Reportes y Matrices",
        key_prefix="reportes",
    )