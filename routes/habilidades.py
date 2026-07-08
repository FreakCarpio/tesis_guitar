"""
Habilidades - Endpoints de lectura del sistema de habilidades (P1).

GET /habilidades/{user_id}            -> estado de las 12 habilidades
GET /habilidades/{user_id}/{slug}     -> historial de una habilidad
"""

from fastapi import APIRouter, HTTPException

from domain import habilidades as dominio

router = APIRouter(prefix="/habilidades", tags=["habilidades"])


def _vista_habilidad(slug: str, hab: dict) -> dict:
    return {
        "id": slug,
        "nombre": dominio.NOMBRES[slug],
        "nivel": int(hab.get("nivel", 0)),
        "progreso": round(float(hab.get("progreso", 0)), 4),
        "confianza": round(float(hab.get("confianza", 0)), 4),
        "intentos": int(hab.get("intentos", 0)),
        "ultima_practica": hab.get("ultima_practica"),
        "valor": round(dominio.valor_habilidad(hab), 4),
    }


@router.get("/{user_id}")
async def get_habilidades(user_id: str):
    """Estado actual de las 12 habilidades (con decaimiento de confianza)."""
    doc = dominio.obtener_habilidades(user_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    vistas = [
        _vista_habilidad(slug, doc["habilidades"][slug])
        for slug in dominio.HABILIDADES
    ]
    # Débiles: menor valor (nivel+progreso), desempate por menor confianza.
    # Fuertes: mayor valor, solo habilidades con evidencia (valor > 0).
    orden_debiles = sorted(vistas, key=lambda v: (v["valor"], v["confianza"]))
    orden_fuertes = [v for v in sorted(vistas, key=lambda v: -v["valor"]) if v["valor"] > 0]

    return {
        "usuario": user_id,
        "habilidades": vistas,
        "debiles": [v["id"] for v in orden_debiles[:3]],
        "fuertes": [v["id"] for v in orden_fuertes[:3]],
        "actualizado": doc.get("actualizado"),
    }


@router.get("/{user_id}/{habilidad}")
async def get_historial_habilidad(user_id: str, habilidad: str):
    """Historial (eventos) de una habilidad concreta."""
    if habilidad not in dominio.HABILIDADES:
        raise HTTPException(status_code=404, detail="Habilidad desconocida.")
    doc = dominio.obtener_habilidades(user_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return {
        "usuario": user_id,
        "habilidad": habilidad,
        "estado": _vista_habilidad(habilidad, doc["habilidades"][habilidad]),
        "historial": dominio.historial_habilidad(user_id, habilidad),
    }
