import secrets
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, HTMLResponse
import base64
from config import settings

class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow health checks and static files without auth
        if request.url.path.startswith("/health") or request.url.path.startswith("/static"):
            return await call_next(request)

        # Ensure credentials exist in env
        admin_user = getattr(settings, 'admin_username', None)
        admin_pass = getattr(settings, 'admin_password', None)
        
        # If no credentials configured, bypass (for local dev or transitional phase)
        if not admin_user or not admin_pass:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Basic "):
            return self.unauthorized()
            
        try:
            encoded_credentials = auth_header.split(" ")[1]
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            username, _, password = decoded_credentials.partition(":")
            
            is_correct_username = secrets.compare_digest(username, admin_user)
            is_correct_password = secrets.compare_digest(password, admin_pass)
            
            if not (is_correct_username and is_correct_password):
                return self.unauthorized()
                
        except Exception:
            return self.unauthorized()

        return await call_next(request)

    def unauthorized(self):
        headers = {"WWW-Authenticate": "Basic"}
        return Response(content="Acceso Denegado. Por favor inicie sesion.", status_code=401, headers=headers)
