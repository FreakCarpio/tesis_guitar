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

# ---------------------------------------------------------------------------
# Práctica guiada de canción (letra + acordes + reconocimiento en el cliente)
# ---------------------------------------------------------------------------

# Los acordes de la práctica guiada son los REALES de la hoja de acordes de
# la comunidad Songsterr (services.canciones_service.obtener_acordes), con
# su letra alineada acorde a acorde y en el orden original. Si una canción
# no tiene hoja de acordes publicada, la práctica se declara no disponible
# (disponible=False) con un mensaje honesto: nunca se inventan acordes.

# Duración estimada por línea cuando la canción no informa su duración.
_SEG_POR_LINEA = 8.0


def _asignar_tiempos(secciones: list[dict], duracion_seg: int | None) -> None:
    """Reparte la duración de la canción entre las líneas de la hoja de
    acordes (que no trae timestamps): tiempos crecientes y acotados para
    que el desplazamiento automático del cliente avance a ritmo razonable."""
    lineas = [linea for s in secciones for linea in s["lineas"]]
    if not lineas:
        return
    paso = (duracion_seg / (len(lineas) + 1)) if duracion_seg else _SEG_POR_LINEA
    paso = max(2.5, min(12.0, paso))
    for i, linea in enumerate(lineas):
        linea["t_seg"] = round(i * paso + 2.0, 2)


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


@router.get("/{song_id}/practica_guiada")
async def practica_guiada(song_id: int, user_id: str):
    """Contenido de la práctica guiada de una canción (estilo Yousician /
    Ultimate Guitar): los acordes REALES de la hoja de Songsterr con su
    letra alineada, en el orden original de la canción, con timestamps
    estimados para el desplazamiento automático y el consejo de RIFF.

    Si la canción no tiene hoja de acordes publicada, responde con
    disponible=False y un mensaje honesto (nunca acordes inventados).
    """
    usuario = usuarios.find_one({"user_id": user_id})
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    try:
        det = canciones_service.obtener_detalle(song_id)
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="El proveedor de canciones no respondió.")
    if det is None:
        raise HTTPException(status_code=404, detail="Canción no encontrada.")

    cancion = {
        "song_id": song_id,
        "titulo": det["titulo"],
        "artista": det["artista"],
        "portada": det.get("portada"),
        "duracion_seg": det.get("duracion_seg"),
    }
    nivel = usuario.get("nivel", "principiante")
    ejercicio = _ejercicio_para_cancion(det.get("dificultad"), nivel)

    try:
        acordes = canciones_service.obtener_acordes(song_id)
    except requests.RequestException:
        # Proveedor caído: mejor declarar la práctica no disponible que
        # inventar una progresión que no es de la canción.
        acordes = None

    if acordes is None:
        return {
            "cancion": cancion,
            "disponible": False,
            "tiene_letra": False,
            "sincronizada": False,
            "bpm": 60,
            "progresion": [],
            "secciones": [],
            "consejo": "",
            "ejercicio_id": ejercicio["id"],
            "nota": (
                "Esta canción aún no tiene sus acordes disponibles en "
                "nuestra fuente, así que la práctica guiada no está lista. "
                "Puedes explorar otra canción o practicar desde Práctica."
            ),
        }

    secciones = acordes["secciones"]
    _asignar_tiempos(secciones, det.get("duracion_seg"))
    tiene_letra = any(
        linea["texto"] for s in secciones for linea in s["lineas"]
    )

    plan = generate_song_plan(
        titulo=det["titulo"],
        artista=det["artista"],
        dificultad=det.get("dificultad"),
        tiene_acordes=det.get("tiene_acordes", True),
        nivel=nivel,
    )
    nota = "Acordes reales de la hoja comunitaria de Songsterr."
    if acordes.get("capo"):
        nota += f" Sugiere capo en el traste {acordes['capo']} (opcional)."
    if acordes.get("afinacion"):
        nota += f" Afinación: {acordes['afinacion']}."
    return {
        "cancion": cancion,
        "disponible": True,
        "tiene_letra": tiene_letra,
        # Los tiempos son estimados (la hoja de acordes no trae timestamps).
        "sincronizada": False,
        "bpm": 60,
        "progresion": acordes["progresion"],
        "secciones": secciones,
        "consejo": plan["consejo"],
        "ejercicio_id": ejercicio["id"],
        "nota": nota,
    }


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
