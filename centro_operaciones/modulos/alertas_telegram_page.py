"""
Alertas Telegram — Matriz de Seguimiento (Streamlit · IA-first)
==============================================================
Flujo diario:
  1. Subir ALERTAS TELEGRAM 2026.xlsx (hoja GENERAL)
  2. La IA clasifica automáticamente Pregunta + Comentario
  3. Revisar / ajustar en st.data_editor
  4. Generar diálogo Claude · Guardar · Exportar Excel

Ejecutar: streamlit run centro_operaciones/app.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from centro_operaciones.constants import (
    CATEGORIAS_IA,
    COLUMNAS_EDITOR,
    OPCIONES_CLASIFICACION,
    OPCIONES_CONTESTO,
    OPCIONES_ESTADO,
    OPCIONES_LLAMADA,
)
from centro_operaciones.components.respuesta_ia import render_panel_desde_fila
from centro_operaciones.services.clasificacion_ia_alertas import clasificar_dataframe_completo
from centro_operaciones.services.datastore import (
    _normalizar,
    cargar_alertas,
    contar_pendientes,
    filtrar_df,
    fusionar_incremental,
    guardar_alertas,
    importar_excel_bytes,
)
from centro_operaciones.services.exportacion import exportar_matriz_seguimiento
from centro_operaciones.services.graficos import (
    donut_estado,
    heatmap_local_clasificacion,
    heatmap_mes_local,
    tendencia_mensual,
    top_problemas,
)
from services.respuesta_ia_service import RespuestaIAService

# ── Session state ─────────────────────────────────────────────────────────────

def _init_session() -> None:
    if "df_alertas" not in st.session_state:
        try:
            st.session_state.df_alertas = cargar_alertas()
        except FileNotFoundError:
            st.session_state.df_alertas = pd.DataFrame()
    if "ids_seleccion" not in st.session_state:
        st.session_state.ids_seleccion = []
    if "auto_clasificar_al_cargar" not in st.session_state:
        st.session_state.auto_clasificar_al_cargar = True


def _df_editor(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve subset de columnas para la tabla editable."""
    cols = [c for c in COLUMNAS_EDITOR if c in df.columns]
    out = df[cols].copy()
    if "fecha_alerta" in out.columns:
        out["fecha_alerta"] = pd.to_datetime(out["fecha_alerta"], errors="coerce").dt.strftime("%d/%m/%Y")
    return out


def _fusionar_editor(df_base: pd.DataFrame, df_editado: pd.DataFrame) -> pd.DataFrame:
    """Sincroniza cambios del data_editor al dataframe completo."""
    if df_editado is None or df_editado.empty:
        return df_base
    out = df_base.copy()
    if "n" not in df_editado.columns:
        return out
    for _, row in df_editado.iterrows():
        n_val = row.get("n")
        if pd.isna(n_val):
            continue
        mask = out["n"] == int(n_val)
        if not mask.any():
            # Fila nueva agregada manualmente
            nueva = {c: "" for c in out.columns}
            for c in row.index:
                if c in nueva:
                    nueva[c] = row[c]
            nueva["id"] = int(out["id"].max() + 1) if len(out) else 1
            nueva["n"] = int(n_val) if n_val else nueva["id"]
            out = pd.concat([out, pd.DataFrame([nueva])], ignore_index=True)
            continue
        for col in row.index:
            if col in out.columns:
                out.loc[mask, col] = row[col]
    return _normalizar(out)


# ── Sidebar: carga Excel y filtros ────────────────────────────────────────────

def _sidebar_carga() -> None:
    st.sidebar.markdown("### 📤 Cargar Excel")
    st.sidebar.caption("Hoja **GENERAL** de ALERTAS TELEGRAM 2026.xlsx")

    modo = st.sidebar.radio("Modo de carga", ["Reemplazar todo", "Solo filas nuevas"], horizontal=True)
    auto_ia = st.sidebar.checkbox(
        "🤖 Clasificar con IA al cargar",
        value=st.session_state.auto_clasificar_al_cargar,
    )
    st.session_state.auto_clasificar_al_cargar = auto_ia

    archivo = st.sidebar.file_uploader("Subir Excel", type=["xlsx", "xls"])
    if archivo is not None:
        if st.sidebar.button("Procesar archivo", type="primary", use_container_width=True):
            with st.spinner("Leyendo hoja GENERAL..."):
                nuevo = importar_excel_bytes(archivo.read())
                if modo.startswith("Solo"):
                    st.session_state.df_alertas = fusionar_incremental(
                        nuevo, st.session_state.df_alertas
                    )
                    st.sidebar.success(f"➕ Filas nuevas integradas. Total: {len(st.session_state.df_alertas)}")
                else:
                    st.session_state.df_alertas = nuevo
                    st.sidebar.success(f"✅ {len(nuevo)} filas cargadas")

                if auto_ia and len(st.session_state.df_alertas) > 0:
                    bar = st.sidebar.progress(0, text="Clasificando con IA...")
                    def _prog(done, total):
                        bar.progress(done / total, text=f"IA: {done}/{total}")

                    st.session_state.df_alertas = clasificar_dataframe_completo(
                        st.session_state.df_alertas,
                        on_progress=_prog,
                    )
                    bar.empty()
                    st.sidebar.success("🤖 Clasificación IA completada")
            st.rerun()


