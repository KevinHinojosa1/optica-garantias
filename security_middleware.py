from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 1. Protección contra Clickjacking (no permite embeber la web en iframes maliciosos)
        response.headers["X-Frame-Options"] = "DENY"
        
        # 2. Protección contra MIME-type sniffing (evita que archivos falsificados se ejecuten)
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # 3. Filtro XSS en navegadores
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # 4. Strict Transport Security (HSTS) - Obliga a que toda la navegación sea exclusivamente HTTPS cifrado
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # 5. Política de Referrer estricta (no filtra URLs internas a terceros)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 6. Restricción de permisos del hardware del cliente
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        
        # 7. Aislamiento de origen (evita ataques Cross-Origin)
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        
        # 8. Ocultar información del servidor para evitar fingerprinting de atacantes
        response.headers["Server"] = "Protected-Server"

        return response
