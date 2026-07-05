import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database import SessionLocal, init_db
from routers import (
    analisis_router,
    clientes_router,
    historial_router,
    import_router,
    ivr_router,
    mensajes_router,
    respuesta_ia_router,
    scripts_router,
    tiendas_router,
)


def _bootstrap_datos():
    """Carga inicial de BD y Excel de prueba (no bloquea si falla)."""
    try:
        init_db()
        for sub in ("data/consultas", "data/base_datos", "data/google"):
            (settings.base_dir / sub).mkdir(parents=True, exist_ok=True)

        from models.cliente import Cliente
        from services.import_service import ImportService

        ruta = ImportService.ruta_archivo_base()
        if not ruta.exists():
            script = settings.base_dir / "scripts" / "generar_base_datos.py"
            if script.exists():
                subprocess.run(["python", str(script)], check=False)

        db = SessionLocal()
        try:
            if db.query(Cliente).count() == 0 and ruta.exists():
                ImportService.importar_desde_carpeta(db, reemplazar=True)
        finally:
            db.close()
    except Exception as exc:
        print(f"Bootstrap (no crítico): {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _bootstrap_datos()
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
        if request.url.path.startswith("/static/") or request.url.path in ("/ivr", "/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response


app.add_middleware(NoCacheMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(import_router)
app.include_router(clientes_router)
app.include_router(analisis_router)
app.include_router(mensajes_router)
app.include_router(historial_router)
app.include_router(ivr_router)
app.include_router(scripts_router)
app.include_router(respuesta_ia_router)
app.include_router(tiendas_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/importar")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"detail": "Recurso no encontrado"})
    return RedirectResponse(url="/clientes")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.app_host, port=settings.app_port, reload=settings.debug)