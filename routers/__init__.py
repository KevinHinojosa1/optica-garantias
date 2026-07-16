from routers.alertas_router import router as alertas_router
from routers.import_router import router as import_router
from routers.clientes_router import router as clientes_router
from routers.analisis_router import router as analisis_router
from routers.mensajes_router import router as mensajes_router
from routers.historial_router import router as historial_router
from routers.ivr_router import router as ivr_router
from routers.scripts_router import router as scripts_router
from routers.respuesta_ia_router import router as respuesta_ia_router
from routers.tiendas_router import router as tiendas_router
from routers.conocimiento_router import router as conocimiento_router

__all__ = [
    "alertas_router",
    "import_router",
    "clientes_router",
    "analisis_router",
    "mensajes_router",
    "historial_router",
    "ivr_router",
    "scripts_router",
    "respuesta_ia_router",
    "tiendas_router",
    "conocimiento_router",
]