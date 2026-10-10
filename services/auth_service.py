import hmac
import hashlib
import json
import base64
import time
import os
import re
from typing import Optional, Tuple
from config import settings

# Diccionario de control de fuerza bruta en memoria
# Estructura: key -> {"intentos": int, "bloqueado_hasta": float, "ultimo_intento": float}
_INTENTOS_FALLIDOS: dict[str, dict] = {}
MAX_INTENTOS = 5
TIEMPO_BLOQUEO_SEGUNDOS = 15 * 60  # 15 minutos
DURACION_TOKEN_SEGUNDOS = 12 * 3600  # 12 horas
PBKDF2_ITERACIONES = 600_000
PREFIJO_HASH = "pbkdf2_sha256$"

_SECRET_KEY_EFIMERA = os.urandom(32).hex()

USUARIOS_METADATA = {
    "miguel": {
        "username": "miguel",
        "nombre": "Miguel",
        "rol": "Jefe de SAC",
        "cargo": "Jefe de Servicio al Cliente",
        "avatar": "👔",
        "color": "indigo",
    },
    "andrea": {
        "username": "andrea",
        "nombre": "Andrea",
        "rol": "Coordinadora",
        "cargo": "Coordinadora de SAC",
        "avatar": "📋",
        "color": "teal",
    },
    "carla": {
        "username": "carla",
        "nombre": "Carla",
        "rol": "Asistente",
        "cargo": "Asistente de SAC",
        "avatar": "👓",
        "color": "rose",
    },
    "kevin": {
        "username": "kevin",
        "nombre": "Kevin",
        "rol": "Asistente",
        "cargo": "Asistente de SAC",
        "avatar": "🔍",
        "color": "blue",
    },
}

def _secret_key() -> bytes:
    """SECRET_KEY del entorno; si falta, una clave aleatoria por proceso (las sesiones no sobreviven reinicios)."""
    return (settings.secret_key or _SECRET_KEY_EFIMERA).encode()


