"""
Clasificación inteligente de alertas Telegram con Claude.

Flujo IA-first: al subir Excel, clasifica cada fila usando Pregunta + Comentario
y devuelve categoría, justificación y solución sugerida.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Callable

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from centro_operaciones.constants import CATEGORIAS_IA, REGLAS_CLASIFICACION

try:
    from config import settings
except ImportError:
    settings = None

LOTE_DEFAULT = 8

SUGERENCIAS_REGLAS: dict[str, str] = {
    "Garantía / OLA PLUS sin informar": "Llamar al cliente, explicar cobertura OLA PLUS y registrar aclaración en sistema.",
    "Demora en entrega / no avisan cuando está listo": "Verificar estado en laboratorio, comunicar fecha real y ofrecer seguimiento por WhatsApp.",
    "Errores de medidas / calidad de lunas / lentes mal hechos": "Agendar revisión optométrica y gestionar cambio/garantía en tienda.",
    "Atención deficiente / falta de empatía / apuro / trato malo": "Escalar a supervisor de tienda, pedir disculpas y registrar plan de mejora.",
    "Falta de explicación (producto, cuidado, garantía, uso)": "Enviar guía de uso/cuidados y confirmar comprensión del cliente.",
    "Cobros extras / valores no solicitados / precio": "Revisar factura con administración y contactar cliente con resolución en 24h.",
    "Otros / Sin clasificar": "Contactar cliente para entender el caso y asignar responsable de seguimiento.",
}


def _texto_alerta(fila: dict) -> str:
    return " ".join(
        str(fila.get(c, "") or "")
        for c in ("pregunta", "comentario", "problema", "descripcion")
    ).strip()


def _clasificar_reglas(texto: str) -> str:
    t = (texto or "").lower()
    mejor = "Otros / Sin clasificar"
    score_max = 0
    for categoria, palabras in REGLAS_CLASIFICACION:
        score = sum(1 for p in palabras if p in t)
        if score > score_max:
            score_max = score
            mejor = categoria
    return mejor


def _simular_resultado(fila: dict) -> dict:
    texto = _texto_alerta(fila)
    cat = _clasificar_reglas(texto)
    return {
        "id": fila.get("id"),
        "clasificacion": cat,
        "justificacion": f"Clasificación automática por palabras clave en: «{texto[:120]}...»",
        "solucion": SUGERENCIAS_REGLAS.get(cat, SUGERENCIAS_REGLAS["Otros / Sin clasificar"]),
        "generado_por": "reglas",
    }


def _parse_json_ia(texto: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", texto)
    if not match:
        raise RuntimeError("La IA no devolvió JSON válido")
    return json.loads(match.group())


async def _clasificar_lote_claude(filas: list[dict]) -> list[dict]:
    """Clasifica un lote de alertas con Claude."""
    if not settings or not settings.anthropic_api_key:
        return [_simular_resultado(f) for f in filas]

    import httpx

    categorias = "\n".join(f"- {c}" for c in CATEGORIAS_IA)
    bloques = []
    for f in filas:
        bloques.append(
            f'id={f.get("id")} | local={f.get("local", "")} | pregunta={f.get("pregunta", "")} | '
            f'comentario={f.get("comentario", "")}'
        )

    prompt = f"""Eres analista de operaciones y CX de Óptica Los Andes Ecuador.
Clasifica cada alerta de Telegram usando SOLO una de estas categorías:
{categorias}

Para cada alerta devuelve:
- clasificacion (exacta de la lista)
- justificacion (1-2 frases en español)
- solucion (acción concreta recomendada para el asesor)

Responde ÚNICAMENTE JSON:
{{"resultados": [{{"id": 1, "clasificacion": "...", "justificacion": "...", "solucion": "..."}}]}}

Alertas:
""" + "\n".join(bloques)

    payload = {
        "model": settings.anthropic_model,
        "max_tokens": 4096,
        "system": "Respondes únicamente JSON válido en español ecuatoriano. Sé empático y operativo.",
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{settings.anthropic_api_base}/messages", headers=headers, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(resp.text[:400])

    data = _parse_json_ia(resp.json()["content"][0]["text"])
    resultados = data.get("resultados", [])
    out = []
    for i, fila in enumerate(filas):
        item = resultados[i] if i < len(resultados) else {}
        cat = item.get("clasificacion", "Otros / Sin clasificar")
        if cat not in CATEGORIAS_IA:
            cat = _clasificar_reglas(_texto_alerta(fila))
        out.append({
            "id": fila.get("id"),
            "clasificacion": cat,
            "justificacion": item.get("justificacion", ""),
            "solucion": item.get("solucion", SUGERENCIAS_REGLAS.get(cat, "")),
            "generado_por": "claude",
        })
    return out


def clasificar_filas_ia_sync(
    filas: list[dict],
    *,
    tamano_lote: int = LOTE_DEFAULT,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[dict]:
    """Clasifica filas en lotes (sync wrapper para Streamlit)."""
    import asyncio

    todos: list[dict] = []
    total = len(filas)
    for i in range(0, total, tamano_lote):
        lote = filas[i : i + tamano_lote]
        resultados = asyncio.run(_clasificar_lote_claude(lote))
        todos.extend(resultados)
        if on_progress:
            on_progress(min(i + len(lote), total), total)
    return todos


def aplicar_clasificacion_ia(df: pd.DataFrame, indices: list[int], resultados: list[dict]) -> pd.DataFrame:
    """Escribe clasificación IA en el DataFrame."""
    out = df.copy()
    mapa = {int(r["id"]): r for r in resultados if r.get("id") is not None}
    for idx in indices:
        if idx not in out.index:
            continue
        rid = int(out.at[idx, "id"])
        if rid not in mapa:
            continue
        r = mapa[rid]
        out.at[idx, "clasificacion"] = r.get("clasificacion", "Otros / Sin clasificar")
        out.at[idx, "justificacion_ia"] = r.get("justificacion", "")
        if not str(out.at[idx, "solucion"] or "").strip():
            out.at[idx, "solucion"] = r.get("solucion", "")
        if not str(out.at[idx, "observacion_gestion"] or "").strip():
            out.at[idx, "observacion_gestion"] = r.get("justificacion", "")
        out.at[idx, "clasificado_por"] = r.get("generado_por", "claude")
        if out.at[idx, "estado_gestion"] in ("", "Sin clasificar", "Sin gestión"):
            out.at[idx, "estado_gestion"] = "En proceso" if r.get("solucion") else "Sin gestión"
    return out


def clasificar_dataframe_completo(
    df: pd.DataFrame,
    indices: list[int] | None = None,
    *,
    on_progress: Callable[[int, int], None] | None = None,
) -> pd.DataFrame:
    """Clasifica con IA las filas indicadas (o todas)."""
    idx = indices if indices is not None else df.index.tolist()
    filas = [df.loc[i].to_dict() for i in idx if i in df.index]
    if not filas:
        return df
    resultados = clasificar_filas_ia_sync(filas, on_progress=on_progress)
    return aplicar_clasificacion_ia(df, idx, resultados)