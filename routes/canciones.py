"""
Canciones (Song Detail) - Endpoints del proxy de canciones.

Android NO habla con Songsterr/iTunes: todo pasa por aquí (caché en Mongo,
DTOs propios de FretMind, proveedor intercambiable).

GET /canciones/buscar?q=&size=&desde=   -> búsqueda paginada
GET /canciones/{song_id}                -> detalle compuesto (Songsterr+iTunes)
"""

from datetime import datetime, timezone

import requests
from fastapi import APIRouter, HTTPException

from database import biblioteca_usuario, usuarios
from domain import ejercicios as ejercicios_dominio
from services import canciones_service
from services.wilfredo_service import generate_song_plan

router = APIRouter(prefix="/canciones", tags=["canciones"])


def _ejercicio_para_cancion(dificultad: str | None, nivel: str) -> dict:
    """Ejercicio del catálogo con el que se practica una canción.

    Canciones fáciles o usuarios principiantes -> "primera_cancion"
    (cambios de acordes); avanzadas con usuario no principiante ->
    "lectura" (canciones completas).
    """
    if dificultad == "Avanzado" and nivel != "principiante":
        return ejercicios_dominio.obtener_ejercicio("lectura")
    return ejercicios_dominio.obtener_ejercicio("primera_cancion")


def _plan_cancion(song_id: int, user_id: str) -> dict:
    usuario = usuarios.find_one({"user_id": user_id})
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    det = canciones_service.obtener_detalle(song_id)
    if det is None:
        raise HTTPException(status_code=404, detail="Canción no encontrada.")

    nivel = usuario.get("nivel", "principiante")
    plan = generate_song_plan(
        titulo=det["titulo"],
        artista=det["artista"],
        dificultad=det.get("dificultad"),
        tiene_acordes=det.get("tiene_acordes", True),
        nivel=nivel,
    )
    ejercicio = _ejercicio_para_cancion(det.get("dificultad"), nivel)
    return {
        "cancion": {
            "song_id": song_id,
            "titulo": det["titulo"],
            "artista": det["artista"],
            "portada": det.get("portada"),
        },
        "ejercicio": ejercicio,
        "objetivos": plan["objetivos"],
        "consejo": plan["consejo"],
        "duracion_sugerida_min": plan["duracion_sugerida_min"],
    }


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


@router.get("/{song_id}/plan")
async def plan(song_id: int, user_id: str):
    """Objetivos de Wilfredo para practicar esta canción (sin efectos)."""
    return _plan_cancion(song_id, user_id)


@router.post("/{song_id}/practicar")
async def practicar(song_id: int, user_id: str):
    """Botón "Practicar": registra la canción en la biblioteca del usuario y
    devuelve el plan de Wilfredo + el ejercicio con el que abrir la práctica.

    La sesión de práctica real se crea al terminar (POST /practica con
    cancion_id), asociando la sesión a esta canción.
    """
    resultado = _plan_cancion(song_id, user_id)
    ahora = datetime.now(timezone.utc).isoformat()
    c = resultado["cancion"]
    biblioteca_usuario.update_one(
        {"usuario": user_id, "song_id": song_id},
        {
            "$set": {
                "titulo": c["titulo"],
                "artista": c["artista"],
                "portada": c["portada"],
                "guardada": True,
                "ultima_practica": ahora,
            },
            "$inc": {"practicas": 1},
            "$setOnInsert": {"favorita": False, "fecha_agregada": ahora},
        },
        upsert=True,
    )
    return resultado
