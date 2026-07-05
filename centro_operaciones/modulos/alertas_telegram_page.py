"""
Centro de Operaciones Óptica Los Andes — Alertas Telegram
Ejecutar: streamlit run centro_operaciones/app.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from centro_operaciones.constants import (  # noqa: E402
    COLUMNAS_EDITABLES,
    OPCIONES_CLASIFICACION,
    OPCIONES_CONTESTO,
    OPCIONES_ESTADO,
    OPCIONES_LLAMADA,
)
from centro_operaciones.services.clasificacion import (  # noqa: E402
    clasificar_dataframe_ia_sync,
    clasificar_dataframe_reglas,
)
from centro_operaciones.services.datastore import (  # noqa: E402
    cargar_alertas,
    contar_pendientes,
    filtrar_df,
    guardar_alertas,
)
from centro_operaciones.components.respuesta_ia import render_panel_desde_fila  # noqa: E402
from services.respuesta_ia_service import RespuestaIAService  # noqa: E402
from centro_operaciones.services.exportacion import exportar_matriz_seguimiento  # noqa: E402
from centro_operaciones.services.graficos import (  # noqa: E402
    donut_estado,
    heatmap_local_area,
    tendencia_mensual,
    top_problemas,
)

try:
    from config import settings as app_settings
except ImportError:
    app_settings = None

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
        for col in COLUMNAS_EDITABLES + ["dialogo_ia", "canal_dialogo"]:
            if col in row.index and col in out.columns:
                out.loc[mask, col] = row[col]
    return out


def construir_grid(df: pd.DataFrame):
    display = df.copy()
    display["fecha_alerta"] = pd.to_datetime(display["fecha_alerta"], errors="coerce").dt.strftime("%d/%m/%Y %H:%M")

    gb = GridOptionsBuilder.from_dataframe(display)
    gb.configure_default_column(filterable=True, sortable=True, resizable=True, wrapText=True, autoHeight=True)
    gb.configure_column("id", width=70, pinned="left")
    gb.configure_column("dialogo_ia", editable=False, wrapText=True, autoHeight=True, width=280)
    gb.configure_column("mensaje_telegram", wrapText=True, autoHeight=True, width=200)
    gb.configure_column(
        "llamada_cliente", editable=True,
        cellEditor="agSelectCellEditor", cellEditorParams={"values": OPCIONES_LLAMADA},
    )
    gb.configure_column(
        "contesto", editable=True,
        cellEditor="agSelectCellEditor", cellEditorParams={"values": OPCIONES_CONTESTO},
    )
    gb.configure_column(
        "clasificacion", editable=True,
        cellEditor="agSelectCellEditor", cellEditorParams={"values": OPCIONES_CLASIFICACION},
    )
    gb.configure_column(
        "estado_gestion", editable=True,
        cellEditor="agSelectCellEditor", cellEditorParams={"values": OPCIONES_ESTADO},
    )
    gb.configure_column("solucion", editable=True, wrapText=True, autoHeight=True, width=220)
    gb.configure_column("asesor", editable=True, width=120)
    gb.configure_selection("multiple", use_checkbox=True, rowMultiSelectWithClick=True)
    gb.configure_grid_options(domLayout="normal", enableCellTextSelection=True)

    return AgGrid(
        display,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.VALUE_CHANGED | GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        height=460,
        theme="streamlit",
        allow_unsafe_jscode=True,
        key="grid_alertas",
    )


def indices_seleccionados(df: pd.DataFrame, selected_rows) -> list[int]:
    if selected_rows is None:
        return []
    if isinstance(selected_rows, pd.DataFrame):
        if selected_rows.empty:
            return []
        ids = selected_rows["id"].tolist()
    elif isinstance(selected_rows, list):
        if not selected_rows:
            return []
        ids = [r.get("id") for r in selected_rows if isinstance(r, dict)]
    else:
        return []
    return df.index[df["id"].isin(ids)].tolist()


def sidebar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.subheader("Filtros — Alertas Telegram")

    pendientes = contar_pendientes(df)
    st.sidebar.markdown(
        f'<p class="pendiente-badge">⏳ Pendientes sin gestión: <b>{pendientes}</b></p>',
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("##### Filtros avanzados")

    min_f = df["fecha_alerta"].min()
    max_f = df["fecha_alerta"].max()
    if pd.isna(min_f):
        min_f = pd.Timestamp.today()
    if pd.isna(max_f):
        max_f = pd.Timestamp.today()

    fecha_desde = st.sidebar.date_input("Desde", value=(min_f.date() if hasattr(min_f, "date") else date.today() - timedelta(days=30)))
    fecha_hasta = st.sidebar.date_input("Hasta", value=(max_f.date() if hasattr(max_f, "date") else date.today()))

    locales = st.sidebar.multiselect("Local", sorted(df["local"].dropna().unique()))
    areas = st.sidebar.multiselect("Área", sorted(df["area"].dropna().unique()))
    clasif = st.sidebar.multiselect("Clasificación", OPCIONES_CLASIFICACION)
    estados = st.sidebar.multiselect("Estado gestión", OPCIONES_ESTADO)
    contesto = st.sidebar.multiselect("Contestó", OPCIONES_CONTESTO)
    texto = st.sidebar.text_input("Buscar texto")

    solo_pend = st.sidebar.checkbox("Solo pendientes sin gestión", value=False)
    filtrado = filtrar_df(
        df,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        locales=locales,
        areas=areas,
        clasificaciones=clasif,
        estados=estados,
        contesto=contesto,
        texto=texto,
    )
    if solo_pend:
        filtrado = filtrado[
            (filtrado["estado_gestion"] == "Sin gestión")
            | (filtrado["solucion"].fillna("").astype(str).str.strip() == "")
        ]
    st.sidebar.caption(f"Mostrando **{len(filtrado)}** de **{len(df)}** casos")
    return filtrado


def render() -> None:
    init_state()
    df = st.session_state.df_alertas
    filtrado = sidebar_filtros(df)

    st.subheader("📡 Alertas Telegram — Matriz de Seguimiento")
    st.caption("Óptica Los Andes · Tablero operativo con clasificación, IA y exportación")

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-card"><div>Total filtrado</div><h2>{len(filtrado)}</h2></div>', unsafe_allow_html=True)
    c2.markdown(
        f'<div class="kpi-card"><div>Sin gestión</div><h2>{contar_pendientes(filtrado)}</h2></div>',
        unsafe_allow_html=True,
    )
    c3.markdown(
        f'<div class="kpi-card"><div>Resueltos</div><h2>{(filtrado["estado_gestion"] == "Resuelto").sum()}</h2></div>',
        unsafe_allow_html=True,
    )
    c4.markdown(
        f'<div class="kpi-card"><div>Contestó Sí</div><h2>{(filtrado["contesto"] == "Sí").sum()}</h2></div>',
        unsafe_allow_html=True,
    )

    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(tendencia_mensual(filtrado), use_container_width=True)
    with g2:
        st.plotly_chart(top_problemas(filtrado), use_container_width=True)

    g3, g4 = st.columns([2, 1])
    with g3:
        st.plotly_chart(heatmap_local_area(filtrado), use_container_width=True)
    with g4:
        st.plotly_chart(donut_estado(filtrado), use_container_width=True)

    st.divider()
    st.subheader("📋 Matriz editable de seguimiento")

    acc1, acc2, acc5 = st.columns([1.2, 1.2, 1])

    grid_resp = construir_grid(filtrado)
    df_grid = pd.DataFrame(grid_resp["data"])
    st.session_state.df_alertas = sincronizar_grid(st.session_state.df_alertas, df_grid)

    sel = grid_resp.get("selected_rows")
    idx_sel = indices_seleccionados(st.session_state.df_alertas, sel)
    idx_filtrados = filtrado.index.tolist()
    st.caption(f"Filas seleccionadas: **{len(idx_sel)}** · Filas visibles (filtro): **{len(idx_filtrados)}**")

    with acc1:
        if st.button("🏷️ Clasificar (reglas)", use_container_width=True):
            target = idx_sel if idx_sel else idx_filtrados
            st.session_state.df_alertas = clasificar_dataframe_reglas(st.session_state.df_alertas, target)
            guardar_alertas(st.session_state.df_alertas)
            st.success(f"Clasificadas {len(target)} filas con reglas.")
            st.rerun()

    with acc2:
        if st.button("🤖 Clasificar todo con IA", use_container_width=True, type="primary"):
            target = idx_sel if idx_sel else idx_filtrados
            with st.spinner("Clasificando con Claude..."):
                try:
                    st.session_state.df_alertas = clasificar_dataframe_ia_sync(
                        st.session_state.df_alertas, target
                    )
                    guardar_alertas(st.session_state.df_alertas)
                    st.success(f"IA clasificó {len(target)} filas.")
                except Exception as exc:
                    st.error(str(exc))
            st.rerun()

    with acc5:
        if st.button("💾 Guardar", use_container_width=True):
            guardar_alertas(st.session_state.df_alertas)
            st.success("Datos guardados.")

    st.download_button(
        label="📥 Exportar Excel — Matriz de Seguimiento",
        data=exportar_matriz_seguimiento(filtrado),
        file_name="matriz_seguimiento_alertas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )

    uploaded = st.file_uploader("Importar CSV de alertas", type=["csv"])
    if uploaded is not None:
        try:
            nuevo = pd.read_csv(uploaded)
            st.session_state.df_alertas = nuevo
            guardar_alertas(nuevo)
            st.success("CSV importado correctamente.")
            st.rerun()
        except Exception as exc:
            st.error(f"Error al importar: {exc}")

    st.divider()
    if idx_sel:
        fila = st.session_state.df_alertas.loc[idx_sel[0]].to_dict()
        st.caption(f"Generando IA para caso **#{fila.get('id')}** — {fila.get('cliente')}")
        resultado = render_panel_desde_fila(
            fila, "alertas_telegram",
            titulo_modulo="Alertas Telegram",
            key_prefix=f"alertas_{fila.get('id')}",
        )
        if resultado:
            texto = RespuestaIAService.dialogo_a_texto(resultado)
            st.session_state.df_alertas.loc[idx_sel[0], "dialogo_ia"] = texto
            st.session_state.df_alertas.loc[idx_sel[0], "canal_dialogo"] = resultado.get("canal", "whatsapp")
    else:
        st.info("Seleccione una fila en la tabla para usar **Generar Diálogo con Claude** o **Sugerir Respuesta IA**.")
        render_panel_desde_fila(
            {"id": "", "cliente": "{cliente}", "telefono": "{telefono}", "local": "{local}",
             "problema": "Caso de ejemplo", "mensaje_telegram": "Comentario del cliente"},
            "alertas_telegram",
            titulo_modulo="Alertas Telegram (demo)",
            key_prefix="alertas_demo",
        )