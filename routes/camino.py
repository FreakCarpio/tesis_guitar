"""
Camino y Ejercicios (P1) - Endpoints de lectura.

GET /camino/{user_id}   -> ruta de aprendizaje con estado derivado
GET /ejercicios         -> catálogo de prácticas inteligentes (?habilidad=)
GET /ejercicios/{id}    -> un ejercicio concreto
"""

from fastapi import APIRouter, HTTPException

from domain import camino as camino_dominio
from domain import ejercicios as ejercicios_dominio

router = APIRouter(tags=["camino"])


@router.get("/camino/{user_id}")
async def get_camino(user_id: str):
    """Camino de aprendizaje del usuario (10 pasos con estado derivado)."""
    doc = camino_dominio.obtener_camino(user_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return doc


@router.get("/ejercicios")
async def get_ejercicios(habilidad: str | None = None):
    """Catálogo de ejercicios (metadata pedagógica). Filtra por habilidad."""
    if habilidad:
        items = ejercicios_dominio.ejercicios_por_habilidad(habilidad)
    else:
        items = ejercicios_dominio.EJERCICIOS
    return {"ejercicios": items, "total": len(items)}


@router.get("/ejercicios/{ejercicio_id}")
async def get_ejercicio(ejercicio_id: str):
    """Metadata de un ejercicio (objetivo, dificultad, criterios de aprobación)."""
    ej = ejercicios_dominio.obtener_ejercicio(ejercicio_id)
    # obtener_ejercicio cae en práctica libre para ids desconocidos: si el id
    # pedido no existe realmente, devolvemos 404 para no confundir al cliente.
    if ej["id"] != ejercicio_id and ejercicio_id not in {e["id"] for e in ejercicios_dominio.EJERCICIOS}:
        raise HTTPException(status_code=404, detail="Ejercicio desconocido.")
    return ej
