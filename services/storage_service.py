from supabase import create_client, Client
from config import settings
import uuid

class StorageService:
    # Use a fixed bucket name as requested
    BUCKET_NAME = "optica-consultas"
    
    @classmethod
    def get_client(cls) -> Client | None:
        if not settings.supabase_url or not settings.supabase_key:
            return None
        try:
            return create_client(settings.supabase_url, settings.supabase_key)
        except Exception as e:
            print(f"Error creating Supabase client: {e}")
            return None

    @classmethod
    def subir_imagen_consulta(cls, file_bytes: bytes, extension: str = ".jpg") -> str | None:
        """Sube una imagen a Supabase Storage y retorna la URL publica. Si falla o no está config, retorna None."""
        client = cls.get_client()
        if not client:
            return None
            
        filename = f"{uuid.uuid4().hex}{extension}"
        content_type = "image/jpeg"
        if extension.lower() == ".png":
            content_type = "image/png"
        elif extension.lower() == ".webp":
            content_type = "image/webp"

        try:
            # Subir archivo
            client.storage.from_(cls.BUCKET_NAME).upload(
                path=filename,
                file=file_bytes,
                file_options={"content-type": content_type}
            )
            # Obtener URL pública
            url = client.storage.from_(cls.BUCKET_NAME).get_public_url(filename)
            return url
        except Exception as e:
            print(f"Error subiendo a Supabase Storage: {e}")
            return None
