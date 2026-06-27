import json
import math

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from templates_shared import templates
from sqlalchemy.orm import Session

from database import get_db
from models.cliente import Cliente
from schemas.cliente import ClienteCreate, ClienteListResponse, ClienteResponse, DescuentoUpdate
from services.descuento_service import DescuentoService
from services.duplicate_service import DuplicateService
from services.garantia_service import GarantiaService
from services.search_service import SearchService
from services.tiendas_service import TiendasService
from services.whatsapp_service import WhatsAppService

router = APIRouter(tags=["Módulo 2 - Clientes"])



def cliente_to_response(cliente: Cliente, es_duplicado: bool = False) -> ClienteResponse:
    estado = GarantiaService.evaluar_estado_general(cliente.fecha_factura, cliente.tiene_ola_plus)
    return ClienteResponse(
        id=cliente.id,
        nombre=cliente.nombre,
        cedula=cliente.cedula,
        telefono=cliente.telefono,
        tienda=cliente.tienda,
        producto=cliente.producto,
        tipo_producto=cliente.tipo_producto,
        fecha_factura=cliente.fecha_factura,
        numero_factura=cliente.numero_factura,
        fecha_entrega=cliente.fecha_entrega,
        tiene_ola_plus=cliente.tiene_ola_plus,
        codigo_descuento=cliente.codigo_descuento,
        porcentaje_descuento=cliente.porcentaje_descuento,
        created_at=cliente.created_at,
        dias_desde_factura=estado["dias_desde_factura"],
        dentro_garantia=estado["dentro_garantia"],
        estado_garantia=estado["estado_garantia"],
        es_duplicado=es_duplicado,
    )


@router.get("/clientes", response_class=HTMLResponse)
async def pagina_clientes(request: Request):
    tiendas = TiendasService.listar()
    tiendas_operativas = [t for t in tiendas if t["id"] != "central-call-center"]
    ciudades = sorted({t["ciudad"] for t in tiendas_operativas})
    return templates.TemplateResponse(
        request,
        "clientes.html",
        {
            "active": "clientes",
            "tiendas": tiendas,
            "ciudades": ciudades,
            "tiendas_json": json.dumps(tiendas_operativas),
        },
    )


@router.get("/clientes/{cliente_id}", response_class=HTMLResponse)
async def pagina_cliente_detalle(cliente_id: int, request: Request, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    es_dup = DuplicateService.es_duplicado(db, cliente)
    data = cliente_to_response(cliente, es_dup)
    cliente_dict = data.model_dump(mode="json")
    tienda_info = TiendasService.resolver_para_cliente(cliente.tienda)
    mensaje = WhatsAppService.mensaje_pre_cargado(cliente_dict)
    wa_link, _ = WhatsAppService.enlace_grupo_apoyo(cliente_dict, mensaje)
    return templates.TemplateResponse(
        request,
        "cliente_detalle.html",
        {
            "active": "clientes",
            "cliente": data,
            "cliente_json": json.dumps(cliente_dict),
            "wa_link": wa_link,
            "mensaje_inicial": mensaje,
            "tienda_info": tienda_info,
            "tienda_info_json": json.dumps(tienda_info),
            "tiendas": TiendasService.listar(),
            "es_duplicado": es_dup,
        },
    )


@router.get("/api/clientes", response_model=ClienteListResponse)
async def listar_clientes(
    q: str = Query("", description="Búsqueda por nombre, cédula o factura"),
    tienda: str = Query("", description="Filtrar por tienda exacta (obligatorio en atención)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    try:
        tienda_filtro = tienda.strip()
        if not tienda_filtro:
            raise HTTPException(
                status_code=422,
                detail="Debe seleccionar un local para consultar pacientes.",
            )
        if not TiendasService.validar_tienda(tienda_filtro):
            raise HTTPException(
                status_code=422,
                detail=f"Tienda '{tienda_filtro}' no reconocida en el catálogo.",
            )

        query = db.query(Cliente).filter(Cliente.tienda == tienda_filtro)
        busqueda = q.strip()
        if busqueda:
            query = query.filter(SearchService.filtro_busqueda(busqueda))

        total = query.count()
        pages = max(1, math.ceil(total / per_page))
        offset = (page - 1) * per_page
        clientes = query.order_by(Cliente.nombre).offset(offset).limit(per_page).all()
        dup_map = DuplicateService.mapa_duplicados(db, clientes)

        return ClienteListResponse(
            items=[cliente_to_response(c, dup_map.get(c.id, False)) for c in clientes],
            total=total,
            page=page,
            pages=pages,
            per_page=per_page,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al listar clientes: {exc}") from exc


@router.post("/api/clientes", response_model=ClienteResponse)
async def crear_cliente(payload: ClienteCreate, db: Session = Depends(get_db)):
    if not TiendasService.validar_tienda(payload.tienda):
        raise HTTPException(
            status_code=422,
            detail=f"Tienda '{payload.tienda}' no reconocida. Seleccione un local del catálogo.",
        )
    if DuplicateService.existe_factura(db, payload.numero_factura):
        raise HTTPException(
            status_code=409,
            detail=f"⚠️ Cliente duplicado: la factura {payload.numero_factura} ya está registrada.",
        )

    try:
        codigo, pct = DescuentoService.validar(
            payload.codigo_descuento,
            payload.porcentaje_descuento,
        )
        data = payload.model_dump()
        data["codigo_descuento"] = codigo
        data["porcentaje_descuento"] = pct
        cliente = Cliente(**data)
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        return cliente_to_response(cliente, DuplicateService.es_duplicado(db, cliente))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        if "uq_clientes_numero_factura" in str(exc) or "UNIQUE" in str(exc).upper():
            raise HTTPException(
                status_code=409,
                detail=f"⚠️ Cliente duplicado: la factura {payload.numero_factura} ya existe.",
            ) from exc
        raise HTTPException(status_code=500, detail=f"Error al registrar cliente: {exc}") from exc


@router.patch("/api/clientes/{cliente_id}/descuento", response_model=ClienteResponse)
async def actualizar_descuento(
    cliente_id: int,
    payload: DescuentoUpdate,
    db: Session = Depends(get_db),
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    try:
        codigo, porcentaje = DescuentoService.validar(
            payload.codigo_descuento,
            payload.porcentaje_descuento,
        )
        cliente.codigo_descuento = codigo
        cliente.porcentaje_descuento = porcentaje
        db.commit()
        db.refresh(cliente)
        return cliente_to_response(cliente, DuplicateService.es_duplicado(db, cliente))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar descuento: {exc}") from exc


@router.delete("/api/clientes/{cliente_id}")
async def eliminar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    try:
        nombre = cliente.nombre
        db.delete(cliente)
        db.commit()
        return {"ok": True, "mensaje": f"Cliente {nombre} eliminado correctamente."}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar: {exc}") from exc


@router.get("/api/clientes/{cliente_id}", response_model=ClienteResponse)
async def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return cliente_to_response(cliente, DuplicateService.es_duplicado(db, cliente))