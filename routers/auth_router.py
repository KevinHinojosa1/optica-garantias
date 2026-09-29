from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from templates_shared import templates
from services.auth_service import AuthService

router = APIRouter(tags=["Autenticación"])

def _obtener_ip_cliente(request: Request) -> str:
    """Extrae la IP real del cliente detrás de proxies reversos (como Render / Cloudflare)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/dashboard", error: str = None):
    ip = _obtener_ip_cliente(request)
    bloqueado, min_restantes = AuthService.verificar_bloqueo(ip, "")
    
    msg_error = error
    if bloqueado and not msg_error:
        msg_error = f"⚠️ Su dirección IP está temporalmente bloqueada por seguridad. Intente de nuevo en {min_restantes} minuto(s)."

    usuarios = AuthService.listar_usuarios()
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "usuarios": usuarios,
            "next_url": next or "/dashboard",
            "error": msg_error,
            "bloqueado": bloqueado,
        },
    )

@router.post("/login")
async def procesar_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next_url: str = Form(default="/dashboard"),
):
    ip = _obtener_ip_cliente(request)
    user, error_msg = AuthService.autenticar(username, password, ip=ip)
    
    if error_msg or not user:
        usuarios = AuthService.listar_usuarios()
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "usuarios": usuarios,
                "next_url": next_url or "/dashboard",
                "error": error_msg or "Usuario o contraseña incorrectos.",
                "selected_username": username.strip().lower() if username else "",
            },
            status_code=400,
        )

    # Autenticación exitosa: generar token criptográfico firmado
    token = AuthService.crear_token(user["username"])
    destino = next_url if next_url and next_url.startswith("/") and next_url != "/login" else "/dashboard"
    
    is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"

    response = RedirectResponse(url=destino, status_code=303)
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=12 * 3600,  # 12 horas (sesión laboral segura)
        httponly=True,       # Protege contra robo por XSS
        secure=is_https,     # Solo viaja cifrado en HTTPS
        samesite="lax",      # Protege contra ataques CSRF
        path="/",
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="session_token", path="/")
    return response
