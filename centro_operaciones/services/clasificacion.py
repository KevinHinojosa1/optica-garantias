"""Clasificación automática por reglas e IA."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from centro_operaciones.constants import OPCIONES_CLASIFICACION, REGLAS_CLASIFICACION

try:
    from config import settings
except ImportError:
    settings = None

CAMPOS_TEXTO = ("comentario", "pregunta", "observacion_gestion", "problema", "descripcion", "mensaje_telegram")


def _texto_fila(row: dict | pd.Series) -> str:
    partes = []
    for c in CAMPOS_TEXTO:
        if isinstance(row, dict):
            val = row.get(c, "")
        else:
            val = row[c] if c in row.index else ""
        if val and str(val).strip():
            partes.append(str(val))
    return " ".join(partes)


def clasificar_por_reglas(texto: str) -> str:
    t = (texto or "").lower()
    mejor = "Sin clasificar"
    mejor_score = 0
    for categoria, palabras in REGLAS_CLASIFICACION:
        score = sum(1 for p in palabras if p in t)
        if score > mejor_score:
            mejor_score = score
            mejor = categoria
    return mejor if mejor_score > 0 else "Otro"


def clasificar_dataframe_reglas(df: pd.DataFrame, indices: list[int] | None = None) -> pd.DataFrame:
    out = df.copy()
    idx = indices if indices is not None else out.index.tolist()
    for i in idx:
        if i not in out.index:
            continue
        texto = _texto_fila(out.loc[i])
        out.at[i, "clasificacion"] = clasificar_por_reglas(texto)
        out.at[i, "clasificado_por"] = "reglas"
    return out


async def clasificar_con_claude(filas: list[dict]) -> list[str]:
    if not settings or not settings.anthropic_api_key:
        return [clasificar_por_reglas(_texto_fila(f)) for f in filas]

    import httpx

    categorias = ", ".join(OPCIONES_CLASIFICACION)
    bloques = []
    for i, f in enumerate(filas):
        bloques.append(
            f"#{i}: local={f.get('local', '')} | comentario={f.get('comentario', '')} | "
            f"pregunta={f.get('pregunta', '')}"
        )
    prompt = (
        f"Clasifica cada alerta de óptica en UNA categoría: {categorias}.\n"
        f"Responde SOLO JSON: {{\"clasificaciones\": [\"cat1\", ...]}} en el mismo orden.\n\n"
        + "\n".join(bloques)
    )
    payload = {
        "model": settings.anthropic_model,
        "max_tokens": 2048,
        "system": "Eres analista de operaciones de Óptica Los Andes Ecuador. Responde únicamente JSON válido.",
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(f"{settings.anthropic_api_base}/messages", headers=headers, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(resp.text[:300])
    texto = resp.json()["content"][0]["text"]
    match = re.search(r"\{[\s\S]*\}", texto)
    if not match:
        raise RuntimeError("Respuesta IA sin JSON")
    data = json.loads(match.group())
    resultados = data.get("clasificaciones", [])
    normalizados = []
    for i, f in enumerate(filas):
        cat = resultados[i] if i < len(resultados) else "Otro"
        if cat not in OPCIONES_CLASIFICACION:
            cat = clasificar_por_reglas(_texto_fila(f))
        normalizados.append(cat)
    return normalizados


def clasificar_dataframe_ia_sync(df: pd.DataFrame, indices: list[int]) -> pd.DataFrame:
    import asyncio

    out = df.copy()
    filas = [out.loc[i].to_dict() for i in indices if i in out.index]
    if not filas:
        return out
    cats = asyncio.run(clasificar_con_claude(filas))
    for idx, cat in zip([i for i in indices if i in out.index], cats):
        out.at[idx, "clasificacion"] = cat
        out.at[idx, "clasificado_por"] = "claude"
    return out