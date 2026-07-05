"""
Componente Streamlit reutilizable — Generar Diálogo con Claude / Sugerir Respuesta IA.

Uso en cualquier módulo:

    from centro_operaciones.components.respuesta_ia import render_panel_respuesta_ia

    contexto = {
        "modulo": "reclamos_activos",
        "caso_id": "42",
        "cliente_nombre": "Juan Pérez",
        "telefono": "0991234567",
        "comentario_cliente": "Llevo 2 semanas esperando mis lentes",
        ...
    }
    render_panel_respuesta_ia(contexto, titulo_modulo="Reclamos Activos", key_prefix="reclamos")
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.respuesta_ia_service import RespuestaIAService

try:
    from config import settings
except ImportError:
    settings = None


def _clipboard_js(texto: str) -> str:
    esc = texto.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    return f"""
    <script>
    navigator.clipboard.writeText(`{esc}`);
    </script>
    """


def render_panel_respuesta_ia(
    contexto: dict,
    *,
    titulo_modulo: str = "Centro de Operaciones",
    key_prefix: str = "ia",
    mostrar_dialogo: bool = True,
    etiqueta_boton: str = "✨ Generar Diálogo con Claude",
    etiqueta_alternativa: str = "💡 Sugerir Respuesta IA",
) -> dict | None:
    """
    Renderiza panel IA reutilizable. Retorna el último resultado generado o None.

    Parámetros
    ----------
    contexto : dict compatible con ContextoCaso (schemas/respuesta_ia.py)
    titulo_modulo : nombre visible del módulo
    key_prefix : prefijo único para keys de Streamlit (evitar colisiones entre módulos)
    """
    sk = f"{key_prefix}_resultado"
    estado_ia = RespuestaIAService.ia_disponible()

    with st.container(border=True):
        st.markdown(f"#### 🤖 Respuesta IA — {titulo_modulo}")
        if estado_ia["disponible"]:
            st.caption(f"Claude activo · {estado_ia['modelo']}")
        else:
            st.caption("⚠️ Sin API key — se usará plantilla empática estándar")

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            canal = st.selectbox("Canal", ["whatsapp", "correo", "ambos"], key=f"{key_prefix}_canal")
        with c2:
            ctx_extra = st.text_input(
                "Contexto adicional",
                placeholder="Ej: cliente molesto, segunda llamada...",
                key=f"{key_prefix}_extra",
            )
        with c3:
            nombre_plantilla = st.text_input(
                "Nombre plantilla (opcional)",
                placeholder="Seguimiento retraso lentes",
                key=f"{key_prefix}_plantilla",
            )

        ctx = {**contexto, "canal": canal, "contexto_extra": ctx_extra}

        b1, b2, b3 = st.columns(3)
        generar = b1.button(etiqueta_boton, type="primary", use_container_width=True, key=f"{key_prefix}_gen")
        sugerir = b2.button(etiqueta_alternativa, use_container_width=True, key=f"{key_prefix}_sug")

        if generar or sugerir:
            with st.spinner("Generando respuesta empática..."):
                resultado = RespuestaIAService.generar_sync(
                    ctx,
                    titulo_modulo=titulo_modulo,
                    guardar_como_plantilla=bool(nombre_plantilla.strip()),
                    nombre_plantilla=nombre_plantilla.strip(),
                )
                st.session_state[sk] = resultado
                if nombre_plantilla.strip():
                    st.success(f"Plantilla «{nombre_plantilla}» guardada (ID: {resultado.get('plantilla_id')})")

        resultado = st.session_state.get(sk)
        if not resultado:
            return None

        por = "Claude AI" if resultado.get("generado_por") == "claude" else "Plantilla CX"
        st.success(f"Generado con {por}")

        if mostrar_dialogo and resultado.get("dialogo"):
            with st.expander("💬 Diálogo generado", expanded=True):
                for linea in resultado["dialogo"]:
                    actor = "🧑‍💼 Asesor" if linea.get("actor") == "asesor" else "👤 Cliente"
                    st.markdown(f"**{actor}:** {linea.get('texto', '')}")

        tab_wa, tab_mail, tab_voz = st.tabs(["WhatsApp", "Correo", "Voz"])

        with tab_wa:
            msg_wa = resultado.get("mensaje_whatsapp", "")
            st.text_area("Mensaje WhatsApp", value=msg_wa, height=180, key=f"{key_prefix}_wa_txt")
            a1, a2, a3 = st.columns(3)
            if a1.button("📋 Copiar WhatsApp", key=f"{key_prefix}_copy_wa"):
                st.session_state[f"{key_prefix}_copiado"] = msg_wa
                st.toast("Texto listo — use Ctrl+C en el cuadro de arriba o el botón de descarga")
            a2.download_button(
                "⬇️ Descargar .txt",
                data=msg_wa,
                file_name=f"whatsapp_{key_prefix}.txt",
                key=f"{key_prefix}_dl_wa",
            )
            wa_link = resultado.get("wa_link", "")
            if wa_link:
                a3.link_button("💬 Enviar por WhatsApp", wa_link, use_container_width=True)
            else:
                a3.caption("Sin teléfono válido para enlace WA")

        with tab_mail:
            st.text_input("Asunto", value=resultado.get("asunto_correo", ""), key=f"{key_prefix}_asunto")
            st.text_area("Cuerpo correo", value=resultado.get("mensaje_correo", ""), height=180, key=f"{key_prefix}_mail")
            if st.button("📋 Copiar correo", key=f"{key_prefix}_copy_mail"):
                st.toast("Copie el asunto y cuerpo del cuadro superior")

        with tab_voz:
            st.text_area("Guión de llamada", value=resultado.get("mensaje_voz", ""), height=120, key=f"{key_prefix}_voz")

        if resultado.get("nota_asesor"):
            st.info(f"💡 **Nota para el asesor:** {resultado['nota_asesor']}")

        if st.button("💾 Guardar como plantilla ahora", key=f"{key_prefix}_save_tpl"):
            nombre = nombre_plantilla.strip() or f"{titulo_modulo} {contexto.get('caso_id', '')}"
            p = RespuestaIAService.guardar_plantilla(
                nombre=nombre,
                modulo=contexto.get("modulo", ""),
                mensaje_whatsapp=resultado.get("mensaje_whatsapp", ""),
                mensaje_correo=resultado.get("mensaje_correo", ""),
                asunto_correo=resultado.get("asunto_correo", ""),
            )
            st.success(f"Plantilla guardada: {p['nombre']} (ID {p['id']})")

        return resultado


def render_panel_desde_fila(
    fila: dict,
    modulo: str,
    *,
    titulo_modulo: str = "",
    key_prefix: str = "ia",
    contexto_extra: str = "",
) -> dict | None:
    """Atajo: construye contexto desde una fila de tabla y renderiza el panel."""
    ctx = RespuestaIAService.contexto_desde_fila(
        fila, modulo, contexto_extra=contexto_extra
    )
    return render_panel_respuesta_ia(
        ctx,
        titulo_modulo=titulo_modulo or modulo.replace("_", " ").title(),
        key_prefix=key_prefix,
    )