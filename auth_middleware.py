from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse
from services.auth_service import AuthService

RUTAS_PUBLICAS = {
    "/login",
    "/api/login",
    "/logout",
    "/health",
    "/favicon.ico",
}

class SessionAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Permitir recursos estáticos siempre
        if path.startswith("/static/"):
            return await call_next(request)

        # Leer cookie de sesión
        token = request.cookies.get("session_token")
        user = AuthService.validar_token(token) if token else None
        
        # Guardar usuario en request.state para que plantillas y rutas puedan accederlo
        request.state.user = user

        # Si ya está autenticado y entra a /login, redirigir al Dashboard
        if path == "/login" and user:
            return RedirectResponse(url="/dashboard", status_code=302)

        # Permitir rutas públicas
        if path in RUTAS_PUBLICAS:
            return await call_next(request)

        # Si no está autenticado:
        if not user:
            if path.startswith("/api/"):
                return JSONResponse(status_code=401, content={"detail": "Sesión no válida o expirada. Inicie sesión."})
            # Guardar a dónde quería ir
            next_url = path if path not in ("/", "/logout") else "/dashboard"
            return RedirectResponse(url=f"/login?next={next_url}", status_code=302)

        return await call_next(request)
