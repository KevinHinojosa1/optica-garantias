"""Componentes de layout reutilizables — header, KPIs, toolbar."""

from __future__ import annotations

import streamlit as st

from centro_operaciones.theme.corporate import COLORS


def render_header(titulo: str, subtitulo: str = "") -> None:
    sub = f"<p>{subtitulo}</p>" if subtitulo else ""
    st.markdown(
        f"""
        <div class="ola-header">
            <h1>{titulo}</h1>
            {sub}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(items: list[tuple[str, str | int]]) -> None:
    """Renderiza fila de KPIs. items = [(label, value), ...]"""
    if not items:
        return
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.markdown(
            f"""
            <div class="ola-kpi">
                <div class="label">{label}</div>
                <div class="value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_toolbar(
    *,
    titulo: str = "Acciones",
    mostrar_divider: bool = True,
) -> None:
    if mostrar_divider:
        st.divider()
    st.markdown(f"##### {titulo}")


def sidebar_estado_ia(estado: dict) -> None:
    if estado.get("disponible"):
        st.sidebar.success(f"🤖 Claude · {estado.get('modelo', 'activo')}")
    else:
        st.sidebar.warning("⚠️ Claude no configurado — plantillas CX")


def sidebar_ayuda_ia() -> None:
    st.sidebar.divider()
    st.sidebar.markdown(
        f"""
        **Herramientas IA** (cada módulo):
        - ✨ Generar Diálogo con Claude
        - 💡 Sugerir Respuesta IA
        - 📋 Copiar · 💬 WhatsApp · 💾 Plantilla

        <span style="color:{COLORS['text_muted']};font-size:0.85rem;">
        Exportación Excel disponible en todos los módulos.
        </span>
        """,
        unsafe_allow_html=True,
    )