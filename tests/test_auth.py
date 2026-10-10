"""Pruebas de autenticación, sesión y cabeceras de seguridad."""

import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import importlib
import services.auth_service as auth_mod
from auth_middleware import SessionAuthMiddleware
from config import settings
from security_middleware import OriginCheckMiddleware, SecurityHeadersMiddleware
from services.auth_service import AuthService

auth_router_mod = importlib.import_module("routers.auth_router")

CLAVE = "Clave-Segura-2026!"


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "clave-de-pruebas")
    for u in ("miguel", "andrea", "carla", "kevin"):
        monkeypatch.setattr(settings, f"pass_{u}", "")
    monkeypatch.setattr(settings, "pass_kevin", CLAVE)
    monkeypatch.setattr(auth_router_mod, "RETARDO_LOGIN_FALLIDO_SEGUNDOS", 0)
    auth_mod._INTENTOS_FALLIDOS.clear()
    yield
    auth_mod._INTENTOS_FALLIDOS.clear()


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(auth_router_mod.router)

    @app.post("/api/eco")
    async def eco():
        return {"ok": True}

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SessionAuthMiddleware)
    app.add_middleware(OriginCheckMiddleware)
    return TestClient(app, follow_redirects=False)


def _login(client, username="kevin", password=CLAVE, next_url="/dashboard"):
    client.cookies.clear()
    return client.post("/login", data={"username": username, "password": password, "next_url": next_url})


def test_login_no_expone_contrasenas(client):
    assert all("password_sugerida" not in u for u in AuthService.listar_usuarios())
    r = client.get("/login")
    assert r.status_code == 200
    assert "data-password" not in r.text
    assert CLAVE not in r.text


@pytest.mark.parametrize("password", ["kevin2026", "kevin123", "optica123", "sac2026"])
def test_contrasenas_por_defecto_rechazadas(password):
    user, error = AuthService.autenticar("kevin", password)
    assert user is None and error


def test_contrasena_configurada_funciona():
    user, error = AuthService.autenticar("kevin", CLAVE)
    assert error is None and user["username"] == "kevin"


def test_usuario_sin_contrasena_configurada_no_ingresa():
    for password in ("", "carla2026", "optica123"):
        assert AuthService.autenticar("carla", password)[0] is None
    assert any("carla" in a for a in AuthService.advertencias_configuracion())


def test_contrasena_hasheada(monkeypatch):
    monkeypatch.setattr(settings, "pass_andrea", AuthService.hash_password("otra-clave-99"))
    assert AuthService.autenticar("andrea", "otra-clave-99")[0] is not None
    assert AuthService.autenticar("andrea", "incorrecta")[0] is None


def test_token_firmado_con_clave_antigua_es_rechazado(monkeypatch):
    raw = base64.urlsafe_b64encode(
        json.dumps({"username": "kevin", "exp": int(time.time()) + 3600}).encode()
    ).decode()
    sig = hmac.new(b"ola-sac-enterprise-secure-key-2026-x99", raw.encode(), hashlib.sha256).hexdigest()
    assert AuthService.validar_token(f"{raw}.{sig}") is None
    assert AuthService.validar_token(AuthService.crear_token("kevin"))["username"] == "kevin"


def test_sin_secret_key_usa_clave_aleatoria(monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "")
    token = AuthService.crear_token("kevin")
    assert AuthService.validar_token(token)["username"] == "kevin"
    assert any("SECRET_KEY" in a for a in AuthService.advertencias_configuracion())


def test_login_fallido_no_bloquea_el_proceso(monkeypatch):
    def prohibido(*_):
        raise AssertionError("time.sleep bloquea el event loop")

    monkeypatch.setattr(time, "sleep", prohibido)
    assert AuthService.autenticar("kevin", "mala")[0] is None
    assert AuthService.autenticar("noexiste", "mala")[0] is None


def test_redireccion_abierta_bloqueada(client):
    for malicioso in ("//evil.com", "/\\evil.com", "https://evil.com"):
        r = _login(client, next_url=malicioso)
        assert r.status_code == 303 and r.headers["location"] == "/dashboard"
    assert _login(client, next_url="/clientes").headers["location"] == "/clientes"


def test_csrf_origen_externo_rechazado(client):
    assert _login(client).status_code == 303
    assert client.post("/api/eco", headers={"Origin": "https://evil.com"}).status_code == 403
    assert client.post("/api/eco", headers={"Referer": "https://evil.com/x"}).status_code == 403
    assert client.post("/api/eco", headers={"Origin": "http://testserver"}).status_code == 200
    assert client.post("/api/eco").status_code == 200


def test_cabeceras_de_seguridad(client):
    r = client.get("/login")
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"


def test_bloqueo_por_intentos(client):
    for _ in range(5):
        AuthService.autenticar("kevin", "mala", ip="1.1.1.1")
    user, error = AuthService.autenticar("kevin", CLAVE, ip="2.2.2.2")
    assert user is None and "bloqueado" in error.lower()
