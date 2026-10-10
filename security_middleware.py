from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

METODOS_INSEGUROS = {"POST", "PUT", "PATCH", "DELETE"}

# Política conservadora: no restringe scripts/estilos (hay CDNs y scripts inline),
# pero bloquea iframes externos, <base> inyectado, plugins y envío de formularios a otros dominios.
CONTENT_SECURITY_POLICY = "frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'"


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """Protección CSRF: rechaza peticiones que modifican datos si vienen de otro sitio (Origin/Referer)."""

    async def dispatch(self, request: Request, call_next):
        if request.method in METODOS_INSEGUROS:
            origen = request.headers.get("origin") or request.headers.get("referer")
            if origen:
                host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
                if urlsplit(origen).netloc.lower() != host.split(",")[0].strip().lower():
                    return JSONResponse(status_code=403, content={"detail": "Origen no permitido."})
        return await call_next(request)

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
        response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
        
        # 8. Ocultar información del servidor para evitar fingerprinting de atacantes
        response.headers["Server"] = "Protected-Server"

        return response
