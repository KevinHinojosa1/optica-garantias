"""Módulo Garantías — enlace a la app FastAPI existente."""

from __future__ import annotations

import os

import streamlit as st
import streamlit.components.v1 as components

from centro_operaciones.components.layout import render_header
from centro_operaciones.components.respuesta_ia import render_panel_respuesta_ia
from services.respuesta_ia_service import RespuestaIAService

FASTAPI_BASE = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")

RUTAS_GARANTIAS = [
    ("Importar base", "/importar", "Carga de pacientes y base de datos"),
    ("Clientes", "/clientes", "Búsqueda y gestión de casos"),
    ("Historial", "/historial", "Historial de gestiones"),
    ("Análisis", "/analisis", "Dashboards y métricas"),
    ("Mensajes", "/mensajes", "Plantillas de comunicación"),
    ("Scripts CX", "/scripts", "Escenarios de atención al cliente"),
    ("Tiendas", "/tiendas", "Catálogo de locales"),
]


def render() -> None:
    render_header(
        "🛡️ Garantías",
        "Sistema de gestión de garantías — funcionalidad FastAPI actual",
    )

    st.markdown(
        f"""
        La aplicación principal de garantías corre en **FastAPI** ({FASTAPI_BASE}).
        Use los accesos directos o el visor embebido.
        """
    )

    cols = st.columns(3)
    for i, (nombre, ruta, desc) in enumerate(RUTAS_GARANTIAS):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div class="ola-modulo-card">
                    <h3>{nombre}</h3>
                    <p style="color:#64748b;font-size:0.85rem;margin:0;">{desc}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.link_button(f"Abrir {nombre}", f"{FASTAPI_BASE}{ruta}", use_container_width=True)

    st.divider()
    vista = st.radio("Vista", ["Accesos rápidos", "Visor embebido (Clientes)"], horizontal=True)
    if vista.startswith("Visor"):
        components.iframe(f"{FASTAPI_BASE}/clientes", height=720, scrolling=True)

    st.divider()
    st.markdown("#### 🤖 Generar Diálogo — Caso de garantía")
    ctx_demo = RespuestaIAService.contexto_desde_fila(
        {
            "id": "GAR-001",
            "cliente": "{cliente}",
            "telefono": "{telefono}",
            "local": "{local}",
            "problema": "Garantía por adaptación visual",
            "descripcion": "Cliente reporta mareos con lentes progresivos",
            "estado_gestion": "En proceso",
        },
        modulo="garantias",
    )
    render_panel_respuesta_ia(ctx_demo, titulo_modulo="Garantías", key_prefix="garantias")