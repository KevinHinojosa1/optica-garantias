"""Botón reutilizable de exportación Excel."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from centro_operaciones.services.exportacion import exportar_tabla_generica


def boton_exportar_excel(
    df: pd.DataFrame,
    *,
    nombre_archivo: str = "export.xlsx",
    titulo_hoja: str = "Datos",
    subtitulo: str = "Centro de Operaciones — Óptica Los Andes",
    key: str = "export_excel",
    label: str = "📥 Exportar Excel",
) -> None:
    if df is None or df.empty:
        st.download_button(
            label=label,
            data=b"",
            file_name=nombre_archivo,
            disabled=True,
            use_container_width=True,
            key=key,
        )
        st.caption("No hay datos para exportar.")
        return

    st.download_button(
        label=label,
        data=exportar_tabla_generica(df, titulo_hoja=titulo_hoja, subtitulo=subtitulo),
        file_name=nombre_archivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
        key=key,
    )