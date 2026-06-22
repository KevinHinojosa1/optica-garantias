import base64
import json
import re

import httpx

from config import settings

POLITICAS_PROMPT = """
Eres un experto en garantías de Óptica Los Andes Ecuador. Analiza la imagen del producto óptico dañado.

REGLAS DE GARANTÍA:

✅ GARANTÍA APLICA (proveedor cubre 1 año desde factura):
- Fisura en montura/armazón sin evidencia de golpe
- Desprendimiento de capa AR (anti-reflejo) sin rayas ni químicos
- Defecto de fabricación en bisagras o soldaduras
- Fisura en perforación o bordes del lente (excepto CR39, hasta 6 meses)
- Defecto en borde de lente de contacto (reclamo dentro de 24h con caja)
- Diferente tonalidad entre lentes de contacto (defecto de fábrica)

❌ GARANTÍA NO APLICA:
- Lente craquelado (red de microfisuras por golpe, calor o mal almacenamiento)
- Lente picado (impactos puntuales, rayaduras visibles)
- Rayas por uso o limpieza inadecuada
- Uso de sprays o agentes químicos detectados
- Reparación previa por terceros no autorizados
- Producto con descuento >= 30%
- Producto en promoción 2x1 con precio $0

⏰ PLAZOS ESPECIALES:
- Gafas cambio de modelo: SOLO 3 días hábiles
- Adaptación medida lentes oftálmicos: 1 mes
- Desprendimiento AR: 12 meses desde entrega
- Fisuras bordes (no CR39): 6 meses
- Armazones/gafas defecto fábrica: 1 año desde factura
- Lentes de contacto defecto: máximo 24 horas

Responde ÚNICAMENTE en JSON válido con este formato:
{
  "veredicto": "APLICA" | "NO APLICA" | "IMAGEN NO CLARA",
  "motivo": "descripción del daño detectado",
  "fundamento": "artículo de política que aplica",
  "confianza": 0-100,
  "tipo_dano": "clasificación del daño"
}
Si confianza < 70, usa veredicto "IMAGEN NO CLARA".
"""


class VisionService:
    @staticmethod
    def _extract_json(text: str) -> dict:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError("La IA no devolvió un JSON válido")

    @staticmethod
    def _normalizar_mime(mime_type: str) -> str:
        allowed = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        if mime_type in allowed:
            return mime_type
        return "image/jpeg"

    @staticmethod
    def _contexto_texto(contexto_cliente: dict) -> str:
        return (
            f"Analiza este producto dañado.\n"
            f"Cliente: {contexto_cliente.get('nombre')}\n"
            f"Producto: {contexto_cliente.get('producto')}\n"
            f"Tipo: {contexto_cliente.get('tipo_producto')}\n"
            f"Fecha factura: {contexto_cliente.get('fecha_factura')}\n"
            f"Días desde factura: {contexto_cliente.get('dias_desde_factura')}\n"
            f"OLA Plus: {'Sí' if contexto_cliente.get('tiene_ola_plus') else 'No'}\n"
            f"Dentro garantía general: {contexto_cliente.get('dentro_garantia')}\n"
        )

    @classmethod
    def _post_procesar(cls, result: dict) -> dict:
        confianza = int(result.get("confianza", 0))
        if confianza < 70 and result.get("veredicto") != "IMAGEN NO CLARA":
            result["veredicto"] = "IMAGEN NO CLARA"
            result["motivo"] = (
                result.get("motivo", "")
                + " — Confianza insuficiente. Solicite una segunda foto con mejor iluminación."
            ).strip()
        result["confianza"] = confianza
        return result

    @classmethod
    def _analisis_demo(cls, contexto_cliente: dict) -> dict:
        dentro = contexto_cliente.get("dentro_garantia", False)
        ola = contexto_cliente.get("tiene_ola_plus", False)
        if not dentro and not ola:
            return {
                "veredicto": "NO APLICA",
                "motivo": "Producto fuera del período de garantía estándar",
                "fundamento": "Garantía del proveedor: 1 año desde fecha de facturación",
                "confianza": 85,
                "tipo_dano": "fuera de tiempo",
                "modo": "demo",
            }
        return {
            "veredicto": "IMAGEN NO CLARA",
            "motivo": "Configure ANTHROPIC_API_KEY o XAI_API_KEY en .env para análisis real.",
            "fundamento": "Se requiere imagen clara para clasificar el daño según políticas de garantía",
            "confianza": 50,
            "tipo_dano": "pendiente de análisis",
            "modo": "demo",
        }

    @classmethod
    def _resolver_proveedor(cls) -> str | None:
        provider = settings.vision_provider.lower()
        if provider == "claude" and settings.anthropic_api_key:
            return "claude"
        if provider == "xai" and settings.xai_api_key:
            return "xai"
        if provider == "auto":
            if settings.anthropic_api_key:
                return "claude"
            if settings.xai_api_key:
                return "xai"
        return None

    @classmethod
    async def _analizar_claude(
        cls,
        image_bytes: bytes,
        mime_type: str,
        contexto_cliente: dict,
    ) -> dict:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        media_type = cls._normalizar_mime(mime_type)

        payload = {
            "model": settings.anthropic_model,
            "max_tokens": 1024,
            "system": POLITICAS_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": cls._contexto_texto(contexto_cliente),
                        },
                    ],
                }
            ],
        }

        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.anthropic_api_base}/messages",
                headers=headers,
                json=payload,
            )

        if response.status_code != 200:
            raise ValueError(f"Error Claude API ({response.status_code}): {response.text}")

        data = response.json()
        content = data["content"][0]["text"]
        result = cls._extract_json(content)
        result["proveedor"] = "claude"
        return cls._post_procesar(result)

    @classmethod
    async def _analizar_xai(
        cls,
        image_bytes: bytes,
        mime_type: str,
        contexto_cliente: dict,
    ) -> dict:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64}"

        payload = {
            "model": settings.xai_vision_model,
            "messages": [
                {"role": "system", "content": POLITICAS_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": cls._contexto_texto(contexto_cliente)},
                        {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
                    ],
                },
            ],
            "temperature": 0.2,
        }

        headers = {
            "Authorization": f"Bearer {settings.xai_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.xai_api_base}/chat/completions",
                headers=headers,
                json=payload,
            )

        if response.status_code != 200:
            raise ValueError(f"Error xAI API ({response.status_code}): {response.text}")

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        result = cls._extract_json(content)
        result["proveedor"] = "xai"
        return cls._post_procesar(result)

    @classmethod
    async def analizar_imagen(
        cls,
        image_bytes: bytes,
        mime_type: str,
        contexto_cliente: dict,
    ) -> dict:
        proveedor = cls._resolver_proveedor()
        if not proveedor:
            return cls._analisis_demo(contexto_cliente)

        if proveedor == "claude":
            return await cls._analizar_claude(image_bytes, mime_type, contexto_cliente)
        return await cls._analizar_xai(image_bytes, mime_type, contexto_cliente)