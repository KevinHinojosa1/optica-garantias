"""Genera data/base_datos/pacientes.xlsx con pacientes de prueba distribuidos por tienda."""

from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd

BASE_DIR = Path(__file__).parent.parent
OUTPUT = BASE_DIR / "data" / "base_datos" / "pacientes.xlsx"

TIENDAS = [
    "Quicentro Shopping",
    "Condado Shopping",
    "Megamaxi 6 de Diciembre",
    "Río Amazonas",
    "Mall del Sol",
    "San Marino Shopping",
    "Riocentro Norte",
    "Village Plaza",
]

NOMBRES = [
    "María González Pérez", "Carlos Mendoza Ruiz", "Ana Lucía Vásquez", "Roberto Sánchez",
    "Juan Pérez Castro", "María López Herrera", "Carlos Ramírez Vega", "Ana Martínez Solís",
    "Luis González Mora", "Patricia Herrera Díaz", "Fernando Castro Ruiz", "Sofía Morales León",
    "Diego Torres Arias", "Valentina Romero Paz", "Andrés Vargas Cruz", "Camila Salazar Núñez",
    "Ricardo Delgado Peña", "Gabriela Ortega Ríos", "Héctor Mendoza Gil", "Natalia Paredes Luna",
    "Oscar Benítez Soto", "Daniela Cordero Mena", "Miguel Álvarez Costa", "Laura Espinoza Vera",
    "Jorge Rivas Campos", "Isabel Fuentes Aguirre", "Pablo Navarro Reyes", "Elena Suárez Ponce",
    "Santiago Mejía Duarte", "Adriana Cabrera Ibarra", "Felipe Guerrero Santos", "Mónica Velasco Rojas",
]

PRODUCTOS = [
    ("Lente Progresivo Blue AR", "lente oftálmico"),
    ("Armazón Titanio Flex", "armazón"),
    ("Gafa Ray-Ban Aviator", "gafa"),
    ("Lente de Contacto Mensual", "lente de contacto"),
    ("Lente Monofocal Antireflejo", "lente oftálmico"),
    ("Armazón Acetato Premium", "armazón"),
    ("Gafa Oakley Sport", "gafa"),
    ("Lente Bifocal Transitions", "lente oftálmico"),
]

random.seed(42)


def generar_cedula(i: int) -> str:
    return f"{random.randint(10, 24)}{random.randint(1000000, 9999999)}"


def generar_telefono(i: int) -> str:
    return f"09{random.randint(10000000, 99999999)}"


def generar_fila(i: int, tienda: str) -> dict:
    nombre = NOMBRES[i % len(NOMBRES)]
    producto, tipo = PRODUCTOS[i % len(PRODUCTOS)]
    dias = random.randint(15, 320)
    fecha_factura = date.today() - timedelta(days=dias)
    fecha_entrega = fecha_factura + timedelta(days=random.randint(3, 14))
    prefijo = tienda[:3].upper().replace(" ", "")
    return {
        "nombre": nombre,
        "cedula": generar_cedula(i),
        "telefono": generar_telefono(i),
        "tienda": tienda,
        "producto": producto,
        "tipo_producto": tipo,
        "fecha_factura": fecha_factura.isoformat(),
        "numero_factura": f"FAC-{prefijo}-{2025 + (i % 2)}-{1000 + i:04d}",
        "fecha_entrega": fecha_entrega.isoformat(),
        "tiene_ola_plus": random.choice([True, False, False]),
    }


def main():
    filas = []
    idx = 0
    for tienda in TIENDAS:
        for _ in range(4):
            filas.append(generar_fila(idx, tienda))
            idx += 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(filas)
    df.to_excel(OUTPUT, index=False, sheet_name="Pacientes")
    print(f"Generado: {OUTPUT} ({len(df)} pacientes, {len(TIENDAS)} tiendas)")


if __name__ == "__main__":
    main()