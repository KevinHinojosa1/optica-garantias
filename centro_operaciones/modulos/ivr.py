"""Módulo 1800 / IVR — verificaciones por tienda."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from centro_operaciones.components.export_excel import boton_exportar_excel
from centro_operaciones.components.layout import render_header, render_kpis
from centro_operaciones.components.respuesta_ia import render_panel_desde_fila

FASTAPI_BASE = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")


def _datos_ejemplo() -> pd.DataFrame:
    return pd.DataFrame([
        {"id": 1, "tienda": "Quito Centro", "semana": "2026-W27", "funciona": "Sí",
         "comentario": "Funciona bien IVR", "verificado_por": "Call Center"},
        {"id": 2, "tienda": "Cuenca Norte", "semana": "2026-W27", "funciona": "No",
         "comentario": "No funciona IVR", "verificado_por": "Supervisor"},
        {"id": 3, "tienda": "Guayaquil Mall", "semana": "2026-W27", "funciona": "Sí",
         "comentario": "Funciona bien, no contesta", "verificado_por": "Auditoría"},
    ])


def render() -> None:
    render_header(
        "📞 1800 / IVR",
        "Verificaciones de línea 1800 e IVR por tienda",
    )

    c1, c2 = st.columns([3, 1])
    with c2:
        st.link_button("Abrir módulo IVR (FastAPI)", f"{FASTAPI_BASE}/ivr", use_container_width=True)

    df = _datos_ejemplo()
    render_kpis([
        ("Verificaciones", len(df)),
        ("Funcionan", (df["funciona"] == "Sí").sum()),
        ("Con falla", (df["funciona"] == "No").sum()),
    ])

    st.dataframe(df, use_container_width=True, hide_index=True)
    boton_exportar_excel(df, nombre_archivo="ivr_verificaciones.xlsx", key="export_ivr")

    st.divider()
    sel = st.selectbox(
        "Caso IVR para IA",
        df["id"].tolist(),
        format_func=lambda i: f"{df.loc[df['id']==i,'tienda'].iloc[0]} — {df.loc[df['id']==i,'funciona'].iloc[0]}",
        key="ivr_sel",
    )
    fila = df[df["id"] == sel].iloc[0].to_dict()
    render_panel_desde_fila(
        {
            "id": fila["id"],
            "cliente": "Equipo tienda",
            "local": fila["tienda"],
            "problema": f"IVR {fila['funciona']}",
            "descripcion": fila["comentario"],
            "estado_gestion": fila["funciona"],
        },
        "ivr",
        titulo_modulo="1800 / IVR",
        key_prefix="ivr",
    )