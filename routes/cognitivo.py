"""
Motor Cognitivo (RIFF) - Endpoints de lectura.

GET /perfil/{user_id}/aprendizaje -> Learning Profile dinámico (MC1)
"""

from fastapi import APIRouter, HTTPException

from database import usuarios
from domain import conocimiento
from ia.cognitivo import learning_profile, progress_intelligence, recommendation_engine

router = APIRouter(tags=["cognitivo"])


@router.get("/plan/{user_id}/diario")
async def get_plan_diario(user_id: str, tz_offset_min: int = 0, regenerar: bool = False):
    """Plan del día (estable): calentamiento + recomendación del motor v2 +
    canción en aprendizaje, con duración total y XP potencial."""
    plan = recommendation_engine.plan_diario(user_id, tz_offset_min, regenerar)
    if plan is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    plan.pop("_id", None)
    return plan


@router.get("/plan/{user_id}/semanal")
async def get_plan_semanal(user_id: str, tz_offset_min: int = 0, regenerar: bool = False):
    """Plan de la semana ISO en curso (estable): focos por día según
    debilidades con evidencia, consolidación y su canción."""
    plan = recommendation_engine.plan_semanal(user_id, tz_offset_min, regenerar)
    if plan is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    plan.pop("_id", None)
    return plan


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


@router.get("/conocimiento/buscar")
async def buscar_conocimiento(q: str, nivel: str | None = None, k: int = 3):
    """Base de Conocimiento de guitarra (curada): búsqueda determinística."""
    resultados = conocimiento.buscar(q, nivel=nivel, k=k)
    return {"consulta": q, "resultados": resultados, "total": len(resultados),
            "categorias": conocimiento.CATEGORIAS}


@router.get("/perfil/{user_id}/aprendizaje")
async def get_perfil_aprendizaje(user_id: str):
    """Perfil dinámico del estudiante (preferencias, habilidades con
    evidencia, estilo de práctica, desempeño, canciones en aprendizaje)."""
    perfil = learning_profile.obtener_perfil(user_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    perfil.pop("_id", None)
    return perfil
