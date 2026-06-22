"""Reparación de datos legacy: tiendas sin asignar y registros duplicados."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.cliente import Cliente
from services.tiendas_service import TiendasService

# Mapeo conocido factura → tienda (importaciones previas a columna tienda)
FACTURA_TIENDA_MAP: dict[str, str] = {
    "FAC-2025-001234": "Quicentro Shopping",
    "FAC-2024-009876": "Mall del Sol",
    "FAC-2025-005432": "Condado Shopping",
    "FAC-2025-006789": "San Marino Shopping",
}


class DataRepairService:
    @classmethod
    def reparar_tiendas_sin_asignar(cls, db: Session) -> int:
        actualizados = 0
        sin_asignar = db.query(Cliente).filter(Cliente.tienda == "Sin asignar").all()
        for cliente in sin_asignar:
            clave = cliente.numero_factura.strip().upper()
            tienda = FACTURA_TIENDA_MAP.get(clave)
            if tienda and TiendasService.validar_tienda(tienda):
                cliente.tienda = tienda
                actualizados += 1
        return actualizados

    @classmethod
    def eliminar_duplicados_por_factura(cls, db: Session) -> int:
        eliminados = 0
        dup_facturas = (
            db.query(Cliente.numero_factura)
            .group_by(Cliente.numero_factura)
            .having(func.count(Cliente.id) > 1)
            .all()
        )
        for (factura,) in dup_facturas:
            registros = (
                db.query(Cliente)
                .filter(Cliente.numero_factura == factura)
                .order_by(Cliente.id)
                .all()
            )
            for duplicado in registros[1:]:
                db.delete(duplicado)
                eliminados += 1
        return eliminados

    @classmethod
    def ejecutar_reparacion(cls, db: Session) -> dict:
        tiendas = cls.reparar_tiendas_sin_asignar(db)
        duplicados = cls.eliminar_duplicados_por_factura(db)
        if tiendas or duplicados:
            db.commit()
        return {"tiendas_actualizadas": tiendas, "duplicados_eliminados": duplicados}