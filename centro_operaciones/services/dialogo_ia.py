"""Wrapper legacy — usa RespuestaIAService central."""

from __future__ import annotations

from services.respuesta_ia_service import RespuestaIAService


def generar_dialogo_sync(fila: dict, canal: str = "WhatsApp") -> dict:
    ctx = RespuestaIAService.contexto_desde_fila(
        fila, "alertas_telegram", canal=canal.lower()
    )
    return RespuestaIAService.generar_sync(ctx, titulo_modulo="Alertas Telegram")


def dialogo_a_texto(resultado: dict) -> str:
    return RespuestaIAService.dialogo_a_texto(resultado)