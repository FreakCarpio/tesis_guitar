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
from services import canciones_service, letras_service
from services.wilfredo_service import generate_song_plan

router = APIRouter(prefix="/canciones", tags=["canciones"])

# ---------------------------------------------------------------------------
# Práctica guiada de canción (letra + acordes + reconocimiento en el cliente)
# ---------------------------------------------------------------------------

# Sin transcripción real disponible (Songsterr la sirve tras CDN firmado),
# los acordes sobre la letra son la PROGRESIÓN DE PRÁCTICA de RIFF: formas
# del catálogo didáctico elegidas por nivel/dificultad. Es material de
# práctica inspirado en la canción, no su transcripción exacta.
def _progresion_practica(dificultad: str | None, nivel: str) -> list[str]:
    if nivel == "principiante" or dificultad in (None, "Fácil"):
        return ["Am", "C", "G"]
    if dificultad == "Intermedio":
        return ["C", "G", "Am", "Em"]
    return ["C", "G", "Am", "F"]


# Duración estimada por línea cuando no hay timestamps (letra plana).
_SEG_POR_LINEA = 8.0


def _armar_secciones(lineas: list[dict], progresion: list[str],
                     duracion_seg: int | None) -> list[dict]:
    """Agrupa la letra en secciones (estrofas separadas por líneas vacías)
    y asigna un acorde de la progresión a cada línea cantada, rotando.

    Cada línea sale con t_seg: el real (letra sincronizada) o uno estimado
    repartiendo la duración de la canción, para que el cliente pueda
    desplazarse automáticamente en ambos casos.
    """
    con_texto = [l for l in lineas if l["texto"]]
    if not con_texto:
        return []

    # Estimación de tiempos si la letra no viene sincronizada.
    sin_tiempos = all(l.get("t_seg") is None for l in con_texto)
    if sin_tiempos:
        paso = (duracion_seg / (len(con_texto) + 1)) if duracion_seg else _SEG_POR_LINEA
        paso = max(3.0, min(12.0, paso))
        for i, linea in enumerate(con_texto):
            linea["t_seg"] = round(i * paso + 2.0, 2)

    secciones: list[dict] = []
    actual: list[dict] = []
    idx_acorde = 0
    for linea in lineas:
        if not linea["texto"]:
            if actual:
                secciones.append(actual)
                actual = []
            continue
        actual.append({
            "texto": linea["texto"],
            "t_seg": linea.get("t_seg"),
            "acorde": progresion[idx_acorde % len(progresion)],
        })
        idx_acorde += 1
    if actual:
        secciones.append(actual)

    # Letras sincronizadas casi nunca traen líneas vacías: si quedó todo en
    # un bloque largo, se corta en estrofas de 8 líneas para poder respirar.
    if len(secciones) == 1 and len(secciones[0]) > 12:
        bloque = secciones[0]
        secciones = [bloque[i:i + 8] for i in range(0, len(bloque), 8)]

    return [
        {"nombre": f"Parte {i + 1}", "lineas": lineas_seccion}
        for i, lineas_seccion in enumerate(secciones)
    ]


def _secciones_sin_letra(progresion: list[str]) -> list[dict]:
    """Fallback sin letra: dos vueltas de la progresión, un compás por
    acorde, para que la práctica guiada funcione igual (solo acordes)."""
    lineas = []
    for vuelta in range(2):
        for j, acorde in enumerate(progresion):
            idx = vuelta * len(progresion) + j
            lineas.append({"texto": "", "t_seg": round(idx * _SEG_POR_LINEA, 2), "acorde": acorde})
    return [{"nombre": "Progresión", "lineas": lineas}]


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
    Ultimate Guitar): letra por secciones con un acorde de la progresión de
    práctica sobre cada línea, timestamps para el desplazamiento automático
    y el consejo de RIFF. Si no hay letra disponible (LRCLIB), devuelve la
    progresión sola para practicar por compases.
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

    nivel = usuario.get("nivel", "principiante")
    progresion = _progresion_practica(det.get("dificultad"), nivel)
    letra = letras_service.obtener_letra(
        det["artista"], det["titulo"], det.get("duracion_seg")
    )

    if letra["tiene_letra"]:
        secciones = _armar_secciones(letra["lineas"], progresion, det.get("duracion_seg"))
    else:
        secciones = []
    tiene_letra = bool(secciones)
    if not tiene_letra:
        secciones = _secciones_sin_letra(progresion)

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
            "duracion_seg": det.get("duracion_seg"),
        },
        "tiene_letra": tiene_letra,
        "sincronizada": bool(letra.get("sincronizada")) and tiene_letra,
        "bpm": 60,
        "progresion": progresion,
        "secciones": secciones,
        "consejo": plan["consejo"],
        "ejercicio_id": ejercicio["id"],
        # Transparencia pedagógica: no es la transcripción original.
        "nota": "Acordes de práctica sugeridos por RIFF, no la transcripción exacta.",
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
