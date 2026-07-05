"""
Servicio reutilizable de Respuesta IA / Diálogo con Claude.
Usar desde FastAPI, Streamlit o cualquier módulo del Centro de Operaciones.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import httpx

from config import settings
from services.whatsapp_service import WhatsAppService

RUTA_PLANTILLAS = Path(__file__).resolve().parent.parent / "data" / "plantillas_respuesta_ia.json"

SYSTEM_PROMPT = """Eres Director de Customer Experience de Óptica Los Andes Ecuador.
Generas seguimientos profesionales, empáticos y en tratamiento de USTED.

REGLAS:
- Validar emociones antes de proponer soluciones.
- Tono formal, cálido, natural — nunca robótico.
- Usar placeholders cuando falte dato: {cliente}, {telefono}, {local}, {asesor}.
- No inventar datos no presentes en el contexto.
- Evitar: "no sé", "no podemos", "cálmese", "eso no me corresponde".
- Español ecuatoriano.

Responde ÚNICAMENTE JSON válido (sin markdown):
{
  "dialogo": [{"actor": "asesor|cliente", "texto": "..."}],
  "mensaje_whatsapp": "mensaje con *negritas* y emojis moderados",
  "mensaje_correo": "cuerpo formal del correo",
  "asunto_correo": "asunto del correo",
  "mensaje_voz": "guión breve para llamada",
  "nota_asesor": "por qué este enfoque es efectivo"
}
"""


class RespuestaIAService:
    @staticmethod
    def ia_disponible() -> dict:
        return {
            "disponible": bool(settings.anthropic_api_key),
            "modelo": settings.anthropic_model,
        }

    @classmethod
    def _cargar_plantillas(cls) -> list[dict]:
        if not RUTA_PLANTILLAS.exists():
            return []
        with open(RUTA_PLANTILLAS, encoding="utf-8") as f:
            return json.load(f).get("plantillas", [])

    @classmethod
    def _guardar_plantillas(cls, plantillas: list[dict]) -> None:
        RUTA_PLANTILLAS.parent.mkdir(parents=True, exist_ok=True)
        with open(RUTA_PLANTILLAS, "w", encoding="utf-8") as f:
            json.dump({"plantillas": plantillas}, f, ensure_ascii=False, indent=2)

    @classmethod
    def listar_plantillas(cls, modulo: str = "") -> list[dict]:
        items = cls._cargar_plantillas()
        if modulo:
            items = [p for p in items if p.get("modulo") == modulo or not p.get("modulo")]
        return items

    @classmethod
    def guardar_plantilla(
        cls,
        *,
        nombre: str,
        modulo: str = "",
        mensaje_whatsapp: str = "",
        mensaje_correo: str = "",
        asunto_correo: str = "",
        metadata: dict | None = None,
    ) -> dict:
        plantillas = cls._cargar_plantillas()
        entry = {
            "id": str(uuid.uuid4())[:8],
            "nombre": nombre.strip(),
            "modulo": modulo,
            "mensaje_whatsapp": mensaje_whatsapp,
            "mensaje_correo": mensaje_correo,
            "asunto_correo": asunto_correo,
            "creada_en": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "metadata": metadata or {},
        }
        plantillas.insert(0, entry)
        cls._guardar_plantillas(plantillas)
        return entry

    @classmethod
    def _aplicar_placeholders(cls, texto: str, ctx: dict) -> str:
        mapping = {
            "cliente": ctx.get("cliente_nombre") or "{cliente}",
            "telefono": ctx.get("telefono") or "{telefono}",
            "local": ctx.get("local") or "{local}",
            "asesor": ctx.get("asesor") or settings.default_asesor,
            "email": ctx.get("email") or "{email}",
            "problema": ctx.get("problema") or "{problema}",
        }
        out = texto or ""
        for k, v in mapping.items():
            out = out.replace(f"{{{k}}}", str(v))
        return out

    @classmethod
    def _contexto_texto(cls, ctx: dict, titulo_modulo: str = "") -> str:
        lineas = [
            f"MÓDULO: {titulo_modulo or ctx.get('modulo', 'general')}",
            f"ID CASO: {ctx.get('caso_id', 'N/D')}",
            f"CLIENTE: {ctx.get('cliente_nombre', '{cliente}')}",
            f"TELÉFONO: {ctx.get('telefono', '{telefono}')}",
            f"EMAIL: {ctx.get('email', '')}",
            f"LOCAL: {ctx.get('local', '')}",
            f"ASESOR: {ctx.get('asesor', settings.default_asesor)}",
            f"PROBLEMA: {ctx.get('problema', '')}",
            f"DESCRIPCIÓN: {ctx.get('descripcion', '')}",
            f"COMENTARIO CLIENTE: {ctx.get('comentario_cliente', '')}",
            f"HISTORIAL: {ctx.get('historial', '')}",
            f"CALIFICACIÓN: {ctx.get('calificacion', '')}",
            f"CLASIFICACIÓN: {ctx.get('clasificacion', '')}",
            f"ESTADO: {ctx.get('estado', '')}",
            f"SOLUCIÓN ACTUAL: {ctx.get('solucion_actual', '')}",
            f"CONTEXTO EXTRA: {ctx.get('contexto_extra', '')}",
            f"CANAL SOLICITADO: {ctx.get('canal', 'whatsapp')}",
        ]
        return "\n".join(lineas)

    @classmethod
    def _plantilla_fallback(cls, ctx: dict) -> dict:
        cliente = ctx.get("cliente_nombre") or "{cliente}"
        telefono = ctx.get("telefono") or "{telefono}"
        local = ctx.get("local") or "{local}"
        asesor = ctx.get("asesor") or settings.default_asesor
        problema = ctx.get("problema") or ctx.get("comentario_cliente") or "su caso"
        dialogo = [
            {"actor": "asesor", "texto": f"Buenos días/tardes, ¿hablo con {cliente}? Le habla {asesor} de Óptica Los Andes, {local}."},
            {"actor": "asesor", "texto": f"Me comunico respecto a: {problema}. Comprendo su situación y estoy aquí para ayudarle."},
            {"actor": "cliente", "texto": "Sí, quisiera una solución clara."},
            {"actor": "asesor", "texto": "Gracias por su tiempo. Permítame confirmar los pasos y le mantengo informado/a."},
            {"actor": "asesor", "texto": "Ha sido un gusto atenderle. Gracias por confiar en Óptica Los Andes."},
        ]
        wa = (
            f"Buenos días/tardes, *{cliente}*. 👋\n\n"
            f"Le saluda *{asesor}* de *{local}*, Óptica Los Andes.\n\n"
            f"Nos comunicamos por: *{problema}*.\n"
            f"*Comprendemos* su situación y estamos gestionando la mejor solución 🤝\n\n"
            f"📞 Contacto: {telefono}\n"
            f"En breve le confirmamos los pasos ✅"
        )
        correo = (
            f"Estimado/a {cliente},\n\n"
            f"Le escribimos desde {local} en relación con: {problema}.\n"
            f"Comprendemos la importancia de su caso y estamos trabajando en la solución.\n\n"
            f"Puede contactarnos al {telefono}.\n\n"
            f"Atentamente,\n{asesor}\nÓptica Los Andes"
        )
        return {
            "dialogo": dialogo,
            "mensaje_whatsapp": wa,
            "mensaje_correo": correo,
            "asunto_correo": f"Seguimiento de su caso — Óptica Los Andes",
            "mensaje_voz": f"Buenos días, {cliente}. Le habla {asesor}. Me comunico por {problema}. Comprendo su situación y le confirmaré los pasos en breve.",
            "nota_asesor": "Plantilla CX estándar. Configure ANTHROPIC_API_KEY para personalización con Claude.",
        }

    @classmethod
    def _parse_json_ia(cls, texto: str) -> dict:
        limpio = texto.strip()
        limpio = re.sub(r"^```(?:json)?\s*", "", limpio)
        limpio = re.sub(r"\s*```$", "", limpio)
        match = re.search(r"\{[\s\S]*\}", limpio)
        if not match:
            raise RuntimeError("IA sin JSON válido")
        raw = match.group()
        for candidato in (raw, re.sub(r",\s*}", "}", raw), re.sub(r",\s*]", "]", raw)):
            try:
                return json.loads(candidato)
            except json.JSONDecodeError:
                continue
        raise RuntimeError("IA sin JSON válido")

    @classmethod
    async def _llamar_claude(cls, prompt: str) -> dict:
        payload = {
            "model": settings.anthropic_model,
            "max_tokens": 2048,
            "system": SYSTEM_PROMPT,
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
        return cls._parse_json_ia(resp.json()["content"][0]["text"])

    @classmethod
    async def generar(
        cls,
        contexto: dict,
        *,
        titulo_modulo: str = "",
        guardar_como_plantilla: bool = False,
        nombre_plantilla: str = "",
    ) -> dict:
        ctx = dict(contexto)
        if settings.anthropic_api_key:
            prompt = (
                f"{cls._contexto_texto(ctx, titulo_modulo)}\n\n"
                "Genera diálogo asesor-cliente (8-12 líneas) y mensajes listos para enviar. "
                "Incluye placeholders solo si un dato no está en el contexto."
            )
            try:
                resultado = await cls._llamar_claude(prompt)
                generado_por = "claude"
            except Exception:
                resultado = cls._plantilla_fallback(ctx)
                generado_por = "plantilla"
        else:
            resultado = cls._plantilla_fallback(ctx)
            generado_por = "plantilla"

        for campo in ("mensaje_whatsapp", "mensaje_correo", "asunto_correo", "mensaje_voz", "nota_asesor"):
            if campo in resultado:
                resultado[campo] = cls._aplicar_placeholders(str(resultado[campo]), ctx)

        dialogo = [
            {"actor": d.get("actor", "asesor"), "texto": cls._aplicar_placeholders(d.get("texto", ""), ctx)}
            for d in resultado.get("dialogo", [])
            if d.get("texto")
        ]

        telefono = ctx.get("telefono", "")
        wa_link = ""
        if telefono and telefono not in ("{telefono}", ""):
            wa_link = WhatsAppService.generar_enlace(telefono, resultado.get("mensaje_whatsapp", ""))

        plantilla_id = None
        if guardar_como_plantilla and nombre_plantilla:
            p = cls.guardar_plantilla(
                nombre=nombre_plantilla,
                modulo=ctx.get("modulo", ""),
                mensaje_whatsapp=resultado.get("mensaje_whatsapp", ""),
                mensaje_correo=resultado.get("mensaje_correo", ""),
                asunto_correo=resultado.get("asunto_correo", ""),
                metadata={"caso_id": ctx.get("caso_id"), "generado_por": generado_por},
            )
            plantilla_id = p["id"]

        return {
            "dialogo": dialogo,
            "mensaje_whatsapp": resultado.get("mensaje_whatsapp", ""),
            "mensaje_correo": resultado.get("mensaje_correo", ""),
            "asunto_correo": resultado.get("asunto_correo", ""),
            "mensaje_voz": resultado.get("mensaje_voz", ""),
            "nota_asesor": resultado.get("nota_asesor", ""),
            "wa_link": wa_link,
            "generado_por": generado_por,
            "plantilla_id": plantilla_id,
        }

    @classmethod
    def generar_sync(cls, contexto: dict, **kwargs) -> dict:
        import asyncio
        return asyncio.run(cls.generar(contexto, **kwargs))

    @staticmethod
    def dialogo_a_texto(resultado: dict) -> str:
        partes = []
        for d in resultado.get("dialogo", []):
            actor = "Asesor" if d.get("actor") == "asesor" else "Cliente"
            partes.append(f"{actor}: {d.get('texto', '')}")
        if resultado.get("mensaje_whatsapp"):
            partes.append("\n--- WHATSAPP ---\n" + resultado["mensaje_whatsapp"])
        if resultado.get("mensaje_correo"):
            asunto = resultado.get("asunto_correo", "")
            partes.append(f"\n--- CORREO ---\nAsunto: {asunto}\n" + resultado["mensaje_correo"])
        if resultado.get("nota_asesor"):
            partes.append("\n💡 " + resultado["nota_asesor"])
        return "\n\n".join(partes)

    @staticmethod
    def contexto_desde_fila(fila: dict, modulo: str, **extra) -> dict:
        """Helper: convierte una fila de DataFrame/dict del módulo a ContextoCaso."""
        return {
            "modulo": modulo,
            "caso_id": str(fila.get("id", "")),
            "cliente_nombre": fila.get("cliente") or fila.get("cliente_nombre") or "{cliente}",
            "telefono": fila.get("telefono") or "{telefono}",
            "email": fila.get("email", ""),
            "local": fila.get("local") or fila.get("tienda", ""),
            "asesor": fila.get("asesor", ""),
            "comentario_cliente": fila.get("mensaje_telegram") or fila.get("comentario") or "",
            "historial": fila.get("historial", ""),
            "calificacion": str(fila.get("calificacion", "")),
            "problema": fila.get("problema", ""),
            "descripcion": fila.get("descripcion", ""),
            "clasificacion": fila.get("clasificacion", ""),
            "estado": fila.get("estado_gestion") or fila.get("estado", ""),
            "solucion_actual": fila.get("solucion", ""),
            "contexto_extra": extra.get("contexto_extra", ""),
            "canal": extra.get("canal", "whatsapp"),
        }