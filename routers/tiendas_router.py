from fastapi import APIRouter, HTTPException

from services.tiendas_service import TiendasService

router = APIRouter(tags=["Tiendas"])


@router.get("/api/tiendas")
async def listar_tiendas():
    try:
        return TiendasService.listar()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al cargar tiendas: {exc}") from exc