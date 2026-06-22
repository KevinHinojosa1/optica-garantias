from sqlalchemy import func
from sqlalchemy.orm import Session

from models.cliente import Cliente


class DuplicateService:
    @staticmethod
    def cedulas_duplicadas(db: Session) -> set[str]:
        rows = (
            db.query(Cliente.cedula)
            .group_by(Cliente.cedula)
            .having(func.count(Cliente.id) > 1)
            .all()
        )
        return {r[0].strip() for r in rows}

    @staticmethod
    def facturas_duplicadas(db: Session) -> set[str]:
        rows = (
            db.query(Cliente.numero_factura)
            .group_by(Cliente.numero_factura)
            .having(func.count(Cliente.id) > 1)
            .all()
        )
        return {r[0].strip().upper() for r in rows}

    @classmethod
    def es_duplicado(cls, db: Session, cliente: Cliente) -> bool:
        cedulas = cls.cedulas_duplicadas(db)
        facturas = cls.facturas_duplicadas(db)
        return (
            cliente.cedula.strip() in cedulas
            or cliente.numero_factura.strip().upper() in facturas
        )

    @classmethod
    def mapa_duplicados(cls, db: Session, clientes: list[Cliente]) -> dict[int, bool]:
        cedulas = cls.cedulas_duplicadas(db)
        facturas = cls.facturas_duplicadas(db)
        return {
            c.id: (
                c.cedula.strip() in cedulas
                or c.numero_factura.strip().upper() in facturas
            )
            for c in clientes
        }

    @staticmethod
    def existe_factura(db: Session, numero_factura: str) -> bool:
        clave = numero_factura.strip().upper()
        existe = (
            db.query(Cliente.id)
            .filter(func.upper(Cliente.numero_factura) == clave)
            .first()
        )
        return existe is not None

    @staticmethod
    def existe_cedula_factura(db: Session, cedula: str, numero_factura: str) -> bool:
        existe = (
            db.query(Cliente.id)
            .filter(
                Cliente.cedula == cedula.strip(),
                func.upper(Cliente.numero_factura) == numero_factura.strip().upper(),
            )
            .first()
        )
        return existe is not None