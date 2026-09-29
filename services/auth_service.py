import hmac
import hashlib
import json
import base64
import time
from typing import Optional

SECRET_KEY = "optica-los-andes-secret-key-sac-2026"

USUARIOS = {
    "miguel": {
        "username": "miguel",
        "nombre": "Miguel",
        "nombre_completo": "Miguel",
        "rol": "Jefe de SAC",
        "cargo": "Jefe de Servicio al Cliente",
        "avatar": "👔",
        "color": "indigo",
        "passwords": ["miguel2026", "miguel123", "optica123", "sac2026"],
    },
    "andrea": {
        "username": "andrea",
        "nombre": "Andrea",
        "nombre_completo": "Andrea",
        "rol": "Coordinadora",
        "cargo": "Coordinadora de SAC",
        "avatar": "📋",
        "color": "teal",
        "passwords": ["andrea2026", "andrea123", "optica123", "sac2026"],
    },
    "carla": {
        "username": "carla",
        "nombre": "Carla",
        "nombre_completo": "Carla",
        "rol": "Asistente",
        "cargo": "Asistente de SAC",
        "avatar": "👓",
        "color": "rose",
        "passwords": ["carla2026", "carla123", "optica123", "sac2026"],
    },
    "kevin": {
        "username": "kevin",
        "nombre": "Kevin",
        "nombre_completo": "Kevin",
        "rol": "Asistente",
        "cargo": "Asistente de SAC",
        "avatar": "🔍",
        "color": "blue",
        "passwords": ["kevin2026", "kevin123", "optica123", "sac2026"],
    },
}

class AuthService:
    @classmethod
    def listar_usuarios(cls) -> list[dict]:
        return [
            {
                "username": u["username"],
                "nombre": u["nombre"],
                "rol": u["rol"],
                "cargo": u["cargo"],
                "avatar": u["avatar"],
                "color": u["color"],
                "password_sugerida": u["passwords"][0],
            }
            for u in USUARIOS.values()
        ]

    @classmethod
    def autenticar(cls, username: str, password: str) -> Optional[dict]:
        user = USUARIOS.get((username or "").strip().lower())
        if not user:
            return None
        password_ingresada = (password or "").strip()
        if password_ingresada in user["passwords"]:
            return {
                "username": user["username"],
                "nombre": user["nombre"],
                "rol": user["rol"],
                "cargo": user["cargo"],
                "avatar": user["avatar"],
            }
        return None

    @classmethod
    def crear_token(cls, username: str) -> str:
        user = USUARIOS.get((username or "").strip().lower())
        if not user:
            return ""
        payload = {
            "username": user["username"],
            "nombre": user["nombre"],
            "rol": user["rol"],
            "ts": int(time.time()),
        }
        raw = base64.b64encode(json.dumps(payload).encode()).decode()
        signature = hmac.new(SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
        return f"{raw}.{signature}"

    @classmethod
    def validar_token(cls, token: str) -> Optional[dict]:
        if not token or "." not in token:
            return None
        try:
            raw, sig = token.split(".", 1)
            expected_sig = hmac.new(SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return None
            data = json.loads(base64.b64decode(raw.encode()).decode())
            user = USUARIOS.get(data.get("username", "").lower())
            if user:
                return {
                    "username": user["username"],
                    "nombre": user["nombre"],
                    "rol": user["rol"],
                    "cargo": user["cargo"],
                    "avatar": user["avatar"],
                }
            return None
        except Exception:
            return None
