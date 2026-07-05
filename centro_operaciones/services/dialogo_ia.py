"""Generación de diálogos de seguimiento con Claude."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from config import settings
except ImportError:
    settings = None

SYSTEM = """Eres asesor senior de Customer Experience en Óptica Los Andes Ecuador.
Generas seguimientos empáticos, profesionales y en tratamiento de USTED.
Valida emociones, ofrece solución concreta y cierre amable.
Nunca uses: "no sé", "no podemos", "cálmese", "eso no me corresponde".

Responde SOLO JSON válido (sin markdown):
{
  "dialogo": [{"actor": "asesor|cliente", "texto": "..."}],
  "mensaje_whatsapp": "texto listo para WhatsApp con *negritas* y emojis moderados",
  "mensaje_correo": "asunto y cuerpo de correo formal",
  "nota_asesor": "consejo breve"
}
"""


def _plantilla_seguimiento(fila: dict, canal: str) -> dict:
    cliente = fila.get("cliente") or "estimado/a cliente"
    problema = fila.get("problema") or "su caso"
    local = fila.get("local") or "su tienda"
    asesor = fila.get("asesor") or "Asesor Óptica Los Andes"
    dialogo = [
        {"actor": "asesor", "texto": f"Buenos días/tardes, ¿hablo con {cliente}? Le habla {asesor} de Óptica Los Andes, {local}."},
        {"actor": "asesor", "texto": f"Me comunico por la alerta relacionada con: {problema}. Comprendo su situación y estoy aquí para ayudarle."},
        {"actor": "cliente", "texto": "Sí, es sobre eso. Quisiera una solución."},
        {"actor": "asesor", "texto": "Gracias por atender mi llamada. Permítame confirmar los pasos y le mantengo informado/a sin demoras."},
        {"actor": "asesor", "texto": "Ha sido un gusto atenderle. Gracias por confiar en Óptica Los Andes."},
    ]
    wa = (
        f"Buenos días/tardes, *{cliente}*. 👋\n\n"
        f"Le saluda *{asesor}* de *{local}*, Óptica Los Andes.\n\n"
        f"Nos comunicamos por su caso: *{problema}*.\n"
        f"*Comprendemos* su situación y estamos trabajando en la mejor solución 🤝\n\n"
        f"En breve le confirmamos los pasos concretos ✅"
    )
    correo = (
        f"Asunto: Seguimiento de su caso — Óptica Los Andes\n\n"
        f"Estimado/a {cliente},\n\n"
        f"Le escribimos desde {local} en relación con: {problema}.\n"
        f"Comprendemos la importancia de su caso y estamos gestionando la solución.\n\n"
        f"Atentamente,\n{asesor}\nÓptica Los Andes"
    )
    return {
        "dialogo": dialogo,
        "mensaje_whatsapp": wa,
        "mensaje_correo": correo,
        "nota_asesor": "Plantilla CX (configure ANTHROPIC_API_KEY para personalización con Claude).",
        "canal": canal,
    }


def _parse_json(texto: str) -> dict:
    limpio = texto.strip()
    limpio = re.sub(r"^```(?:json)?\s*", "", limpio)
    limpio = re.sub(r"\s*```$", "", limpio)
    match = re.search(r"\{[\s\S]*\}", limpio)
    if not match:
        raise RuntimeError("IA sin JSON válido")
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return json.loads(re.sub(r",\s*}", "}", match.group()))


async def generar_dialogo_seguimiento(fila: dict, canal: str = "WhatsApp") -> dict:
    canal = canal if canal in ("WhatsApp", "Correo") else "WhatsApp"
    if not settings or not settings.anthropic_api_key:
        return _plantilla_seguimiento(fila, canal)

    import httpx

    prompt = (
        f"CANAL PRIORITARIO: {canal}\n"
        f"CLIENTE: {fila.get('cliente', '')}\n"
        f"TELÉFONO: {fila.get('telefono', '')}\n"
        f"LOCAL: {fila.get('local', '')}\n"
        f"ÁREA: {fila.get('area', '')}\n"
        f"PROBLEMA: {fila.get('problema', '')}\n"
        f"DESCRIPCIÓN: {fila.get('descripcion', '')}\n"
        f"MENSAJE TELEGRAM: {fila.get('mensaje_telegram', '')}\n"
        f"CLASIFICACIÓN: {fila.get('clasificacion', '')}\n"
        f"ESTADO: {fila.get('estado_gestion', '')}\n"
        f"SOLUCIÓN ACTUAL: {fila.get('solucion', '')}\n"
        f"ASESOR: {fila.get('asesor', '') or 'Asesor Óptica Los Andes'}\n\n"
        "Genera diálogo de seguimiento empático (8-12 líneas) y mensajes listos para enviar."
    )
    payload = {
        "model": settings.anthropic_model,
        "max_tokens": 2048,
        "system": SYSTEM,
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
        return _plantilla_seguimiento(fila, canal)
    try:
        data = _parse_json(resp.json()["content"][0]["text"])
    except Exception:
        return _plantilla_seguimiento(fila, canal)
    data["canal"] = canal
    data["generado_por"] = "claude"
    return data


def generar_dialogo_sync(fila: dict, canal: str = "WhatsApp") -> dict:
    import asyncio
    return asyncio.run(generar_dialogo_seguimiento(fila, canal))


def dialogo_a_texto(resultado: dict) -> str:
    lineas = []
    for d in resultado.get("dialogo", []):
        actor = "Asesor" if d.get("actor") == "asesor" else "Cliente"
        lineas.append(f"{actor}: {d.get('texto', '')}")
    canal = resultado.get("canal", "WhatsApp")
    if canal == "Correo" and resultado.get("mensaje_correo"):
        lineas.append("\n--- CORREO ---\n" + resultado["mensaje_correo"])
    elif resultado.get("mensaje_whatsapp"):
        lineas.append("\n--- WHATSAPP ---\n" + resultado["mensaje_whatsapp"])
    if resultado.get("nota_asesor"):
        lineas.append("\n💡 " + resultado["nota_asesor"])
    return "\n\n".join(lineas)