"""Módulo Códigos de Descuento."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from centro_operaciones.components.export_excel import boton_exportar_excel
from centro_operaciones.components.layout import render_header, render_kpis
from centro_operaciones.components.respuesta_ia import render_panel_respuesta_ia
from services.descuento_service import CODIGOS_VALIDOS, DescuentoService


def _historial_ejemplo() -> pd.DataFrame:
    return pd.DataFrame([
        {"id": 1, "cliente": "Rosa Méndez", "local": "Quito Sur", "codigo": 20, "aplicado": 15, "asesor": "Ana P."},
        {"id": 2, "cliente": "Diego Morales", "local": "Ambato", "codigo": 30, "aplicado": 30, "asesor": "Luis R."},
        {"id": 3, "cliente": "Elena Vásquez", "local": "Manta", "codigo": 10, "aplicado": 10, "asesor": "Carla M."},
    ])


def render() -> None:
    render_header(
        "🏷️ Códigos de Descuento",
        f"Códigos autorizados: {CODIGOS_VALIDOS}",
    )

    with st.form("form_descuento", border=True):
        c1, c2, c3 = st.columns(3)
        codigo = c1.selectbox("Código autorizado (%)", [None, *CODIGOS_VALIDOS], format_func=lambda x: "—" if x is None else f"{x}%")
        aplicado = c2.number_input("Porcentaje aplicado (%)", min_value=0, max_value=50, value=0)
        cliente = c3.text_input("Cliente")
        if st.form_submit_button("Validar código", type="primary"):
            try:
                c, p = DescuentoService.validar(
                    codigo if codigo is not None else None,
                    aplicado if aplicado > 0 else None,
                )
                st.success(DescuentoService.texto_reporte(c, p))
            except ValueError as exc:
                st.error(str(exc))

    df = _historial_ejemplo()
    render_kpis([
        ("Registros", len(df)),
        ("Prom. aplicado", f"{df['aplicado'].mean():.0f}%"),
        ("Códigos usados", df["codigo"].nunique()),
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
    boton_exportar_excel(df, nombre_archivo="codigos_descuento.xlsx", key="export_desc")

    st.divider()
    sel = st.selectbox("Caso para comunicar descuento", df["id"].tolist(), key="desc_sel")
    fila = df[df["id"] == sel].iloc[0].to_dict()
    render_panel_respuesta_ia(
        {
            "modulo": "codigos_descuento",
            "caso_id": str(fila["id"]),
            "cliente_nombre": fila["cliente"],
            "local": fila["local"],
            "comentario_cliente": f"Solicitud descuento {fila['codigo']}%",
            "contexto_extra": DescuentoService.texto_reporte(fila["codigo"], fila["aplicado"]),
        },
        titulo_modulo="Códigos de Descuento",
        key_prefix="descuentos",
    )