import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/optica_garantias.db"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_api_base: str = "https://api.anthropic.com/v1"
    xai_api_key: str = ""
    xai_api_base: str = "https://api.x.ai/v1"
    xai_vision_model: str = "grok-2-vision-1212"
    vision_provider: str = "claude"  # claude | xai | auto
    app_name: str = "Óptica Los Andes - Gestión de Garantías"
    app_host: str = "0.0.0.0"
    app_port: int = int(os.getenv("PORT", "8000"))
    debug: bool = False
    default_asesor: str = "Asesor Virtual"
    base_datos_dir: str = "data/base_datos"
    base_datos_archivo: str = "pacientes.xlsx"
    consultas_imagenes_dir: str = "data/consultas"
    base_dir: Path = BASE_DIR
    google_credentials_path: str = ""
    google_spreadsheet_id: str = ""
    google_sheet_ivr_name: str = "IVR Verificaciones"


settings = Settings()