def _sidebar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown("### 🔍 Filtros")
    pend = contar_pendientes(df)
    st.sidebar.markdown(
        f'<p class="pendiente-badge">⏳ Pendientes: <b>{pend}</b></p>',
        unsafe_allow_html=True,
    )

    min_f = df["fecha_alerta"].min() if not df.empty else pd.Timestamp.today()
    max_f = df["fecha_alerta"].max() if not df.empty else pd.Timestamp.today()
    if pd.isna(min_f):
        min_f = pd.Timestamp.today()
    if pd.isna(max_f):
        max_f = pd.Timestamp.today()

    f_desde = st.sidebar.date_input("Desde", value=min_f.date() if hasattr(min_f, "date") else date.today() - timedelta(days=90))
    f_hasta = st.sidebar.date_input("Hasta", value=max_f.date() if hasattr(max_f, "date") else date.today())
    meses = st.sidebar.multiselect("Mes", sorted(df["mes"].dropna().unique()) if not df.empty else [])
    locales = st.sidebar.multiselect("Local", sorted(df["local"].dropna().unique()) if not df.empty else [])
    clasif = st.sidebar.multiselect("Clasificación", OPCIONES_CLASIFICACION)
    estados = st.sidebar.multiselect("Estado", OPCIONES_ESTADO)
    solo_pend = st.sidebar.checkbox("Solo pendientes sin gestión", value=False)
    texto = st.sidebar.text_input("Buscar")

    if df.empty:
        return df

    filtrado = filtrar_df(
        df,
        fecha_desde=f_desde,
        fecha_hasta=f_hasta,
        locales=locales,
        areas=[],
        clasificaciones=clasif,
        estados=estados,
        contesto=[],
        texto=texto,
        meses=meses,
    )
    if solo_pend:
        sin_sol = filtrado["solucion"].fillna("").astype(str).str.strip() == ""
        sin_obs = filtrado["observacion_gestion"].fillna("").astype(str).str.strip() == ""
        filtrado = filtrado[sin_sol & sin_obs]
    st.sidebar.caption(f"Mostrando **{len(filtrado)}** de **{len(df)}**")
    return filtrado


# ── Formulario rápido: nueva alerta del día ───────────────────────────────────

def _formulario_nueva_alerta() -> None:
    with st.expander("➕ Agregar alerta nueva (actualización diaria)", expanded=False):
        with st.form("nueva_alerta", border=True):
            c1, c2, c3 = st.columns(3)
            local = c1.text_input("Local *")
            area = c2.selectbox("Área", ["Ventas", "Optometría", "Laboratorio", "Postventa", ""])
            mes = c3.text_input("Mes", placeholder="Ej: Julio")
            c4, c5 = st.columns(2)
            cliente = c4.text_input("Cliente")
            contacto = c5.text_input("Contacto / Teléfono")
            pregunta = st.text_input("Pregunta")
            comentario = st.text_area("Comentario del cliente *")
            if st.form_submit_button("Agregar y clasificar con IA", type="primary"):
                if not local.strip() or not comentario.strip():
                    st.error("Local y Comentario son obligatorios.")
                    return
                df = st.session_state.df_alertas
                nuevo_id = int(df["id"].max() + 1) if not df.empty else 1
                fila = {
                    "id": nuevo_id, "n": nuevo_id, "mes": mes, "fecha_alerta": pd.Timestamp.now(),
                    "canal": "Telegram", "local": local.strip(), "area": area,
                    "cliente": cliente, "contacto": contacto,
                    "pregunta": pregunta, "comentario": comentario,
                    "clasificacion": "Otros / Sin clasificar", "estado_gestion": "Sin gestión",
                }
                df_nueva = pd.DataFrame([fila])
                df_nueva = clasificar_dataframe_completo(df_nueva)
                st.session_state.df_alertas = _normalizar(
                    pd.concat([df, df_nueva], ignore_index=True) if not df.empty else df_nueva
                )
                st.success(f"Alerta #{nuevo_id} agregada y clasificada.")
                st.rerun()


# ── Render principal ────────────────────────────────────────────────────────

