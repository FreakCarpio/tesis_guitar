"""
Motor Cognitivo (RIFF) - Endpoints de lectura.

GET /perfil/{user_id}/aprendizaje -> Learning Profile dinámico (MC1)
"""

from fastapi import APIRouter, HTTPException

from ia.cognitivo import learning_profile

router = APIRouter(tags=["cognitivo"])


@router.get("/perfil/{user_id}/aprendizaje")
async def get_perfil_aprendizaje(user_id: str):
    """Perfil dinámico del estudiante (preferencias, habilidades con
    evidencia, estilo de práctica, desempeño, canciones en aprendizaje)."""
    perfil = learning_profile.obtener_perfil(user_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    perfil.pop("_id", None)
    return perfil
