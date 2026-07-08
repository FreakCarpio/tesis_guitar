"""
RIFF AI (MC8) - Orquestador conversacional del Motor Cognitivo.

RIFF = Reconocimiento Inteligente para Formación y Feedback (nombre visual
del tutor; los endpoints conservan /wilfredo por retrocompatibilidad).

Pipeline: Context Builder (contexto selectivo por intención) → LLMProvider
activo → fallback determinístico garantizado (ReglasProvider). La memoria
conversacional vive en `conversaciones` (últimos turnos por usuario).
"""

from datetime import datetime, timezone

from database import conversaciones, usuarios
from ia.cognitivo import context_builder, llm_provider

MAX_TURNOS_MEMORIA = 8


def _guardar_turno(user_id: str, rol: str, texto: str, intencion: str | None = None) -> None:
    conversaciones.insert_one({
        "usuario": user_id,
        "rol": rol,                       # "usuario" | "riff"
        "texto": texto,
        "intencion": intencion,
        "fecha": datetime.now(timezone.utc).isoformat(),
    })


def _historial(user_id: str) -> list[dict]:
    docs = list(
        conversaciones.find({"usuario": user_id}, {"_id": 0, "rol": 1, "texto": 1})
        .sort("fecha", -1)
        .limit(MAX_TURNOS_MEMORIA)
    )
    return list(reversed(docs))


def responder(user_id: str, mensaje: str, tz_offset_min: int = 0) -> dict | None:
    """Respuesta de RIFF para un usuario. None si el usuario no existe."""
    if usuarios.find_one({"user_id": user_id}) is None:
        return None

    contexto = context_builder.construir(user_id, mensaje, tz_offset_min)
    if contexto is None:
        return None
    historial = _historial(user_id)
    _guardar_turno(user_id, "usuario", mensaje, contexto["intencion"])

    # Proveedor activo con fallback determinístico SIEMPRE garantizado.
    respuesta: str | None = None
    proveedor = llm_provider.obtener_provider()
    try:
        respuesta = proveedor.generar(mensaje, contexto, historial)
    except Exception:
        respuesta = None
    if not respuesta:
        respuesta = llm_provider.fallback_provider().generar(mensaje, contexto, historial)

    _guardar_turno(user_id, "riff", respuesta, contexto["intencion"])
    return {
        "respuesta": respuesta,
        "nivel": contexto.get("nivel", "principiante"),
        "intencion": contexto["intencion"],
        "proveedor": proveedor.nombre,
    }
