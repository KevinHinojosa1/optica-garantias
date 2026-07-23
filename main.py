import asyncio
import subprocess
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database import SessionLocal, init_db
from routers import (
    alertas_router,
    analisis_router,
    clientes_router,
    cuaderno_router,
    historial_router,
    import_router,
    ivr_router,
    mensajes_router,
    respuesta_ia_router,
    scripts_router,
    tiendas_router,
    conocimiento_router,
    whatsapp_envios_router,
)


def _preparar_directorios() -> None:
    for sub in ("data", "data/consultas", "data/base_datos", "data/google", "data/conocimiento", "static/img"):
        (settings.base_dir / sub).mkdir(parents=True, exist_ok=True)


def _bootstrap_datos():
    """Carga inicial de BD y Excel — en segundo plano para no bloquear health check."""
    try:
        from models.cliente import Cliente
        from services.conocimiento_service import ConocimientoService
        from services.import_service import ImportService

        ruta = ImportService.ruta_archivo_base()
        if not ruta.exists():
            script = settings.base_dir / "scripts" / "generar_base_datos.py"
            if script.exists():
                subprocess.run([sys.executable, str(script)], check=False, timeout=120)

        db = SessionLocal()
        try:
            ConocimientoService.sembrar_inicial(db)
            if db.query(Cliente).count() == 0 and ruta.exists():
                ImportService.importar_desde_carpeta(db, reemplazar=True)
        finally:
            db.close()
    except Exception as exc:
        print(f"Bootstrap (no crítico): {exc}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _preparar_directorios()
    try:
        init_db()
    except Exception as exc:
        print(f"init_db (no crítico): {exc}", flush=True)
    asyncio.create_task(asyncio.to_thread(_bootstrap_datos))
    yield


app = FastAPI(
    title=settings.app_name,
    description="Sistema de gestión de garantías para Óptica Los Andes Ecuador",
    version="1.2.2",
    lifespan=lifespan,
)

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest


class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/static/") or path in ("/ivr", "/alertas", "/conocimiento", "/envios-whatsapp", "/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        # JS/CSS en UTF-8: evita emojis rotos si el navegador asume latin-1
        if path.endswith((".js", ".css", ".html", ".json", ".svg")):
            ct = response.headers.get("content-type", "")
            if ct and "charset" not in ct.lower():
                response.headers["content-type"] = f"{ct}; charset=utf-8"
        return response


app.add_middleware(NoCacheMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(alertas_router)
app.include_router(import_router)
app.include_router(clientes_router)
app.include_router(analisis_router)
app.include_router(mensajes_router)
app.include_router(historial_router)
app.include_router(ivr_router)
app.include_router(scripts_router)
app.include_router(respuesta_ia_router)
app.include_router(tiendas_router)
app.include_router(conocimiento_router)
app.include_router(whatsapp_envios_router)
app.include_router(cuaderno_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/importar")


@app.get("/health")
async def health():
    from templates_shared import ASSET_VERSION

    return {"status": "ok", "app": settings.app_name, "version": ASSET_VERSION}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"detail": "Recurso no encontrado"})
    return RedirectResponse(url="/clientes")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.app_host, port=settings.app_port, reload=settings.debug)