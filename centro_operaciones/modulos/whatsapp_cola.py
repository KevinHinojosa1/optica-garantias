"""Módulo Cola WhatsApp — Centro de Operaciones."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from centro_operaciones.components.respuesta_ia import render_panel_respuesta_ia
from services.respuesta_ia_service import RespuestaIAService


def _datos_ejemplo() -> pd.DataFrame:
    return pd.DataFrame([
        {"id": 101, "cliente": "Pedro Vega", "telefono": "0994445566", "local": "Ambato",
         "mensaje": "¿Cuándo llegan mis lentes?", "espera_min": 45, "prioridad": "Alta"},
        {"id": 102, "cliente": "Lucía Mendoza", "telefono": "0985556677", "local": "Riobamba",
         "mensaje": "Necesito factura de mi compra", "espera_min": 20, "prioridad": "Media"},
        {"id": 103, "cliente": "Jorge Salinas", "telefono": "0976667788", "local": "Manta",
         "mensaje": "Mis gafas llegaron rayadas", "espera_min": 90, "prioridad": "Alta"},
    ])


def render() -> None:
    st.subheader("💬 Cola WhatsApp")
    df = _datos_ejemplo()
    st.dataframe(df, use_container_width=True, hide_index=True)

    sel = st.selectbox(
        "Mensaje a responder con IA",
        df["id"].tolist(),
        format_func=lambda i: f"#{i} — {df.loc[df['id']==i,'cliente'].iloc[0]}",
        key="wa_sel",
    )
    fila = df[df["id"] == sel].iloc[0].to_dict()

    ctx = RespuestaIAService.contexto_desde_fila(
        {
            "id": fila["id"],
            "cliente": fila["cliente"],
            "telefono": fila["telefono"],
            "local": fila["local"],
            "comentario_cliente": fila["mensaje"],
            "problema": fila["mensaje"],
            "descripcion": f"Espera: {fila['espera_min']} min · Prioridad: {fila['prioridad']}",
        },
        modulo="whatsapp",
    )

    render_panel_respuesta_ia(ctx, titulo_modulo="Cola WhatsApp", key_prefix="whatsapp")