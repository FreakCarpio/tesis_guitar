"""
Canciones (Song Detail) - Endpoints del proxy de canciones.

Android NO habla con Songsterr/iTunes: todo pasa por aquí (caché en Mongo,
DTOs propios de FretMind, proveedor intercambiable).

GET /canciones/buscar?q=&size=&desde=   -> búsqueda paginada
GET /canciones/{song_id}                -> detalle compuesto (Songsterr+iTunes)
"""

import requests
from fastapi import APIRouter, HTTPException

from services import canciones_service

router = APIRouter(prefix="/canciones", tags=["canciones"])


@router.get("/buscar")
async def buscar(q: str, size: int = 10, desde: int = 0):
    """Búsqueda de canciones (paginada). `hay_mas` indica si existe otra página."""
    if not q.strip():
        return {"canciones": [], "cantidad": 0, "desde": 0, "size": size, "hay_mas": False}
    try:
        return canciones_service.buscar_canciones(q, size=size, desde=desde)
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="El proveedor de canciones no respondió.")


@router.get("/{song_id}")
async def detalle(song_id: int):
    """Detalle unificado de una canción (metadata + portada/género/duración)."""
    try:
        data = canciones_service.obtener_detalle(song_id)
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="El proveedor de canciones no respondió.")
    if data is None:
        raise HTTPException(status_code=404, detail="Canción no encontrada.")
    return data
