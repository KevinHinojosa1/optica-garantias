"""
Alertas Telegram — Matriz de Seguimiento (Streamlit)
Hoja GENERAL de ALERTAS TELEGRAM 2026.xlsx
Ejecutar: streamlit run centro_operaciones/app.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from centro_operaciones.constants import (
    COLUMNAS_EDITABLES,
    COLUMNAS_EXCEL_EXPORTE,
    OPCIONES_CLASIFICACION,
    OPCIONES_CONTESTO,
    OPCIONES_ESTADO,
    OPCIONES_LLAMADA,
)
from centro_operaciones.services.clasificacion import (
    clasificar_dataframe_ia_sync,
    clasificar_dataframe_reglas,
)
from centro_operaciones.services.datastore import (
    cargar_alertas,
    contar_pendientes,
    filtrar_df,
    guardar_alertas,
    recargar_desde_excel,
)
from centro_operaciones.components.respuesta_ia import render_panel_desde_fila
from centro_operaciones.services.exportacion import exportar_matriz_seguimiento
from centro_operaciones.services.graficos import (
    donut_estado,
    heatmap_local_clasificacion,
    heatmap_mes_local,
    tendencia_mensual,
    top_problemas,
)
from services.respuesta_ia_service import RespuestaIAService


def init_state() -> None:
    if "df_alertas" not in st.session_state:
        st.session_state.df_alertas = cargar_alertas()


def sincronizar_grid(df_base: pd.DataFrame, df_grid: pd.DataFrame) -> pd.DataFrame:
    if df_grid is None or df_grid.empty:
        return df_base
    out = df_base.copy()
    if "id" not in df_grid.columns:
        return out
    for _, row in df_grid.iterrows():
        rid = int(row["id"])
        mask = out["id"] == rid
        if not mask.any():
            continue
        for col in COLUMNAS_EDITABLES:
            if col in row.index and col in out.columns:
                out.loc[mask, col] = row[col]
    return out


def construir_grid(df: pd.DataFrame):
    display = df.copy()
    display["fecha_alerta"] = pd.to_datetime(display["fecha_alerta"], errors="coerce").dt.strftime("%d/%m/%Y")

    cols_show = [c for c, _ in COLUMNAS_EXCEL_EXPORTE if c in display.columns]
    display = display[cols_show + [c for c in ("dialogo_ia", "clasificado_por") if c in display.columns]]

    gb = GridOptionsBuilder.from_dataframe(display)
    gb.configure_default_column(filterable=True, sortable=True, resizable=True, wrapText=True, autoHeight=True)
    gb.configure_column("n", width=60, pinned="left")
    gb.configure_column("fecha_alerta", width=100, pinned="left")
    gb.configure_column("local", width=140, pinned="left")
    gb.configure_column("comentario", wrapText=True, autoHeight=True, width=240)
    gb.configure_column("observacion_gestion", editable=True, wrapText=True, autoHeight=True, width=260)
    gb.configure_column("solucion", editable=True, wrapText=True, autoHeight=True, width=220)
    for col, opts in [
        ("llamada_cliente", OPCIONES_LLAMADA),
        ("contesto", OPCIONES_CONTESTO),
        ("clasificacion", OPCIONES_CLASIFICACION),
        ("estado_gestion", OPCIONES_ESTADO),
    ]:
        if col in display.columns:
            gb.configure_column(col, editable=True, cellEditor="agSelectCellEditor", cellEditorParams={"values": opts})
    for col in ("asesor", "quien_llama", "correos_disculpa"):
        if col in display.columns:
            gb.configure_column(col, editable=True)
    gb.configure_selection("multiple", use_checkbox=True)
    return AgGrid(
        display,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.VALUE_CHANGED | GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        height=520,
        theme="streamlit",
        key="grid_alertas_general",
    )


def sidebar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.subheader("Filtros — Alertas Telegram")
    pendientes = contar_pendientes(df)
    st.sidebar.markdown(
        f'<p class="pendiente-badge">⏳ Pendientes sin gestión: <b>{pendientes}</b></p>',
        unsafe_allow_html=True,
    )

    min_f, max_f = df["fecha_alerta"].min(), df["fecha_alerta"].max()
    if pd.isna(min_f):
        min_f = pd.Timestamp.today()
    if pd.isna(max_f):
        max_f = pd.Timestamp.today()

    fecha_desde = st.sidebar.date_input("Desde", value=min_f.date() if hasattr(min_f, "date") else date.today() - timedelta(days=90))
    fecha_hasta = st.sidebar.date_input("Hasta", value=max_f.date() if hasattr(max_f, "date") else date.today())
    meses = st.sidebar.multiselect("Mes", sorted(df["mes"].replace("", pd.NA).dropna().unique()))
    locales = st.sidebar.multiselect("Local", sorted(df["local"].dropna().unique()))
    areas = st.sidebar.multiselect("Área", sorted(df["area"].replace("", pd.NA).dropna().unique()))
    clasif = st.sidebar.multiselect("Clasificación", OPCIONES_CLASIFICACION)
    estados = st.sidebar.multiselect("Estado gestión", OPCIONES_ESTADO)
    contesto = st.sidebar.multiselect("Contestó", OPCIONES_CONTESTO)
    texto = st.sidebar.text_input("Buscar texto")
    solo_pend = st.sidebar.checkbox("Solo pendientes sin gestión", value=False)

    filtrado = filtrar_df(
        df, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        locales=locales, areas=areas, clasificaciones=clasif,
        estados=estados, contesto=contesto, texto=texto, meses=meses,
    )
    if solo_pend:
        sin_sol = filtrado["solucion"].fillna("").astype(str).str.strip() == ""
        sin_obs = filtrado["observacion_gestion"].fillna("").astype(str).str.strip() == ""
        filtrado = filtrado[sin_sol & sin_obs]
    st.sidebar.caption(f"Mostrando **{len(filtrado)}** de **{len(df)}** casos")
    return filtrado


def render() -> None:
    init_state()
    df = st.session_state.df_alertas
    filtrado = sidebar_filtros(df)

    estado_ia = RespuestaIAService.ia_disponible()
    c0, c1 = st.columns([3, 1])
    with c0:
        st.subheader("📡 Alertas Telegram — Matriz GENERAL")
        st.caption("ALERTAS TELEGRAM 2026.xlsx · Seguimiento diario por local")
    with c1:
        if estado_ia["disponible"]:
            st.success(f"🤖 Claude · {estado_ia['modelo']}")
        else:
            st.warning("Claude no configurado")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total filtrado", len(filtrado))
    k2.metric("Sin gestión", int(filtrado["estado_gestion"].isin(["Sin gestión", "Pendiente llamada", ""]).sum()))
    k3.metric("Resueltos", int((filtrado["estado_gestion"] == "Resuelto").sum()))
    k4.metric("Contestó Sí", int(filtrado["contesto"].isin(["Sí", "si", "SI", "Si"]).sum()))

    g1, g2 = st.columns(2)
    g1.plotly_chart(tendencia_mensual(filtrado), use_container_width=True)
    g2.plotly_chart(top_problemas(filtrado), use_container_width=True)
    g3, g4 = st.columns(2)
    g3.plotly_chart(heatmap_local_clasificacion(filtrado), use_container_width=True)
    g4.plotly_chart(heatmap_mes_local(filtrado), use_container_width=True)
    st.plotly_chart(donut_estado(filtrado), use_container_width=True)

    st.divider()
    st.subheader("📋 Matriz editable — hoja GENERAL")

    acc1, acc2, acc3, acc4, acc5 = st.columns(5)
    grid_resp = construir_grid(filtrado)
    st.session_state.df_alertas = sincronizar_grid(st.session_state.df_alertas, pd.DataFrame(grid_resp["data"]))

    sel = grid_resp.get("selected_rows")
    ids_sel = []
    if isinstance(sel, pd.DataFrame) and not sel.empty and "id" in sel.columns:
        ids_sel = sel["id"].tolist()
    elif isinstance(sel, list) and sel:
        ids_sel = [r.get("id") for r in sel if isinstance(r, dict)]

    with acc1:
        if st.button("💾 Actualizar / Guardar", type="primary", use_container_width=True):
            guardar_alertas(st.session_state.df_alertas)
            st.success("Cambios guardados.")
            st.rerun()
    with acc2:
        if st.button("🏷️ Clasificar reglas", use_container_width=True):
            idx = st.session_state.df_alertas.index[st.session_state.df_alertas["id"].isin(ids_sel)].tolist() if ids_sel else filtrado.index.tolist()
            st.session_state.df_alertas = clasificar_dataframe_reglas(st.session_state.df_alertas, idx)
            guardar_alertas(st.session_state.df_alertas)
            st.rerun()
    with acc3:
        if st.button("🤖 Clasificar IA", use_container_width=True):
            idx = st.session_state.df_alertas.index[st.session_state.df_alertas["id"].isin(ids_sel)].tolist() if ids_sel else filtrado.index.tolist()
            with st.spinner("Clasificando..."):
                st.session_state.df_alertas = clasificar_dataframe_ia_sync(st.session_state.df_alertas, idx)
            guardar_alertas(st.session_state.df_alertas)
            st.rerun()
    with acc4:
        if st.button("🔄 Recargar Excel", use_container_width=True):
            st.session_state.df_alertas = recargar_desde_excel()
            st.rerun()
    with acc5:
        st.download_button(
            "📥 Exportar Excel",
            data=exportar_matriz_seguimiento(filtrado),
            file_name="matriz_alertas_telegram.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.divider()
    if ids_sel:
        fila = st.session_state.df_alertas[st.session_state.df_alertas["id"] == ids_sel[0]].iloc[0].to_dict()
        st.caption(f"IA para caso **#{fila.get('n')}** — {fila.get('cliente')}")
        render_panel_desde_fila(fila, "alertas_telegram", titulo_modulo="Alertas Telegram", key_prefix=f"alertas_{fila.get('id')}")
    else:
        st.info("Seleccione una fila para **Generar sugerencia con Claude**.")