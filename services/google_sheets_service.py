import json
from datetime import date, datetime
from pathlib import Path

from config import settings


class GoogleSheetsService:
    _client = None

    @classmethod
    def configurado(cls) -> bool:
        if not settings.google_spreadsheet_id:
            return False
        if settings.google_credentials_json.strip():
            try:
                json.loads(settings.google_credentials_json)
                return True
            except json.JSONDecodeError:
                return False
        if settings.google_credentials_path:
            return Path(settings.google_credentials_path).exists()
        return False

    @classmethod
    def _cargar_credenciales(cls):
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        json_raw = settings.google_credentials_json.strip()
        if json_raw:
            info = json.loads(json_raw)
            return Credentials.from_service_account_info(info, scopes=scopes)

        cred_path = Path(settings.google_credentials_path)
        if cred_path.exists():
            return Credentials.from_service_account_file(str(cred_path), scopes=scopes)

        return None

    @classmethod
    def _obtener_cliente(cls):
        if cls._client is not None:
            return cls._client
        if not cls.configurado():
            return None

        try:
            import gspread

            creds = cls._cargar_credenciales()
            if not creds:
                return None
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
        comentario_auditoria: str = "",
        verificado_por: str = "",
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
                        "IVR Vale",
                        "Detalle gestión",
                        "Comentario auditoría",
                        "Verificado por",
                        "Timestamp UTC",
                    ]
                )

            ivr_vale = 1 if funciona else 0
            detalle = (comentario or "").strip() or ("Funciona" if funciona else "No funciona")
            ws.append_row(
                [
                    fecha.isoformat(),
                    hora.strftime("%H:%M:%S"),
                    semana,
                    tienda_nombre,
                    ciudad,
                    ivr_vale,
                    detalle,
                    comentario_auditoria or "",
                    verificado_por,
                    hora.isoformat(),
                ],
                value_input_option="USER_ENTERED",
            )
            return {"ok": True, "motivo": "Registrado en Google Sheets"}
        except Exception as exc:
            return {"ok": False, "motivo": str(exc)}