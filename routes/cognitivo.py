"""
Motor Cognitivo (RIFF) - Endpoints de lectura.

GET /perfil/{user_id}/aprendizaje -> Learning Profile dinámico (MC1)
"""

from fastapi import APIRouter, HTTPException

from database import usuarios
from ia.cognitivo import learning_profile, progress_intelligence

router = APIRouter(tags=["cognitivo"])


@router.get("/perfil/{user_id}/hitos")
async def get_hitos(user_id: str, limite: int = 20):
    """Hitos detectados por Progress Intelligence (logros, evolución,
    estancamiento, recaídas), más recientes primero."""
    if usuarios.find_one({"user_id": user_id}) is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return {
        "usuario": user_id,
        "hitos": progress_intelligence.obtener_hitos(user_id, limite),
        "estado": progress_intelligence.estado_aprendizaje(user_id),
    }


@router.get("/perfil/{user_id}/aprendizaje")
async def get_perfil_aprendizaje(user_id: str):
    """Perfil dinámico del estudiante (preferencias, habilidades con
    evidencia, estilo de práctica, desempeño, canciones en aprendizaje)."""
    perfil = learning_profile.obtener_perfil(user_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    perfil.pop("_id", None)
    return perfil
