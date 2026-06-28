import json
import re

import httpx

from config import settings
from services.scripts_service import ScriptsService
from services.whatsapp_service import WhatsAppService

DIALOGO_SYSTEM_PROMPT = """Eres Director de Customer Experience (CX) de Óptica Los Andes Ecuador.
Tienes 25+ años en servicio al cliente, postventa, PNL y resolución de conflictos en el sector óptico.

Generas diálogos naturales, empáticos y estratégicos — nunca robóticos ni fríos.

REGLAS OBLIGATORIAS:
- Tratamiento de USTED siempre.
- Validar emociones antes de proponer soluciones.
- Tono profesional, cálido, conversacional y seguro.
- No usar frases prohibidas: "no sé", "no podemos", "cálmese", "eso no me corresponde", etc.
- No inventar datos que no estén en el contexto del cliente.
- Español ecuatoriano natural.
- El diálogo debe tener 8-14 intercambios asesor/cliente con ramificaciones realistas.

FORMATO DE SALIDA: responde ÚNICAMENTE con JSON válido (sin markdown, sin texto extra).
Escapa comillas dentro de strings. Máximo 10 intercambios en dialogo.
{
  "dialogo": [
    {"actor": "asesor", "texto": "..."},
    {"actor": "cliente", "texto": "..."}
  ],
  "mensaje_voz": "guión consolidado para leer en llamada (fase solicitada)",
  "mensaje_whatsapp": "mensaje WhatsApp con *negritas* y emojis moderados",
  "nota_asesor": "consejo breve de por qué este enfoque es efectivo"
}
"""

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
    def _parse_json_ia(cls, texto: str) -> dict:
        limpio = texto.strip()
        limpio = re.sub(r"^```(?:json)?\s*", "", limpio)
        limpio = re.sub(r"\s*```$", "", limpio)
        if not limpio.startswith("{"):
            match = re.search(r"\{[\s\S]*\}", limpio)
            if not match:
                raise RuntimeError("La IA no devolvió JSON válido.")
            limpio = match.group()

        intentos = [
            limpio,
            re.sub(r",\s*}", "}", limpio),
            re.sub(r",\s*]", "]", limpio),
        ]
        for candidato in intentos:
            try:
                return json.loads(candidato)
            except json.JSONDecodeError:
                continue

        resultado: dict = {"dialogo": [], "mensaje_voz": "", "mensaje_whatsapp": "", "nota_asesor": ""}
        bloques = re.findall(
            r'\{\s*"actor"\s*:\s*"(asesor|cliente)"\s*,\s*"texto"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}',
            limpio,
        )
        if bloques:
            resultado["dialogo"] = [
                {"actor": actor, "texto": json.loads(f'"{texto}"')}
                for actor, texto in bloques
            ]
        for campo in ("mensaje_voz", "mensaje_whatsapp", "nota_asesor"):
            m = re.search(rf'"{campo}"\s*:\s*"((?:[^"\\]|\\.)*)"', limpio)
            if m:
                resultado[campo] = json.loads(f'"{m.group(1)}"')
        if resultado["dialogo"] or resultado["mensaje_voz"]:
            return resultado
        raise RuntimeError("La IA no devolvió JSON válido.")

    @classmethod
    async def _llamar_claude(
        cls,
        prompt_usuario: str,
        *,
        system: str = SYSTEM_PROMPT,
        max_tokens: int = 1024,
    ) -> dict:
        payload = {
            "model": settings.anthropic_model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt_usuario}],
        }
        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{settings.anthropic_api_base}/messages",
                headers=headers,
                json=payload,
            )
        if response.status_code != 200:
            raise RuntimeError(f"Error IA: {response.text[:300]}")
        texto = response.json()["content"][0]["text"]
        return cls._parse_json_ia(texto)

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

    @classmethod
    def _buscar_escenario(cls, escenario_id: str, grupo_id: str = "") -> tuple[dict, dict] | None:
        data = ScriptsService.cargar()
        for grupo in data.get("grupos", []):
            if grupo_id and grupo.get("id") != grupo_id:
                continue
            for esc in grupo.get("escenarios", []):
                if esc.get("id") == escenario_id:
                    return grupo, esc
        if grupo_id:
            return None
        for grupo in data.get("grupos", []):
            for esc in grupo.get("escenarios", []):
                if esc.get("id") == escenario_id:
                    return grupo, esc
        return None

    @classmethod
    def _variables_desde_ficha(cls, ficha: dict, asesor: str) -> dict[str, str]:
        return ScriptsService.ficha_a_variables(ficha, asesor)

    @classmethod
    def _personalizar(cls, texto: str, variables: dict[str, str]) -> str:
        return ScriptsService.personalizar(texto or "", variables)

    @classmethod
    def _dialogo_plantilla(cls, esc: dict, variables: dict[str, str], fase: str) -> dict:
        cx = esc.get("cx") or {}
        dialogo_raw = cx.get("guion") or []
        dialogo = [
            {
                "actor": linea.get("actor", "asesor"),
                "texto": cls._personalizar(linea.get("texto", ""), variables),
            }
            for linea in dialogo_raw
        ]
        fases = esc.get("fases") or {}
        fase_data = fases.get(fase) or fases.get("saludo") or {}
        return {
            "dialogo": dialogo,
            "mensaje_voz": cls._personalizar(fase_data.get("voz", ""), variables),
            "mensaje_whatsapp": cls._personalizar(fase_data.get("whatsapp", ""), variables),
            "nota_asesor": "Diálogo generado desde plantilla CX. Configure ANTHROPIC_API_KEY para personalización con Claude.",
        }

    @classmethod
    def _contexto_escenario(cls, grupo: dict, esc: dict) -> str:
        cx = esc.get("cx") or {}
        niveles = esc.get("niveles") or {}
        partes = [
            f"CATEGORÍA: {grupo.get('titulo', '')}",
            f"ESCENARIO: {esc.get('titulo', '')}",
            f"OBJETIVO: {esc.get('objetivo', esc.get('descripcion', ''))}",
            f"PERFIL EMOCIONAL: {', '.join(esc.get('perfil_emocional', []))}",
            f"NIVELES — Empatía: {niveles.get('empatia', 'N/D')}, Control: {niveles.get('control', 'N/D')}, Fidelización: {niveles.get('fidelizacion', 'N/D')}",
            f"DESCUBRIMIENTO: {cx.get('descubrimiento', '')}",
            f"SOLUCIÓN: {cx.get('solucion', '')}",
            f"CIERRE: {cx.get('cierre', '')}",
        ]
        if cx.get("objeciones"):
            obj = "\n".join(f"- {o.get('situacion')}: {o.get('respuesta')}" for o in cx["objeciones"][:5])
            partes.append(f"OBJECIONES FRECUENTES:\n{obj}")
        if cx.get("evitar"):
            ev = "\n".join(f"- NO: {e.get('frase')} → SÍ: {e.get('alternativa')}" for e in cx["evitar"][:5])
            partes.append(f"QUÉ EVITAR:\n{ev}")
        fases = esc.get("fases") or {}
        for nombre, textos in fases.items():
            partes.append(f"GUIÓN BASE {nombre.upper()} (voz): {textos.get('voz', '')}")
        return "\n\n".join(partes)

    @classmethod
    async def generar_dialogo(
        cls,
        *,
        escenario_id: str,
        grupo_id: str = "",
        ficha: dict,
        asesor: str = "",
        canal: str = "voz",
        fase: str = "saludo",
        contexto_adicional: str = "",
    ) -> dict:
        encontrado = cls._buscar_escenario(escenario_id, grupo_id)
        if not encontrado:
            raise ValueError("Escenario de script no encontrado.")

        grupo, esc = encontrado
        asesor_n = asesor.strip() or settings.default_asesor
        variables = cls._variables_desde_ficha(ficha, asesor_n)
        cliente_dict = ScriptsService.ficha_a_cliente_dict(ficha)

        if settings.anthropic_api_key:
            contexto = cls._contexto_escenario(grupo, esc)
            if len(contexto) > 3500:
                contexto = contexto[:3500] + "\n...[contexto recortado]"
            prompt = (
                f"CONTEXTO DEL SCRIPT:\n{contexto}\n\n"
                f"DATOS DEL CLIENTE:\n{cls._ficha_texto(ficha)}\n\n"
                f"ASESOR: {asesor_n}\n"
                f"CANAL PRIORITARIO: {canal}\n"
                f"FASE A ENFATIZAR: {fase}\n"
                f"CONTEXTO ADICIONAL DEL ASESOR: {contexto_adicional or 'Ninguno'}\n\n"
                "Genera un diálogo completo asesor-cliente adaptado a este escenario. "
                "Incluye reacciones del cliente (molesto, dudoso, conforme) y respuestas empáticas del asesor. "
                f"El mensaje_voz y mensaje_whatsapp deben corresponder a la fase '{fase}'."
            )
            try:
                resultado = await cls._llamar_claude(
                    prompt,
                    system=DIALOGO_SYSTEM_PROMPT,
                    max_tokens=4096,
                )
                generado_por = "claude"
            except Exception:
                resultado = cls._dialogo_plantilla(esc, variables, fase)
                generado_por = "plantilla"
        else:
            resultado = cls._dialogo_plantilla(esc, variables, fase)
            generado_por = "plantilla"

        dialogo = [
            {"actor": d.get("actor", "asesor"), "texto": d.get("texto", "").strip()}
            for d in resultado.get("dialogo", [])
            if d.get("texto", "").strip()
        ]
        mensaje_voz = resultado.get("mensaje_voz", "").strip()
        cuerpo_wa = resultado.get("mensaje_whatsapp", "").strip()

        if grupo.get("solo_asesor_cliente"):
            pie = f"\n\n👨‍💼 *Asesor:* {asesor_n}\n💙 *Gracias por confiar en Óptica Los Andes*"
            mensaje_whatsapp = f"{cuerpo_wa}{pie}" if cuerpo_wa else ""
            wa_link = ""
        else:
            mensaje_whatsapp = WhatsAppService.mensaje_scripts_completo(
                cliente_dict, cuerpo_wa, asesor_n
            )
            telefono = ficha.get("telefono", "")
            wa_link = WhatsAppService.generar_enlace(telefono, mensaje_whatsapp) if telefono else ""

        return {
            "dialogo": dialogo,
            "mensaje_voz": mensaje_voz,
            "mensaje_whatsapp": mensaje_whatsapp,
            "wa_link": wa_link,
            "generado_por": generado_por,
            "nota_asesor": resultado.get("nota_asesor", "").strip(),
        }