def render() -> None:
    _init_session()
    _sidebar_carga()
    df = st.session_state.df_alertas

    if df.empty:
        st.warning("Suba el Excel **ALERTAS TELEGRAM 2026.xlsx** en la barra lateral para comenzar.")
        return

    filtrado = _sidebar_filtros(df)

    # Header
    ia = RespuestaIAService.ia_disponible()
    h1, h2 = st.columns([3, 1])
    with h1:
        st.subheader("📡 Alertas Telegram — Matriz de Seguimiento")
        st.caption("Flujo IA-first · Suba Excel → IA clasifica → Usted ajusta → Guarda")
    with h2:
        if ia["disponible"]:
            st.success(f"🤖 Claude · {ia['modelo']}")
        else:
            st.info("Modo simulación (reglas) — sin API key")

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total filtrado", len(filtrado))
    k2.metric("Sin gestión", int(filtrado["estado_gestion"].isin(["Sin gestión", "Pendiente llamada", ""]).sum()) if not filtrado.empty else 0)
    k3.metric("Resueltos", int((filtrado["estado_gestion"] == "Resuelto").sum()) if not filtrado.empty else 0)
    k4.metric("Pendientes", contar_pendientes(filtrado))

    # Gráficos
    if not filtrado.empty:
        g1, g2 = st.columns(2)
        g1.plotly_chart(tendencia_mensual(filtrado), use_container_width=True)
        g2.plotly_chart(top_problemas(filtrado), use_container_width=True)
        g3, g4 = st.columns(2)
        g3.plotly_chart(heatmap_local_clasificacion(filtrado), use_container_width=True)
        g4.plotly_chart(heatmap_mes_local(filtrado), use_container_width=True)
        st.plotly_chart(donut_estado(filtrado), use_container_width=True)

    st.divider()
    _formulario_nueva_alerta()

    # Botones de acción
    st.markdown("### 📋 Matriz editable")
    b1, b2, b3, b4 = st.columns(4)
    reclasificar = b1.button("🤖 Clasificar / Re-clasificar con IA", type="primary", use_container_width=True)
    guardar_btn = b2.button("💾 Actualizar / Guardar cambios", use_container_width=True)
    b3.download_button(
        "📥 Exportar Excel",
        data=exportar_matriz_seguimiento(filtrado if not filtrado.empty else df),
        file_name="alertas_telegram_actualizado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    reclasificar_sel = b4.button("🏷️ IA solo filas filtradas", use_container_width=True)

    # Tabla editable principal
    df_show = _df_editor(filtrado if not filtrado.empty else df)
    editado = st.data_editor(
        df_show,
        num_rows="dynamic",
        use_container_width=True,
        height=480,
        column_config={
            "clasificacion": st.column_config.SelectboxColumn("CLASIFICACION", options=CATEGORIAS_IA, required=False),
            "estado_gestion": st.column_config.SelectboxColumn("Estado", options=OPCIONES_ESTADO, required=False),
            "llamada_cliente": st.column_config.SelectboxColumn("Llamada", options=OPCIONES_LLAMADA, required=False),
            "contesto": st.column_config.SelectboxColumn("Contestó", options=OPCIONES_CONTESTO, required=False),
            "comentario": st.column_config.TextColumn("Comentario", width="large"),
            "observacion_gestion": st.column_config.TextColumn("Gestión", width="large"),
            "solucion": st.column_config.TextColumn("SOLUCIÓN", width="large"),
            "justificacion_ia": st.column_config.TextColumn("Justificación IA", width="medium"),
            "dialogo_ia": st.column_config.TextColumn("Diálogo IA", width="large"),
        },
        key="editor_alertas",
    )

    # Sincronizar ediciones al session_state
    st.session_state.df_alertas = _fusionar_editor(st.session_state.df_alertas, editado)

    # Acciones IA / guardar
    if reclasificar or reclasificar_sel:
        target_df = filtrado if reclasificar_sel else st.session_state.df_alertas
        indices = target_df.index.tolist()
        bar = st.progress(0, text="Clasificando con IA...")
        st.session_state.df_alertas = clasificar_dataframe_completo(
            st.session_state.df_alertas,
            indices=indices,
            on_progress=lambda d, t: bar.progress(d / t, text=f"IA: {d}/{t}"),
        )
        bar.empty()
        guardar_alertas(st.session_state.df_alertas)
        st.success(f"✅ {len(indices)} fila(s) clasificadas con IA")
        st.rerun()

    if guardar_btn:
        guardar_alertas(st.session_state.df_alertas)
        st.success("💾 Cambios guardados correctamente")
        st.rerun()

    # Selección para diálogo Claude
    st.divider()
    st.markdown("### ✨ Generar Diálogo con Claude")
    if not filtrado.empty:
        opciones = filtrado["n"].tolist()
        sel_n = st.selectbox(
            "Seleccionar caso",
            opciones,
            format_func=lambda n: f"#{n} — {filtrado.loc[filtrado['n']==n, 'cliente'].iloc[0]} ({filtrado.loc[filtrado['n']==n, 'local'].iloc[0]})",
        )
        fila = st.session_state.df_alertas[st.session_state.df_alertas["n"] == sel_n].iloc[0].to_dict()
        resultado = render_panel_desde_fila(
            fila,
            "alertas_telegram",
            titulo_modulo="Alertas Telegram",
            key_prefix=f"alertas_{fila.get('id')}",
        )
        if resultado:
            texto = RespuestaIAService.dialogo_a_texto(resultado)
            mask = st.session_state.df_alertas["id"] == fila["id"]
            st.session_state.df_alertas.loc[mask, "dialogo_ia"] = texto
            st.session_state.df_alertas.loc[mask, "canal_dialogo"] = resultado.get("canal", "whatsapp")
    else:
        st.info("No hay filas en el filtro actual.")