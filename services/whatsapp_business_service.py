"""WhatsApp Business Cloud API — envío automático de mensajes de texto."""

from __future__ import annotations

import time
from typing import Any

import httpx

from config import settings


class WhatsAppBusinessService:
    @classmethod
    def esta_configurado(cls) -> bool:
        return bool(
            settings.whatsapp_business_token.strip()
            and settings.whatsapp_phone_number_id.strip()
        )

    @classmethod
    def info_config(cls) -> dict[str, Any]:
        activa = cls.esta_configurado()
        pid = settings.whatsapp_phone_number_id.strip()
        return {
            "business_api_activa": activa,
            "phone_number_id": f"…{pid[-4:]}" if len(pid) > 4 else "",
            "api_version": settings.whatsapp_api_version,
        }

    @classmethod
    def _url_mensajes(cls) -> str:
        return (
            f"https://graph.facebook.com/{settings.whatsapp_api_version}"
            f"/{settings.whatsapp_phone_number_id}/messages"
        )

    @classmethod
    def enviar_texto(cls, telefono: str, mensaje: str) -> dict[str, Any]:
        if not cls.esta_configurado():
            raise ValueError(
                "WhatsApp Business API no está configurada. "
                "Agregue WHATSAPP_BUSINESS_TOKEN y WHATSAPP_PHONE_NUMBER_ID en Render."
            )

        numero = "".join(c for c in telefono if c.isdigit())
        if not numero:
            raise ValueError("Teléfono inválido para WhatsApp Business.")

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "text",
            "text": {"preview_url": False, "body": mensaje[:4096]},
        }
        headers = {
            "Authorization": f"Bearer {settings.whatsapp_business_token}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(cls._url_mensajes(), json=payload, headers=headers)

        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            err = data.get("error", {})
            detalle = err.get("message") or err.get("error_user_msg") or f"HTTP {resp.status_code}"
            raise ValueError(detalle)

        msg_id = ""
        if data.get("messages"):
            msg_id = data["messages"][0].get("id", "")

        return {"ok": True, "message_id": msg_id, "telefono": numero}

    @classmethod
    def enviar_lote(cls, items: list[dict[str, Any]], *, delay_seg: float = 1.5) -> dict[str, Any]:
        resultados: list[dict[str, Any]] = []
        enviados = 0
        fallidos = 0

        for i, it in enumerate(items):
            if i > 0:
                time.sleep(delay_seg)
            indice = it.get("indice", i + 1)
            tel = it.get("telefono_limpio") or it.get("telefono", "")
            mensaje = it.get("mensaje", "")
            try:
                r = cls.enviar_texto(tel, mensaje)
                resultados.append({**r, "indice": indice, "ok": True})
                enviados += 1
            except Exception as exc:
                resultados.append({
                    "ok": False,
                    "indice": indice,
                    "telefono": tel,
                    "error": str(exc),
                })
                fallidos += 1

        return {"enviados": enviados, "fallidos": fallidos, "resultados": resultados}