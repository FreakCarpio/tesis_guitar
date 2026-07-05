"""
Rutas de autenticación con Google.

Flujo:
1. El cliente Android obtiene un idToken de Google (Credential Manager).
2. POST /auth/google verifica ese idToken contra Google usando el Web Client ID.
3. Si el usuario no existe en MongoDB se crea automáticamente; si existe se
   actualiza su última sesión y datos de Google.
4. Se devuelve el perfil del usuario (identidad = `sub` de Google = user_id),
   que el cliente persiste en DataStore.

No se emite un token de sesión propio: la identidad estable es el `sub` de
Google, reutilizado como `user_id` en el resto de la API (p. ej. /practica).
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from database import usuarios, sesiones

router = APIRouter(prefix="/auth", tags=["auth"])

# Web Client ID de Google (público, no es secreto). Configurable por entorno.
GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    "715955170207-lrnnkauikqnb8la60pci3jh64vs6gn6c.apps.googleusercontent.com",
)


class GoogleLoginRequest(BaseModel):
    id_token: str


class PerfilUpdate(BaseModel):
    nombre: Optional[str] = None
    nivel: Optional[str] = None
    foto: Optional[str] = None


class OnboardingRequest(BaseModel):
    """Respuestas del onboarding inicial y/o marca de finalización.

    - experiencia: nunca | principiante | intermedio | avanzado
    - objetivo: aprender_desde_cero | mejorar_tecnica | aprender_canciones | practicar_diario
    - completado: True cuando el usuario terminó todo el flujo (afinador + 1ª práctica)
    """
    experiencia: Optional[str] = None
    objetivo: Optional[str] = None
    completado: Optional[bool] = None


# La experiencia declarada define el nivel inicial que usa Wilfredo.
NIVEL_POR_EXPERIENCIA = {
    "nunca": "principiante",
    "principiante": "principiante",
    "intermedio": "intermedio",
    "avanzado": "avanzado",
}


def _estadisticas(user_id: str) -> dict:
    """Estadísticas reales agregadas directamente desde las sesiones en Mongo."""
    agg = list(sesiones.aggregate([
        {"$match": {"usuario": user_id}},
        {"$group": {
            "_id": None,
            "sesiones": {"$sum": 1},
            "precision_promedio": {"$avg": "$precision"},
        }}
    ]))
    if not agg:
        return {"sesiones": 0, "precision_promedio": 0.0}
    return {
        "sesiones": int(agg[0]["sesiones"]),
        "precision_promedio": round(float(agg[0]["precision_promedio"] or 0), 4),
    }


def _perfil_publico(doc: dict) -> dict:
    """Proyección pública del perfil (sin _id de Mongo)."""
    return {
        "id": doc["user_id"],
        "nombre": doc.get("nombre"),
        "email": doc.get("email"),
        "foto": doc.get("foto"),
        "nivel": doc.get("nivel", "principiante"),
        "experiencia": doc.get("experiencia"),
        "objetivo": doc.get("objetivo"),
        "onboarding_completado": bool(doc.get("onboarding_completado", False)),
        "fecha_registro": doc.get("fecha_registro"),
        "ultima_sesion": doc.get("ultima_sesion"),
        "estadisticas": _estadisticas(doc["user_id"]),
    }


@router.post("/google")
async def login_google(req: GoogleLoginRequest):
    """Verifica el idToken de Google, crea/actualiza el usuario y devuelve su perfil."""
    try:
        info = google_id_token.verify_oauth2_token(
            req.id_token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Token de Google inválido o expirado.")

    sub = info.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token de Google sin identificador de usuario.")

    now = datetime.now(timezone.utc).isoformat()
    usuario = usuarios.find_one({"user_id": sub})

    if usuario is None:
        # Alta automática de usuario.
        usuario = {
            "user_id": sub,
            "nombre": info.get("name"),
            "email": info.get("email"),
            "foto": info.get("picture"),
            "nivel": "principiante",
            "precision": 0,
            "sesiones": 0,
            "onboarding_completado": False,
            "fecha_registro": now,
            "ultima_sesion": now,
        }
        usuarios.insert_one(usuario)
    else:
        # Refresca datos de Google y la última sesión.
        usuarios.update_one(
            {"user_id": sub},
            {"$set": {
                "ultima_sesion": now,
                "nombre": info.get("name", usuario.get("nombre")),
                "email": info.get("email", usuario.get("email")),
                "foto": info.get("picture", usuario.get("foto")),
            }},
        )
        usuario = usuarios.find_one({"user_id": sub})

    return _perfil_publico(usuario)


@router.get("/perfil/{user_id}")
async def get_perfil(user_id: str):
    """Devuelve el perfil del usuario con estadísticas reales."""
    usuario = usuarios.find_one({"user_id": user_id})
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return _perfil_publico(usuario)


@router.post("/onboarding/{user_id}")
async def save_onboarding(user_id: str, req: OnboardingRequest):
    """Guarda las respuestas del onboarding y/o lo marca como completado."""
    updates = {}
    if req.experiencia is not None:
        experiencia = req.experiencia.lower().strip()
        if experiencia not in NIVEL_POR_EXPERIENCIA:
            raise HTTPException(status_code=422, detail="Experiencia inválida.")
        updates["experiencia"] = experiencia
        updates["nivel"] = NIVEL_POR_EXPERIENCIA[experiencia]
    if req.objetivo is not None:
        updates["objetivo"] = req.objetivo.lower().strip()
    if req.completado is not None:
        updates["onboarding_completado"] = req.completado
    if not updates:
        raise HTTPException(status_code=400, detail="No se enviaron datos de onboarding.")

    result = usuarios.update_one({"user_id": user_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return _perfil_publico(usuarios.find_one({"user_id": user_id}))


@router.put("/perfil/{user_id}")
async def update_perfil(user_id: str, cambios: PerfilUpdate):
    """Actualiza campos editables del perfil (nombre, nivel, foto)."""
    updates = cambios.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar.")
    result = usuarios.update_one({"user_id": user_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return _perfil_publico(usuarios.find_one({"user_id": user_id}))
