"""
Entrenador (P1) - Endpoint que alimenta la Home como entrenador personal.

GET /entrenador/{user_id}?tz_offset_min=...

Ensambla en una sola llamada todo lo que la Home necesita:
- recomendación del motor (qué practicar hoy y POR QUÉ)
- objetivo del día (meta, minutos, tiempo restante) con zona horaria del usuario
- habilidades débiles y fuertes
- próximo logro (siguiente paso del camino o siguiente nivel)
- consejo personalizado de Wilfredo
- celebración (si corresponde)
"""

from fastapi import APIRouter, HTTPException

from domain import camino as camino_dominio
from domain import habilidades as habilidades_dominio
from ia import motor_adaptativo_v1 as motor
from ia import motor_config as cfg
from ia.cognitivo import adaptive_engine

router = APIRouter(prefix="/entrenador", tags=["entrenador"])


def _proximo_logro(camino: dict, doc_hab: dict) -> dict:
    """Siguiente meta tangible: completar el paso en curso o subir de nivel."""
    en_curso = next((p for p in camino["pasos"] if p["estado"] == "en_curso"), None)
    if en_curso is not None:
        # Habilidad y nivel objetivo que cierran el paso actual.
        objetivos = en_curso["criterios_salida"]
        slug = en_curso["habilidad"] if en_curso["habilidad"] in objetivos else next(iter(objetivos))
        nivel_objetivo = objetivos[slug]
        nivel_actual = int(doc_hab["habilidades"][slug]["nivel"])
        return {
            "tipo": "completar_paso",
            "titulo": f"Completa «{en_curso['nombre']}»",
            "detalle": f"Lleva {habilidades_dominio.NOMBRES[slug]} al nivel {nivel_objetivo} "
                       f"(vas por el {nivel_actual}).",
            "paso": en_curso["id"],
        }
    # Camino completo: el logro es seguir subiendo la habilidad más fuerte.
    return {
        "tipo": "maestria",
        "titulo": "¡Completaste el camino!",
        "detalle": "Sigue puliendo tus habilidades para alcanzar la maestría.",
        "paso": None,
    }


@router.get("/{user_id}")
async def get_entrenador(user_id: str, tz_offset_min: int = 0):
    """Payload completo del entrenador para la Home.

    MC4: decide el Adaptive Engine v2 (motor v1 + señales del Learning
    Profile). El shape de la respuesta es idéntico al de siempre.
    """
    resultado = adaptive_engine.decidir(user_id, offset_min=tz_offset_min)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    doc_hab = habilidades_dominio.obtener_habilidades(user_id)
    camino = camino_dominio.obtener_camino(user_id)
    senales = motor.recopilar_senales(user_id, tz_offset_min)

    # Habilidades débiles / fuertes (mismo criterio que /habilidades).
    vistas = []
    for slug in habilidades_dominio.HABILIDADES:
        hab = doc_hab["habilidades"][slug]
        vistas.append({
            "id": slug,
            "nombre": habilidades_dominio.NOMBRES[slug],
            "nivel": int(hab.get("nivel", 0)),
            "confianza": round(float(hab.get("confianza", 0)), 4),
            "valor": round(habilidades_dominio.valor_habilidad(hab), 4),
        })
    debiles = sorted(vistas, key=lambda v: (v["valor"], v["confianza"]))[:3]
    fuertes = [v for v in sorted(vistas, key=lambda v: -v["valor"]) if v["valor"] > 0][:3]

    # Consejo personalizado (usa la habilidad más débil real).
    slug_debil = debiles[0]["id"]
    senales_debil = {
        "dias_sin_practica": motor._dias_sin_practica(
            doc_hab["habilidades"][slug_debil], senales["hoy_local"], tz_offset_min
        ),
        "confianza": float(doc_hab["habilidades"][slug_debil].get("confianza", 0)),
    }
    consejo = motor._consejo_personalizado(slug_debil, senales_debil, senales)

    minutos_hoy = senales["minutos_hoy"]
    restante = max(0.0, cfg.META_DIARIA_MIN - minutos_hoy)

    return {
        "usuario": user_id,
        "recomendacion": resultado["recomendacion"],
        "ejercicio": resultado["ejercicio"],
        "celebracion": resultado["celebracion"],
        "consejo": consejo,
        "objetivo_dia": {
            "meta_min": cfg.META_DIARIA_MIN,
            "minutos_hoy": minutos_hoy,
            "restante_min": round(restante, 1),
            "cumplido": minutos_hoy >= cfg.META_DIARIA_MIN,
        },
        "racha": senales["racha"],
        "habilidades_debiles": debiles,
        "habilidades_fuertes": fuertes,
        "proximo_logro": _proximo_logro(camino, doc_hab),
        "paso_actual": camino["paso_actual"],
    }
