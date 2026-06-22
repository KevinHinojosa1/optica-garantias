from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database import init_db
from routers import (
    analisis_router,
    clientes_router,
    historial_router,
    import_router,
    ivr_router,
    mensajes_router,
    scripts_router,
    tiendas_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Sistema de gestión de garantías para Óptica Los Andes Ecuador",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(import_router)
app.include_router(clientes_router)
app.include_router(analisis_router)
app.include_router(mensajes_router)
app.include_router(historial_router)
app.include_router(ivr_router)
app.include_router(scripts_router)
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