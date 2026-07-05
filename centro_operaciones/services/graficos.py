"""Gráficos del tablero de alertas."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def tendencia_mensual(df: pd.DataFrame):
    if df.empty:
        return go.Figure().update_layout(title="Sin datos")
    tmp = df.copy()
    tmp["mes"] = pd.to_datetime(tmp["fecha_alerta"], errors="coerce").dt.to_period("M").astype(str)
    agg = tmp.groupby("mes").size().reset_index(name="alertas")
    fig = px.bar(
        agg, x="mes", y="alertas", title="Tendencia mensual de alertas",
        color_discrete_sequence=["#2563eb"],
        labels={"mes": "Mes", "alertas": "Cantidad"},
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def top_problemas(df: pd.DataFrame, top_n: int = 8):
    if df.empty:
        return go.Figure().update_layout(title="Sin datos")
    agg = (
        df["problema"].value_counts().head(top_n).reset_index()
    )
    agg.columns = ["problema", "casos"]
    fig = px.bar(
        agg, y="problema", x="casos", orientation="h",
        title=f"Top {top_n} problemas",
        color_discrete_sequence=["#7c3aed"],
        labels={"problema": "Problema", "casos": "Casos"},
    )
    fig.update_layout(height=320, yaxis=dict(categoryorder="total ascending"), margin=dict(l=20, r=20, t=50, b=20))
    return fig


def heatmap_local_area(df: pd.DataFrame):
    if df.empty:
        return go.Figure().update_layout(title="Sin datos")
    pivot = pd.crosstab(df["local"], df["area"])
    fig = px.imshow(
        pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        color_continuous_scale="Blues",
        title="Heatmap — Local × Área",
        labels=dict(color="Casos"),
    )
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def donut_estado(df: pd.DataFrame):
    if df.empty:
        return go.Figure().update_layout(title="Sin datos")
    agg = df["estado_gestion"].value_counts().reset_index()
    agg.columns = ["estado", "casos"]
    fig = px.pie(
        agg, names="estado", values="casos", hole=0.45,
        title="Estado de gestión",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
    return fig