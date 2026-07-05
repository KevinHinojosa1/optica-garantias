"""Carga, importación Excel GENERAL y persistencia — Alertas Telegram."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from centro_operaciones.constants import (
    ALERTAS_CSV,
    ALERTAS_EXCEL,
    ALERTAS_EXCEL_HOJA,
    ALERTAS_PARQUET,
    COLUMNAS_ORDEN,
    MAPEO_EXCEL,
    OPCIONES_ESTADO,
)


def _limpiar_texto(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        if isinstance(val, float) and val == int(val):
            val = int(val)
        return str(val)
    s = str(val).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return "" if s.lower() in ("nan", "none", "nat") else s


COLUMNAS_TEXTO = [
    c for c in COLUMNAS_ORDEN if c not in ("id", "n", "fecha_alerta")
]


def _normalizar_si_no(val: str, default: str = "Pendiente") -> str:
    t = _limpiar_texto(val).lower()
    if t in ("si", "sí", "yes"):
        return "Sí"
    if t in ("no",):
        return "No"
    if not t:
        return default
    return _limpiar_texto(val)


def _derivar_estado(solucion: str, observacion: str, contesto: str) -> str:
    if _limpiar_texto(solucion):
        return "Resuelto"
    if _limpiar_texto(observacion):
        return "En proceso"
    if _normalizar_si_no(contesto, "") in ("No", "Pendiente") and not _limpiar_texto(observacion):
        return "Pendiente llamada"
    return "Sin gestión"


def importar_excel_general(ruta: Path | None = None) -> pd.DataFrame:
    """Lee la hoja GENERAL del Excel operativo."""
    path = ruta or ALERTAS_EXCEL
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el Excel de alertas: {path}")

    raw = pd.read_excel(path, sheet_name=ALERTAS_EXCEL_HOJA)
    out = pd.DataFrame()

    for excel_col, interno in MAPEO_EXCEL.items():
        if excel_col in raw.columns:
            out[interno] = raw[excel_col]

    # Solo filas operativas (con local asignado)
    if "local" in out.columns:
        out["local"] = out["local"].apply(_limpiar_texto)
        out = out[out["local"] != ""].copy()

    out["id"] = pd.to_numeric(out.get("n", range(1, len(out) + 1)), errors="coerce").fillna(0).astype(int)
    out["fecha_alerta"] = pd.to_datetime(out.get("fecha_alerta"), errors="coerce")
    out["mes"] = out.get("mes", "").apply(_limpiar_texto)
    out["local"] = out.get("local", "").apply(_limpiar_texto)
    out["area"] = out.get("area", "").apply(_limpiar_texto)
    out["cliente"] = out.get("cliente", "").apply(_limpiar_texto)
    out["contacto"] = out.get("contacto", "").apply(_limpiar_texto)
    out["cedula_id"] = out.get("cedula_id", "").apply(_limpiar_texto)
    out["calificacion"] = out.get("calificacion", "").apply(_limpiar_texto)
    out["comentario"] = out.get("comentario", "").apply(_limpiar_texto)
    out["pregunta"] = out.get("pregunta", "").apply(_limpiar_texto)
    out["llamada_cliente"] = out.get("llamada_cliente", "").apply(lambda x: _normalizar_si_no(x, "Pendiente"))
    out["contesto"] = out.get("contesto", "").apply(lambda x: _normalizar_si_no(x, "Pendiente"))
    out["observacion_gestion"] = out.get("observacion_gestion", "").apply(_limpiar_texto)
    out["solucion"] = out.get("solucion", "").apply(_limpiar_texto)
    out["clasificacion"] = out.get("clasificacion", "").apply(_limpiar_texto)
    out.loc[out["clasificacion"] == "", "clasificacion"] = "Sin clasificar"
    out["estado_gestion"] = [
        _derivar_estado(s, o, c)
        for s, o, c in zip(out["solucion"], out["observacion_gestion"], out["contesto"])
    ]
    out["dialogo_ia"] = ""
    out["canal_dialogo"] = ""
    out["clasificado_por"] = ""

    # Alias compatibilidad
    out["telefono"] = out["contacto"]
    out["mensaje_telegram"] = out["comentario"]
    out["problema"] = out["pregunta"]
    out["descripcion"] = out["comentario"]

    return _normalizar(out)


def _fusionar_con_guardados(excel_df: pd.DataFrame, guardado: pd.DataFrame) -> pd.DataFrame:
    """Mantiene ediciones guardadas por id sobre la base del Excel."""
    if guardado is None or guardado.empty:
        return _normalizar(excel_df)
    out = _normalizar(excel_df).copy()
    g = _normalizar(guardado).set_index("id", drop=False)
    cols_editables = {
        c for c in out.columns
        if c not in ("id", "n", "fecha_alerta", "mes", "canal", "momento", "pregunta", "responde")
    }
    for i, row in out.iterrows():
        rid = int(row["id"])
        if rid not in g.index:
            continue
        saved = g.loc[rid]
        if isinstance(saved, pd.DataFrame):
            saved = saved.iloc[0]
        for col in cols_editables:
            if col not in saved.index:
                continue
            val = _limpiar_texto(saved[col])
            if val:
                out.at[i, col] = val
    return _normalizar(out)


def cargar_alertas() -> pd.DataFrame:
    excel_df = None
    if ALERTAS_EXCEL.exists():
        try:
            excel_df = importar_excel_general()
        except Exception:
            excel_df = None

    if ALERTAS_PARQUET.exists():
        try:
            guardado = pd.read_parquet(ALERTAS_PARQUET)
            if excel_df is not None:
                return _fusionar_con_guardados(excel_df, guardado)
            return _normalizar(guardado)
        except Exception:
            ALERTAS_PARQUET.unlink(missing_ok=True)

    if ALERTAS_CSV.exists():
        guardado = pd.read_csv(ALERTAS_CSV, dtype=str, keep_default_na=False)
        if excel_df is not None:
            return _fusionar_con_guardados(excel_df, guardado)
        return _normalizar(guardado)

    if excel_df is not None:
        guardar_alertas(excel_df)
        return excel_df

    raise FileNotFoundError(
        "No hay datos de alertas. Coloque ALERTAS_TELEGRAM_2026.xlsx en centro_operaciones/data/"
    )


def recargar_desde_excel() -> pd.DataFrame:
    """Reimporta Excel y fusiona ediciones existentes."""
    excel_df = importar_excel_general()
    guardado = None
    if ALERTAS_PARQUET.exists():
        guardado = pd.read_parquet(ALERTAS_PARQUET)
    elif ALERTAS_CSV.exists():
        guardado = pd.read_csv(ALERTAS_CSV)
    df = _fusionar_con_guardados(excel_df, guardado) if guardado is not None else excel_df
    guardar_alertas(df)
    return df


def guardar_alertas(df: pd.DataFrame) -> None:
    ALERTAS_CSV.parent.mkdir(parents=True, exist_ok=True)
    out = _normalizar(df)
    out.to_csv(ALERTAS_CSV, index=False)
    try:
        out.to_parquet(ALERTAS_PARQUET, index=False)
    except Exception:
        pass


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in COLUMNAS_ORDEN:
        if col not in out.columns:
            out[col] = ""
    out = out[COLUMNAS_ORDEN].copy()

    out["id"] = pd.to_numeric(out["id"], errors="coerce").fillna(0).astype(int)
    out["n"] = pd.to_numeric(out["n"], errors="coerce").fillna(out["id"]).astype(int)
    out["fecha_alerta"] = pd.to_datetime(out["fecha_alerta"], errors="coerce")

    for col in COLUMNAS_TEXTO:
        out[col] = out[col].apply(_limpiar_texto)

    out["llamada_cliente"] = out["llamada_cliente"].apply(lambda x: _normalizar_si_no(x, "Pendiente"))
    out["contesto"] = out["contesto"].apply(lambda x: _normalizar_si_no(x, "Pendiente"))
    out.loc[out["clasificacion"].str.strip() == "", "clasificacion"] = "Sin clasificar"
    vacio_estado = out["estado_gestion"].str.strip() == ""
    out.loc[vacio_estado, "estado_gestion"] = out.loc[vacio_estado].apply(
        lambda r: _derivar_estado(r["solucion"], r["observacion_gestion"], r["contesto"]), axis=1
    )
    out["telefono"] = out["contacto"]
    out["mensaje_telegram"] = out["comentario"]
    out["problema"] = out["pregunta"]
    out["descripcion"] = out["comentario"]

    # Evitar dtypes Arrow string que fallan al fusionar tipos mixtos
    for col in COLUMNAS_TEXTO:
        out[col] = out[col].astype(object)
    return out


def contar_pendientes(df: pd.DataFrame) -> int:
    sin_sol = df["solucion"].fillna("").astype(str).str.strip() == ""
    sin_obs = df["observacion_gestion"].fillna("").astype(str).str.strip() == ""
    sin_gestion = df["estado_gestion"].isin(["Sin gestión", "Pendiente llamada", ""])
    return int((sin_sol & sin_obs & sin_gestion).sum())


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
    meses: list[str] | None = None,
) -> pd.DataFrame:
    out = df.copy()
    if fecha_desde:
        out = out[out["fecha_alerta"] >= pd.Timestamp(fecha_desde)]
    if fecha_hasta:
        out = out[out["fecha_alerta"] <= pd.Timestamp(fecha_hasta) + timedelta(days=1)]
    if meses:
        out = out[out["mes"].isin(meses)]
    if locales:
        out = out[out["local"].isin(locales)]
    if areas:
        out = out[out["area"].isin(areas)]
    if clasificaciones:
        out = out[out["clasificacion"].isin(clasificaciones)]
    if estados:
        out = out[out["estado_gestion"].isin(estados)]
    if contesto:
        norm = []
        for c in contesto:
            norm.append(c)
            if c == "Sí":
                norm.extend(["si", "SI", "Si"])
            if c == "No":
                norm.extend(["no", "NO", "No"])
        out = out[out["contesto"].isin(norm)]
    if texto.strip():
        q = texto.strip().lower()
        cols = [
            "cliente", "pregunta", "comentario", "local", "solucion",
            "observacion_gestion", "asesor", "optometra", "contacto", "clasificacion",
        ]
        mask = False
        for c in cols:
            if c in out.columns:
                mask = mask | out[c].fillna("").astype(str).str.lower().str.contains(q, regex=False)
        out = out[mask]
    return out