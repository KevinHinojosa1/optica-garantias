import httpx

from config import settings
from services.scripts_service import ScriptsService
from services.whatsapp_service import WhatsAppService

SYSTEM_PROMPT = """Eres un asesor experto de Óptica Los Andes Ecuador.
Generas respuestas para clientes molestos o en situaciones difíciles.

REGLAS OBLIGATORIAS:
- Tratamiento de USTED siempre (nunca tú/te/tu).
- Tono cálido, empático, humano y profesional — nunca robótico.
- Usa emojis con moderación (2-4 por mensaje).
- Valida la emoción del cliente antes de ofrecer solución.
- Ofrece pasos concretos y compromiso de seguimiento.
- No inventes datos que no estén en la ficha del cliente.
- Responde en español ecuatoriano natural.

FORMATO DE SALIDA (JSON estricto, sin markdown):
{
  "mensaje_voz": "texto para leer en llamada, 3-5 oraciones",
  "cuerpo_whatsapp": "solo el cuerpo del mensaje WhatsApp (SIN encabezado de ficha ni pie)"
}
"""


class ScriptsAiService:
    @classmethod
    def _ficha_texto(cls, ficha: dict) -> str:
        lineas = [
            f"Cliente: {ficha.get('nombre', 'N/D')}",
            f"Cédula: {ficha.get('cedula', 'N/D')}",
            f"Teléfono: {ficha.get('telefono', 'N/D')}",
            f"Tienda: {ficha.get('tienda', 'N/D')}",
            f"Producto: {ficha.get('producto', 'N/D')}",
            f"Tipo: {ficha.get('tipo_producto', 'N/D')}",
            f"Factura: {ficha.get('numero_factura', 'N/D')} | {ficha.get('fecha_factura', 'N/D')}",
            f"Estado garantía: {ficha.get('estado_garantia', 'N/D')}",
        ]
        if ficha.get("veredicto"):
            lineas.append(f"Veredicto historial: {ficha['veredicto']}")
        if ficha.get("motivo"):
            lineas.append(f"Motivo: {ficha['motivo']}")
        return "\n".join(lineas)

    @classmethod
    async def _llamar_claude(cls, prompt_usuario: str) -> dict:
        payload = {
            "model": settings.anthropic_model,
            "max_tokens": 1024,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt_usuario}],
        }
        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.anthropic_api_base}/messages",
                headers=headers,
                json=payload,
            )
        if response.status_code != 200:
            raise RuntimeError(f"Error IA: {response.text[:300]}")
        texto = response.json()["content"][0]["text"]
        import json
        import re

        match = re.search(r"\{[\s\S]*\}", texto)
        if not match:
            raise RuntimeError("La IA no devolvió JSON válido.")
        return json.loads(match.group())

    @classmethod
    def _respuesta_plantilla(cls, mensaje_cliente: str, ficha: dict, asesor: str) -> dict:
        nombre = ficha.get("nombre") or "estimado/a cliente"
        asesor_n = asesor or "su asesor de Óptica Los Andes"
        return {
            "mensaje_voz": (
                f"Buenos días/tardes, {nombre}. Le habla {asesor_n}. "
                f"Comprendo perfectamente lo que usted me indica y tiene toda la razón en sentirse así. "
                f"Permítame revisar su caso de {ficha.get('producto', 'su pedido')} y en breve le confirmo "
                f"los pasos para resolverlo. No se preocupe, estoy pendiente de usted."
            ),
            "cuerpo_whatsapp": (
                f"Buenos días/tardes, {nombre}. 👋\n\n"
                f"Comprendo perfectamente su mensaje y lamento la situación 😔\n\n"
                f"📝 *Usted nos escribió:*\n\"{mensaje_cliente[:200]}\"\n\n"
                f"Estoy revisando su caso personalmente y en breve le confirmaré los pasos para resolverlo ✅\n\n"
                f"No se preocupe, estamos pendientes de usted 🤝"
            ),
        }

    @classmethod
    async def generar_respuesta(
        cls,
        *,
        mensaje_cliente: str,
        ficha: dict,
        asesor: str = "",
        escenario: str = "",
        contexto_adicional: str = "",
    ) -> dict:
        cliente_dict = ScriptsService.ficha_a_cliente_dict(ficha)
        asesor_n = asesor.strip() or settings.default_asesor

        if settings.anthropic_api_key:
            prompt = (
                f"FICHA DEL CLIENTE:\n{cls._ficha_texto(ficha)}\n\n"
                f"ASESOR: {asesor_n}\n"
                f"ESCENARIO: {escenario or 'Atención general'}\n"
                f"CONTEXTO ADICIONAL: {contexto_adicional or 'Ninguno'}\n\n"
                f"MENSAJE DEL CLIENTE:\n\"{mensaje_cliente}\"\n\n"
                "Genera una respuesta empática en voz y cuerpo WhatsApp."
            )
            try:
                resultado = await cls._llamar_claude(prompt)
                generado_por = "ia"
            except Exception:
                resultado = cls._respuesta_plantilla(mensaje_cliente, ficha, asesor_n)
                generado_por = "plantilla"
        else:
            resultado = cls._respuesta_plantilla(mensaje_cliente, ficha, asesor_n)
            generado_por = "plantilla"

        cuerpo = resultado.get("cuerpo_whatsapp", "").strip()
        mensaje_whatsapp = WhatsAppService.mensaje_scripts_completo(cliente_dict, cuerpo, asesor_n)
        telefono = ficha.get("telefono", "")
        wa_link = WhatsAppService.generar_enlace(telefono, mensaje_whatsapp) if telefono else ""

        return {
            "mensaje_voz": resultado.get("mensaje_voz", "").strip(),
            "mensaje_whatsapp": mensaje_whatsapp,
            "wa_link": wa_link,
            "generado_por": generado_por,
        }