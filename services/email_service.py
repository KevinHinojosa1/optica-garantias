"""Envío opcional de correos (SMTP) para reprogramaciones a tienda."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any
from urllib.parse import quote

from config import settings


class EmailService:
    @classmethod
    def esta_configurado(cls) -> bool:
        return bool(
            settings.smtp_host.strip()
            and settings.smtp_user.strip()
            and settings.smtp_password.strip()
        )

    @classmethod
    def info_config(cls) -> dict[str, Any]:
        return {
            "smtp_activo": cls.esta_configurado(),
            "smtp_host": settings.smtp_host or "",
            "smtp_from": settings.smtp_from or settings.smtp_user or "",
        }

    @classmethod
    def mailto_link(cls, destinatario: str, asunto: str, cuerpo: str) -> str:
        to = (destinatario or "").strip()
        return (
            f"mailto:{quote(to, safe='@.+-_')}"
            f"?subject={quote(asunto)}"
            f"&body={quote(cuerpo)}"
        )

    @classmethod
    def enviar(
        cls,
        *,
        destinatario: str,
        asunto: str,
        cuerpo: str,
        html: str = "",
    ) -> dict[str, Any]:
        if not cls.esta_configurado():
            raise ValueError(
                "SMTP no configurado. Use copiar correo o mailto, "
                "o agregue SMTP_HOST, SMTP_USER y SMTP_PASSWORD en Render."
            )
        dest = (destinatario or "").strip()
        if not dest or "@" not in dest:
            raise ValueError("Destinatario de correo inválido.")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"] = settings.smtp_from or settings.smtp_user
        msg["To"] = dest
        msg.attach(MIMEText(cuerpo, "plain", "utf-8"))
        if html:
            msg.attach(MIMEText(html, "html", "utf-8"))

        port = settings.smtp_port or 587
        with smtplib.SMTP(settings.smtp_host, port, timeout=30) as server:
            server.ehlo()
            if settings.smtp_use_tls:
                server.starttls()
                server.ehlo()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(msg["From"], [dest], msg.as_string())

        return {"ok": True, "destinatario": dest, "asunto": asunto}
