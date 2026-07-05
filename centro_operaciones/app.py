"""
Centro de Operaciones Óptica Los Andes — aplicación principal Streamlit.

Ejecutar:
    streamlit run centro_operaciones/app.py

Módulos (sidebar):
    Garantías · Alertas Telegram · Reclamos Activos · LeadBox ·
    WhatsApp Business · 1800/IVR · Códigos de Descuento ·
    Protección de Datos · Reportes y Matrices
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from centro_operaciones.registry import labels_sidebar, modulo_por_label  # noqa: E402
from centro_operaciones.theme.corporate import inject_corporate_css  # noqa: E402
from centro_operaciones.components.layout import sidebar_ayuda_ia, sidebar_estado_ia  # noqa: E402
from services.respuesta_ia_service import RespuestaIAService  # noqa: E402

APP_VERSION = "1.0.0"


def configurar_pagina() -> None:
    st.set_page_config(
        page_title="Centro de Operaciones — Óptica Los Andes",
        page_icon="🏢",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_corporate_css()


def render_sidebar() -> str:
    st.sidebar.markdown(
        """
        <div style="padding:0.5rem 0 1rem;">
            <span style="font-size:1.15rem;font-weight:800;color:#1E3A5F;">
                Centro de Operaciones
            </span><br>
            <span style="font-size:0.85rem;color:#64748b;">Óptica Los Andes</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    estado_ia = RespuestaIAService.ia_disponible()
    sidebar_estado_ia(estado_ia)

    st.sidebar.divider()
    opciones = labels_sidebar()
    modulo_label = st.sidebar.radio(
        "Módulo",
        opciones,
        key="modulo_activo",
        label_visibility="collapsed",
    )

    sidebar_ayuda_ia()
    st.sidebar.caption(f"v{APP_VERSION}")

    return modulo_label


def main() -> None:
    configurar_pagina()
    modulo_label = render_sidebar()

    entrada = modulo_por_label(modulo_label)
    if entrada is None:
        st.error("Módulo no encontrado en el registro.")
        return

    entrada.render()


if __name__ == "__main__":
    main()