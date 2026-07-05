"""
Centro de Operaciones Óptica Los Andes — Hub multi-módulo
Ejecutar: streamlit run centro_operaciones/hub.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from centro_operaciones.modulos.alertas_telegram_page import render as render_alertas  # noqa: E402
from centro_operaciones.modulos.reclamos_activos import render as render_reclamos  # noqa: E402
from centro_operaciones.modulos.whatsapp_cola import render as render_whatsapp  # noqa: E402
from services.respuesta_ia_service import RespuestaIAService  # noqa: E402

try:
    from config import settings
except ImportError:
    settings = None

st.set_page_config(
    page_title="Centro de Operaciones — Óptica Los Andes",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .pendiente-badge { background:#fef3c7;color:#92400e;padding:8px 14px;border-radius:10px;font-weight:700; }
    .kpi-card { background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:14px;text-align:center; }
    div[data-testid="stSidebar"] { background:#f1f5f9; }
    </style>
    """,
    unsafe_allow_html=True,
)


def sidebar_hub() -> str:
    st.sidebar.title("🏢 Centro de Operaciones")
    st.sidebar.caption("Óptica Los Andes")

    estado = RespuestaIAService.ia_disponible()
    if estado["disponible"]:
        st.sidebar.success(f"🤖 Claude · {estado['modelo']}")
    else:
        st.sidebar.warning("⚠️ Claude no configurado")

    st.sidebar.divider()
    modulo = st.sidebar.radio(
        "Módulo",
        [
            "📡 Alertas Telegram",
            "📋 Reclamos Activos",
            "💬 Cola WhatsApp",
        ],
        key="modulo_activo",
    )
    st.sidebar.divider()
    st.sidebar.markdown(
        "**IA reutilizable** en cada módulo:\n"
        "- ✨ Generar Diálogo con Claude\n"
        "- 💡 Sugerir Respuesta IA\n"
        "- 📋 Copiar · 💬 WhatsApp · 💾 Plantilla"
    )
    return modulo


def main() -> None:
    modulo = sidebar_hub()
    st.title("Centro de Operaciones — Óptica Los Andes")

    if modulo.startswith("📡"):
        render_alertas()
    elif modulo.startswith("📋"):
        render_reclamos()
    elif modulo.startswith("💬"):
        render_whatsapp()


if __name__ == "__main__":
    main()