class AuthService:
    @staticmethod
    def hash_password(password: str, salt: bytes = None) -> str:
        """Hash PBKDF2-HMAC-SHA256 (600.000 iteraciones, OWASP) en formato pbkdf2_sha256$iter$salt$key."""
        salt = salt or os.urandom(16)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERACIONES)
        return f"{PREFIJO_HASH}{PBKDF2_ITERACIONES}${salt.hex()}${key.hex()}"

    @staticmethod
    def _verificar_password_hash(stored_hash: str, password_ingresada: str) -> bool:
        try:
            iteraciones, salt_hex, key_hex = stored_hash[len(PREFIJO_HASH):].split("$")
            key = hashlib.pbkdf2_hmac(
                "sha256", password_ingresada.encode("utf-8"), bytes.fromhex(salt_hex), int(iteraciones)
            )
            return hmac.compare_digest(key.hex(), key_hex)
        except Exception:
            return False

    @staticmethod
    def _password_configurada(username: str) -> str:
        return (getattr(settings, f"pass_{username.lower()}", "") or "").strip()

    @classmethod
    def _verificar_password(cls, username: str, password: str) -> bool:
        configurada = cls._password_configurada(username)
        if not configurada or not password:
            return False
        if configurada.startswith(PREFIJO_HASH):
            return cls._verificar_password_hash(configurada, password)
        return hmac.compare_digest(password.encode("utf-8"), configurada.encode("utf-8"))

    @classmethod
    def advertencias_configuracion(cls) -> list[str]:
        avisos = []
        if not settings.secret_key:
            avisos.append("SECRET_KEY no configurada: se usa una clave temporal y las sesiones se pierden al reiniciar.")
        sin_pass = [u for u in USUARIOS_METADATA if not cls._password_configurada(u)]
        if sin_pass:
            avisos.append(f"Usuarios sin contraseña configurada (no podrán ingresar): {', '.join(sin_pass)}.")
        return avisos

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
            }
            for u in USUARIOS_METADATA.values()
        ]

    @classmethod
    def verificar_bloqueo(cls, ip: str, username: str) -> Tuple[bool, int]:
        """Comprueba si la IP o el usuario están bloqueados por intentos fallidos. Retorna (bloqueado, minutos_restantes)."""
        now = time.time()
        for key in [f"ip:{ip}", f"user:{username.lower()}"]:
            registro = _INTENTOS_FALLIDOS.get(key)
            if registro and registro.get("bloqueado_hasta", 0) > now:
                restante = int((registro["bloqueado_hasta"] - now) / 60) + 1
                return True, restante
        return False, 0

    @classmethod
    def registrar_intento_fallido(cls, ip: str, username: str) -> int:
        """Registra un fallo. Si excede el máximo, activa el bloqueo temporal."""
        now = time.time()
        intentos_max = 0
        for key in [f"ip:{ip}", f"user:{username.lower()}"]:
            if key not in _INTENTOS_FALLIDOS:
                _INTENTOS_FALLIDOS[key] = {"intentos": 0, "bloqueado_hasta": 0, "ultimo_intento": now}
            
            registro = _INTENTOS_FALLIDOS[key]
            # Si el último intento fue hace más de 10 minutos, resetear contador
            if now - registro.get("ultimo_intento", 0) > 600:
                registro["intentos"] = 0

            registro["intentos"] += 1
            registro["ultimo_intento"] = now
            intentos_max = max(intentos_max, registro["intentos"])

            if registro["intentos"] >= MAX_INTENTOS:
                registro["bloqueado_hasta"] = now + TIEMPO_BLOQUEO_SEGUNDOS
                print(f"[SEGURIDAD ALERTA] Bloqueo temporal activado para '{key}' por 15 minutos.", flush=True)

        return MAX_INTENTOS - intentos_max

    @classmethod
    def resetear_intentos(cls, ip: str, username: str):
        """Limpia los intentos fallidos tras login exitoso."""
        for key in [f"ip:{ip}", f"user:{username.lower()}"]:
            _INTENTOS_FALLIDOS.pop(key, None)

    @classmethod
    def autenticar(cls, username: str, password: str, ip: str = "127.0.0.1") -> Tuple[Optional[dict], Optional[str]]:
        """
        Valida credenciales con máxima seguridad:
        - Sanitización de entrada contra inyecciones
        - Verificación de bloqueo anti-fuerza bruta
        - Comparación resistente a timing attacks
        - Hashing de contraseñas
        Retorna (usuario_dict, mensaje_error).
        """
        u_clean = (username or "").strip().lower()
        p_clean = (password or "").strip()

        # Validación de formato (solo caracteres alfanuméricos seguros)
        if not re.match(r"^[a-z0-9_\-\.]{3,30}$", u_clean):
            return None, "Formato de usuario no válido."

        # Verificar si está bloqueado por fuerza bruta
        bloqueado, min_restantes = cls.verificar_bloqueo(ip, u_clean)
        if bloqueado:
            return None, f"⚠️ Acceso bloqueado temporalmente por seguridad. Intente nuevamente en {min_restantes} minuto(s)."

        user_meta = USUARIOS_METADATA.get(u_clean)
        if not user_meta:
            cls.registrar_intento_fallido(ip, u_clean)
            return None, "Usuario o contraseña incorrectos."

        if not cls._verificar_password(u_clean, p_clean):
            restantes = cls.registrar_intento_fallido(ip, u_clean)
            if restantes <= 0:
                return None, "⚠️ Ha superado el límite de intentos. Su acceso ha sido bloqueado por 15 minutos."
            return None, f"Contraseña incorrecta. Le quedan {restantes} intento(s) antes del bloqueo de seguridad."

        # Login exitoso
        cls.resetear_intentos(ip, u_clean)
        print(f"[SEGURIDAD AUDITORIA] Login exitoso de '{u_clean}' ({user_meta['rol']}) desde IP {ip}", flush=True)

        return {
            "username": user_meta["username"],
            "nombre": user_meta["nombre"],
            "rol": user_meta["rol"],
            "cargo": user_meta["cargo"],
            "avatar": user_meta["avatar"],
        }, None

    @classmethod
    def crear_token(cls, username: str) -> str:
        """Crea un token criptográfico anti-tampering con expiración estricta de 12 horas."""
        user = USUARIOS_METADATA.get((username or "").strip().lower())
        if not user:
            return ""
        now = int(time.time())
        exp = now + DURACION_TOKEN_SEGUNDOS
        nonce = os.urandom(12).hex()

        payload = {
            "username": user["username"],
            "nombre": user["nombre"],
            "rol": user["rol"],
            "iat": now,
            "exp": exp,
            "nonce": nonce,
        }
        raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
        signature = hmac.new(_secret_key(), raw.encode(), hashlib.sha256).hexdigest()
        return f"{raw}.{signature}"

    @classmethod
    def validar_token(cls, token: str) -> Optional[dict]:
        """Verifica la integridad de la firma HMAC y la vigencia temporal del token."""
        if not token or "." not in token:
            return None
        try:
            raw, sig = token.split(".", 1)
            expected_sig = hmac.new(_secret_key(), raw.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return None

            data = json.loads(base64.urlsafe_b64decode(raw.encode()).decode())
            now = int(time.time())

            # Comprobar expiración (12 horas)
            if now > data.get("exp", 0):
                return None

            user = USUARIOS_METADATA.get(data.get("username", "").lower())
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


if __name__ == "__main__":
    import getpass

    print(AuthService.hash_password(getpass.getpass("Contraseña a hashear: ")))
