"""Módulo Reclamos Activos — Centro de Operaciones."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from centro_operaciones.components.respuesta_ia import render_panel_respuesta_ia
from services.respuesta_ia_service import RespuestaIAService


def _datos_ejemplo() -> pd.DataFrame:
    return pd.DataFrame([
        {"id": 1, "cliente": "María López", "telefono": "0991112233", "local": "Quito Centro",
         "problema": "Lentes con error de graduación", "estado": "Abierto", "dias_abierto": 5,
         "comentario": "No ve bien con los lentes nuevos", "calificacion": "2/5"},
        {"id": 2, "cliente": "Carlos Ruiz", "telefono": "0982223344", "local": "Cuenca Centro",
         "problema": "Garantía pendiente", "estado": "En revisión", "dias_abierto": 12,
         "comentario": "Esperando respuesta del laboratorio", "calificacion": "1/5"},
        {"id": 3, "cliente": "Ana Torres", "telefono": "0973334455", "local": "Guayaquil Norte",
         "problema": "Devolución solicitada", "estado": "Abierto", "dias_abierto": 3,
         "comentario": "Quiere devolver la montura", "calificacion": "2/5"},
    ])


def render() -> None:
    st.subheader("📋 Reclamos Activos")
    df = _datos_ejemplo()
    st.dataframe(df, use_container_width=True, hide_index=True)

    sel = st.selectbox("Seleccionar caso para IA", df["id"].tolist(), format_func=lambda i: f"#{i} — {df.loc[df['id']==i,'cliente'].iloc[0]}")
    fila = df[df["id"] == sel].iloc[0].to_dict()

    ctx = RespuestaIAService.contexto_desde_fila(
        {**fila, "descripcion": fila.get("comentario", ""), "estado_gestion": fila.get("estado", "")},
        modulo="reclamos_activos",
    )
    ctx["historial"] = f"Días abierto: {fila.get('dias_abierto', '')}"
    ctx["calificacion"] = fila.get("calificacion", "")

    render_panel_respuesta_ia(ctx, titulo_modulo="Reclamos Activos", key_prefix="reclamos")