"""
Biblioteca - Canciones guardadas y favoritas del usuario (Song Detail).

Un documento por (usuario, canción) con flags `guardada` y `favorita` y un
snapshot mínimo de metadata (título/artista/portada) para listar sin volver
a consultar proveedores.

GET    /biblioteca/{user_id}              -> lista (con ?tipo=guardadas|favoritas)
POST   /biblioteca/{user_id}/{song_id}    -> fija flags {guardada?, favorita?}
DELETE /biblioteca/{user_id}/{song_id}    -> elimina la entrada
"""

from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import biblioteca_usuario, usuarios
from services import canciones_service

router = APIRouter(prefix="/biblioteca", tags=["biblioteca"])


class BibliotecaUpdate(BaseModel):
    guardada: Optional[bool] = None
    favorita: Optional[bool] = None


def _item_publico(doc: dict) -> dict:
    return {
        "song_id": doc["song_id"],
        "titulo": doc.get("titulo", ""),
        "artista": doc.get("artista", ""),
        "portada": doc.get("portada"),
        "guardada": bool(doc.get("guardada", False)),
        "favorita": bool(doc.get("favorita", False)),
        "practicas": int(doc.get("practicas", 0) or 0),
        "fecha_agregada": doc.get("fecha_agregada"),
        "ultima_practica": doc.get("ultima_practica"),
    }


@router.get("/{user_id}")
async def listar(user_id: str, tipo: Optional[str] = None):
    """Biblioteca del usuario. `tipo` filtra: guardadas | favoritas."""
    if usuarios.find_one({"user_id": user_id}) is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    filtro: dict = {"usuario": user_id}
    if tipo == "guardadas":
        filtro["guardada"] = True
    elif tipo == "favoritas":
        filtro["favorita"] = True
    docs = list(biblioteca_usuario.find(filtro).sort("fecha_agregada", -1))
    return {"usuario": user_id, "items": [_item_publico(d) for d in docs], "total": len(docs)}


@router.get("/{user_id}/{song_id}")
async def estado(user_id: str, song_id: int):
    """Estado de una canción en la biblioteca (para pintar los botones)."""
    doc = biblioteca_usuario.find_one({"usuario": user_id, "song_id": song_id})
    if doc is None:
        return {"song_id": song_id, "guardada": False, "favorita": False, "practicas": 0}
    return _item_publico(doc)


@router.post("/{user_id}/{song_id}")
async def actualizar(user_id: str, song_id: int, cambios: BibliotecaUpdate):
    """Fija los flags guardada/favorita. Si ambos quedan en False, se elimina."""
    if usuarios.find_one({"user_id": user_id}) is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if cambios.guardada is None and cambios.favorita is None:
        raise HTTPException(status_code=400, detail="No se enviaron cambios.")

    doc = biblioteca_usuario.find_one({"usuario": user_id, "song_id": song_id})

    # Snapshot de metadata al crear la entrada (desde el caché del proxy).
    if doc is None:
        try:
            det = canciones_service.obtener_detalle(song_id)
        except requests.RequestException:
            det = None
        if det is None:
            raise HTTPException(status_code=404, detail="Canción no encontrada.")
        doc = {
            "usuario": user_id,
            "song_id": song_id,
            "titulo": det["titulo"],
            "artista": det["artista"],
            "portada": det.get("portada"),
            "guardada": False,
            "favorita": False,
            "practicas": 0,
            "fecha_agregada": datetime.now(timezone.utc).isoformat(),
        }

    if cambios.guardada is not None:
        doc["guardada"] = cambios.guardada
    if cambios.favorita is not None:
        doc["favorita"] = cambios.favorita

    if not doc["guardada"] and not doc["favorita"]:
        biblioteca_usuario.delete_one({"usuario": user_id, "song_id": song_id})
        return {"song_id": song_id, "guardada": False, "favorita": False, "practicas": 0}

    biblioteca_usuario.update_one(
        {"usuario": user_id, "song_id": song_id},
        {"$set": {k: v for k, v in doc.items() if k != "_id"}},
        upsert=True,
    )
    return _item_publico(doc)


@router.delete("/{user_id}/{song_id}")
async def eliminar(user_id: str, song_id: int):
    """Elimina la canción de la biblioteca."""
    biblioteca_usuario.delete_one({"usuario": user_id, "song_id": song_id})
    return {"song_id": song_id, "guardada": False, "favorita": False}
