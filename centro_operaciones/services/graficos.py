"""Gráficos del tablero de alertas."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _layout_base(fig, height: int = 320, title: str = ""):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(family="Inter, system-ui, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.5)",
    )
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=14, color="#1E3A5F")))
    return fig


def tendencia_mensual(df: pd.DataFrame):
    if df.empty:
        return _layout_base(go.Figure(), title="Tendencia mensual — sin datos")
    tmp = df.copy()
    if "mes" in tmp.columns and tmp["mes"].fillna("").astype(str).str.strip().any():
        agg = tmp.groupby("mes", dropna=False).size().reset_index(name="alertas")
        agg = agg.sort_values("mes")
        x_col, x_label = "mes", "Mes"
    else:
        tmp["mes_calc"] = pd.to_datetime(tmp["fecha_alerta"], errors="coerce").dt.to_period("M").astype(str)
        agg = tmp.groupby("mes_calc").size().reset_index(name="alertas")
        x_col, x_label = "mes_calc", "Mes"
    fig = px.bar(
        agg, x=x_col, y="alertas",
        color_discrete_sequence=["#2563eb"],
        labels={x_col: x_label, "alertas": "Alertas"},
    )
    return _layout_base(fig, title="Tendencia mensual de alertas")


def top_problemas(df: pd.DataFrame, top_n: int = 10):
    if df.empty:
        return _layout_base(go.Figure(), title="Top problemas — sin datos")
    tmp = df.copy()
    tmp["tipo"] = tmp["clasificacion"].replace("", "Sin clasificar")
    tmp.loc[tmp["tipo"] == "Sin clasificar", "tipo"] = tmp.loc[tmp["tipo"] == "Sin clasificar", "clasificacion"]
    agg = tmp["clasificacion"].replace("", "Sin clasificar").value_counts().head(top_n).reset_index()
    agg.columns = ["clasificacion", "casos"]
    fig = px.bar(
        agg, y="clasificacion", x="casos", orientation="h",
        color_discrete_sequence=["#1d4ed8"],
        labels={"clasificacion": "Clasificación", "casos": "Casos"},
    )
    fig.update_layout(yaxis=dict(categoryorder="total ascending"))
    return _layout_base(fig, title=f"Top {top_n} clasificaciones / problemas")


def heatmap_local_clasificacion(df: pd.DataFrame, top_locales: int = 20):
    """Heatmap principal: Local × Clasificación."""
    if df.empty:
        return _layout_base(go.Figure(), height=460, title="Heatmap Local × Clasificación")
    tmp = df.copy()
    tmp["clas"] = tmp["clasificacion"].replace("", "Sin clasificar")
    top_locs = tmp["local"].value_counts().head(top_locales).index.tolist()
    tmp = tmp[tmp["local"].isin(top_locs)]
    pivot = pd.crosstab(tmp["local"], tmp["clas"])
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
    fig = px.imshow(
        pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        color_continuous_scale="Blues",
        labels=dict(color="Casos", x="Clasificación", y="Local"),
        aspect="auto",
    )
    return _layout_base(fig, height=480, title="Heatmap — Local × Clasificación")


def heatmap_mes_local(df: pd.DataFrame, top_locales: int = 15):
    if df.empty:
        return _layout_base(go.Figure(), height=400, title="Heatmap Mes × Local")
    tmp = df.copy()
    tmp["mes_val"] = tmp["mes"].replace("", pd.NA)
    tmp.loc[tmp["mes_val"].isna(), "mes_val"] = (
        pd.to_datetime(tmp["fecha_alerta"], errors="coerce").dt.strftime("%Y-%m")
    )
    top_locs = tmp["local"].value_counts().head(top_locales).index.tolist()
    tmp = tmp[tmp["local"].isin(top_locs)]
    pivot = pd.crosstab(tmp["mes_val"], tmp["local"])
    fig = px.imshow(
        pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        color_continuous_scale="PuBu",
        labels=dict(color="Casos"),
        aspect="auto",
    )
    return _layout_base(fig, height=400, title="Heatmap — Mes × Local")


def heatmap_local_area(df: pd.DataFrame):
    return heatmap_local_clasificacion(df)


def donut_estado(df: pd.DataFrame):
    if df.empty:
        return _layout_base(go.Figure(), title="Estado de gestión")
    agg = df["estado_gestion"].replace("", "Sin gestión").value_counts().reset_index()
    agg.columns = ["estado", "casos"]
    fig = px.pie(
        agg, names="estado", values="casos", hole=0.45,
        color_discrete_sequence=["#2563eb", "#f59e0b", "#16a34a", "#94a3b8"],
    )
    return _layout_base(fig, height=300, title="Estado de gestión")