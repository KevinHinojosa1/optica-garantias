"""Carga, guardado y datos de ejemplo — Alertas Telegram."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from centro_operaciones.constants import (
    ALERTAS_CSV,
    ALERTAS_PARQUET,
    AREAS,
    COLUMNAS_ORDEN,
    OPCIONES_CLASIFICACION,
    OPCIONES_CONTESTO,
    OPCIONES_ESTADO,
    OPCIONES_LLAMADA,
)

LOCALES = [
    "Quito Centro", "Cuenca Centro", "Guayaquil Norte", "Ambato", "Riobamba",
    "Manta", "Loja", "Ibarra", "Machala", "Portoviejo",
]

PROBLEMAS = [
    "Retraso en entrega de lentes",
    "Cliente no satisfecho con montura",
    "Garantía rechazada",
    "Error en graduación",
    "Producto defectuoso",
    "Demora en laboratorio",
    "Mala atención en tienda",
    "Consulta de estado de pedido",
    "Solicitud de devolución",
    "Adaptación difícil a lentes nuevos",
]


def _columnas_vacias() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNAS_ORDEN)


def generar_datos_ejemplo(n: int = 48) -> pd.DataFrame:
    random.seed(42)
    filas = []
    base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(1, n + 1):
        dias = random.randint(0, 45)
        fecha = base - timedelta(days=dias, hours=random.randint(8, 19))
        problema = random.choice(PROBLEMAS)
        estado = random.choices(
            OPCIONES_ESTADO, weights=[35, 25, 40], k=1
        )[0]
        filas.append({
            "id": i,
            "fecha_alerta": fecha.strftime("%Y-%m-%d %H:%M"),
            "local": random.choice(LOCALES),
            "area": random.choice(AREAS),
            "problema": problema,
            "descripcion": f"Alerta Telegram #{i}: {problema.lower()} reportado por cliente.",
            "cliente": f"Cliente {i}",
            "telefono": f"09{random.randint(10000000, 99999999)}",
            "mensaje_telegram": f"🚨 {problema} — requiere seguimiento del equipo.",
            "llamada_cliente": random.choice(OPCIONES_LLAMADA),
            "contesto": random.choice(OPCIONES_CONTESTO),
            "solucion": "" if estado == "Sin gestión" else "Seguimiento registrado en sistema.",
            "clasificacion": random.choice(OPCIONES_CLASIFICACION),
            "estado_gestion": estado,
            "asesor": "" if estado == "Sin gestión" else random.choice(["María G.", "Carlos R.", "Ana P."]),
            "dialogo_ia": "",
            "canal_dialogo": "",
            "clasificado_por": "reglas" if random.random() > 0.3 else "",
        })
    return pd.DataFrame(filas)


def cargar_alertas() -> pd.DataFrame:
    if ALERTAS_PARQUET.exists():
        df = pd.read_parquet(ALERTAS_PARQUET)
    elif ALERTAS_CSV.exists():
        df = pd.read_csv(ALERTAS_CSV)
    else:
        df = generar_datos_ejemplo()
        guardar_alertas(df)
    return _normalizar(df)


def guardar_alertas(df: pd.DataFrame) -> None:
    ALERTAS_CSV.parent.mkdir(parents=True, exist_ok=True)
    out = _normalizar(df)
    out.to_csv(ALERTAS_CSV, index=False)
    try:
        out.to_parquet(ALERTAS_PARQUET, index=False)
    except Exception:
        pass


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    for col in COLUMNAS_ORDEN:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNAS_ORDEN].copy()
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    df["fecha_alerta"] = pd.to_datetime(df["fecha_alerta"], errors="coerce")
    for col in ("llamada_cliente", "contesto", "estado_gestion", "clasificacion"):
        df[col] = df[col].fillna("").astype(str).replace("nan", "")
    df.loc[df["llamada_cliente"] == "", "llamada_cliente"] = "Pendiente"
    df.loc[df["contesto"] == "", "contesto"] = "Pendiente"
    df.loc[df["estado_gestion"] == "", "estado_gestion"] = "Sin gestión"
    return df


def contar_pendientes(df: pd.DataFrame) -> int:
    mask = (df["estado_gestion"] == "Sin gestión") | (
        df["solucion"].fillna("").astype(str).str.strip() == ""
    )
    return int(mask.sum())


def filtrar_df(
    df: pd.DataFrame,
    *,
    fecha_desde,
    fecha_hasta,
    locales: list[str],
    areas: list[str],
    clasificaciones: list[str],
    estados: list[str],
    contesto: list[str],
    texto: str,
) -> pd.DataFrame:
    out = df.copy()
    if fecha_desde:
        out = out[out["fecha_alerta"] >= pd.Timestamp(fecha_desde)]
    if fecha_hasta:
        out = out[out["fecha_alerta"] <= pd.Timestamp(fecha_hasta) + timedelta(days=1)]
    if locales:
        out = out[out["local"].isin(locales)]
    if areas:
        out = out[out["area"].isin(areas)]
    if clasificaciones:
        out = out[out["clasificacion"].isin(clasificaciones)]
    if estados:
        out = out[out["estado_gestion"].isin(estados)]
    if contesto:
        out = out[out["contesto"].isin(contesto)]
    if texto.strip():
        q = texto.strip().lower()
        cols = ["cliente", "problema", "descripcion", "mensaje_telegram", "local", "solucion"]
        mask = False
        for c in cols:
            mask = mask | out[c].fillna("").astype(str).str.lower().str.contains(q, regex=False)
        out = out[mask]
    return out