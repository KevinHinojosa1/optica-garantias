import json
from datetime import date, datetime
from pathlib import Path

from config import settings


class GoogleSheetsService:
    _client = None

    @classmethod
    def configurado(cls) -> bool:
        return bool(settings.google_spreadsheet_id and settings.google_credentials_path)

    @classmethod
    def _obtener_cliente(cls):
        if cls._client is not None:
            return cls._client
        if not cls.configurado():
            return None

        cred_path = Path(settings.google_credentials_path)
        if not cred_path.exists():
            return None

        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_file(str(cred_path), scopes=scopes)
            cls._client = gspread.authorize(creds)
            return cls._client
        except Exception:
            return None

    @classmethod
    def registrar_ivr(
        cls,
        *,
        fecha: date,
        hora: datetime,
        semana: str,
        tienda_nombre: str,
        ciudad: str,
        funciona: bool,
        comentario: str,
        verificado_por: str,
    ) -> dict:
        if not cls.configurado():
            return {"ok": False, "motivo": "Google Sheets no configurado"}

        client = cls._obtener_cliente()
        if not client:
            return {"ok": False, "motivo": "No se pudo conectar con Google Sheets"}

        try:
            sheet = client.open_by_key(settings.google_spreadsheet_id)
            try:
                ws = sheet.worksheet(settings.google_sheet_ivr_name)
            except Exception:
                ws = sheet.add_worksheet(
                    title=settings.google_sheet_ivr_name,
                    rows=1000,
                    cols=10,
                )
                ws.append_row(
                    [
                        "Fecha",
                        "Hora",
                        "Semana",
                        "Tienda",
                        "Ciudad",
                        "Estado IVR",
                        "Comentario",
                        "Verificado por",
                        "Timestamp UTC",
                    ]
                )

            estado = "✅ FUNCIONA" if funciona else "❌ NO FUNCIONA"
            ws.append_row(
                [
                    fecha.isoformat(),
                    hora.strftime("%H:%M:%S"),
                    semana,
                    tienda_nombre,
                    ciudad,
                    estado,
                    comentario or "",
                    verificado_por,
                    hora.isoformat(),
                ],
                value_input_option="USER_ENTERED",
            )
            return {"ok": True, "motivo": "Registrado en Google Sheets"}
        except Exception as exc:
            return {"ok": False, "motivo": str(exc)}