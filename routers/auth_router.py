from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from templates_shared import templates
from services.auth_service import AuthService

router = APIRouter(tags=["Autenticación"])

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/dashboard", error: str = None):
    usuarios = AuthService.listar_usuarios()
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "usuarios": usuarios,
            "next_url": next or "/dashboard",
            "error": error,
        },
    )

@router.post("/login")
async def procesar_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next_url: str = Form(default="/dashboard"),
):
    user = AuthService.autenticar(username, password)
    if not user:
        usuarios = AuthService.listar_usuarios()
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "usuarios": usuarios,
                "next_url": next_url or "/dashboard",
                "error": "Usuario o contraseña incorrectos. Verifique sus credenciales.",
                "selected_username": username.strip().lower(),
            },
            status_code=400,
        )

    # Autenticación exitosa
    token = AuthService.crear_token(user["username"])
    destino = next_url if next_url and next_url.startswith("/") and next_url != "/login" else "/dashboard"
    
    response = RedirectResponse(url=destino, status_code=303)
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=60 * 60 * 24 * 30,  # 30 días
        httponly=True,
        samesite="lax",
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response
