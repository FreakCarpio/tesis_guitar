"""
Camino de Aprendizaje (P1).

Ruta de 10 pasos inspirada en Duolingo/Yousician/Simply Guitar:

  Afinación → Acordes abiertos → Cambios lentos → Ritmo básico →
  Primera canción → Arpegios → Fingerstyle → Cejillas → Escalas →
  Canciones completas

La definición de los pasos es CÓDIGO versionado. El estado por usuario se
DERIVA de sus habilidades en tiempo de lectura (no se duplica estado):

- completado : cumple los criterios de salida del paso
- disponible : cumple los requisitos de entrada
- bloqueado  : no cumple los requisitos
- en_curso   : el primer paso disponible no completado

En Mongo (`camino_usuario`) solo se guardan las fechas de completado y los
refuerzos que el motor decide (volver a un paso anterior cuando la
confianza de su habilidad decae). Así la ruta cambia dinámicamente según
el desempeño sin inconsistencias de estado duplicado.
"""

from datetime import datetime, timezone

from database import camino_usuario
from domain import habilidades as habilidades_dominio

PASOS = [
    {
        "id": "afinacion",
        "nombre": "Afinación",
        "descripcion": "Aprende a dejar tu guitarra lista para sonar bien",
        "habilidad": "afinacion",
        "ejercicios": ["afinacion"],
        "requisitos": {},
        "criterios_salida": {"afinacion": 2},
    },
    {
        "id": "acordes_abiertos",
        "nombre": "Acordes abiertos",
        "descripcion": "Am, C, G, D, Em: la base de cientos de canciones",
        "habilidad": "acordes_abiertos",
        "ejercicios": ["acordes"],
        "requisitos": {"afinacion": 1},
        "criterios_salida": {"acordes_abiertos": 2},
    },
    {
        "id": "cambios_lentos",
        "nombre": "Cambios lentos",
        "descripcion": "Transiciones limpias entre acordes, sin prisa",
        "habilidad": "cambios_acordes",
        "ejercicios": ["cambios_acordes"],
        "requisitos": {"acordes_abiertos": 1},
        "criterios_salida": {"cambios_acordes": 2},
    },
    {
        "id": "ritmo_basico",
        "nombre": "Ritmo básico",
        "descripcion": "Pulso, compás y tus primeros patrones de rasgueo",
        "habilidad": "ritmo",
        "ejercicios": ["ritmo", "rasgueo"],
        "requisitos": {"cambios_acordes": 1},
        "criterios_salida": {"ritmo": 2},
    },
    {
        "id": "primera_cancion",
        "nombre": "Primera canción",
        "descripcion": "Tu primera canción completa de 3 acordes",
        "habilidad": "cambios_acordes",
        "ejercicios": ["primera_cancion"],
        "requisitos": {"cambios_acordes": 2, "ritmo": 1},
        "criterios_salida": {"cambios_acordes": 3, "ritmo": 2},
    },
    {
        "id": "arpegios",
        "nombre": "Arpegios",
        "descripcion": "Las notas del acorde, una por una",
        "habilidad": "arpegios",
        "ejercicios": ["arpegios"],
        "requisitos": {"cambios_acordes": 2},
        "criterios_salida": {"arpegios": 2},
    },
    {
        "id": "fingerstyle",
        "nombre": "Fingerstyle",
        "descripcion": "Melodía y acompañamiento con los dedos",
        "habilidad": "fingerstyle",
        "ejercicios": ["fingerpicking"],
        "requisitos": {"arpegios": 1},
        "criterios_salida": {"fingerstyle": 2},
    },
    {
        "id": "cejillas",
        "nombre": "Cejillas",
        "descripcion": "F, Bm y el mástil completo",
        "habilidad": "acordes_cejilla",
        "ejercicios": ["cejilla"],
        "requisitos": {"acordes_abiertos": 3, "cambios_acordes": 2},
        "criterios_salida": {"acordes_cejilla": 2},
    },
    {
        "id": "escalas",
        "nombre": "Escalas",
        "descripcion": "Digitación, oído y el mapa del diapasón",
        "habilidad": "escalas",
        "ejercicios": ["escalas"],
        "requisitos": {"precision": 2},
        "criterios_salida": {"escalas": 2},
    },
    {
        "id": "canciones_completas",
        "nombre": "Canciones completas",
        "descripcion": "Repertorio real de principio a fin",
        "habilidad": "lectura",
        "ejercicios": ["lectura", "velocidad"],
        "requisitos": {"cambios_acordes": 3, "ritmo": 2},
        "criterios_salida": {"lectura": 2, "velocidad": 2},
    },
]

_PASO_POR_ID = {p["id"]: p for p in PASOS}


def _cumple(niveles: dict, condiciones: dict) -> bool:
    return all(niveles.get(hab, 0) >= minimo for hab, minimo in condiciones.items())


def _niveles(doc_habilidades: dict) -> dict:
    return {
        slug: int(hab.get("nivel", 0))
        for slug, hab in doc_habilidades["habilidades"].items()
    }


def obtener_camino(user_id: str) -> dict | None:
    """Estado completo del camino del usuario (derivado de sus habilidades).

    Registra en `camino_usuario` la fecha de los pasos recién completados
    y devuelve pasos con estado, paso actual y refuerzos pendientes.
    """
    doc_hab = habilidades_dominio.obtener_habilidades(user_id)
    if doc_hab is None:
        return None
    niveles = _niveles(doc_hab)

    registro = camino_usuario.find_one({"usuario": user_id}) or {
        "usuario": user_id,
        "completados": [],
        "refuerzos_pendientes": [],
    }
    fechas_completado = {c["paso"]: c["fecha"] for c in registro.get("completados", [])}
    refuerzos = [r for r in registro.get("refuerzos_pendientes", []) if r in _PASO_POR_ID]

    ahora = datetime.now(timezone.utc).isoformat()
    pasos_vista = []
    paso_actual = None
    nuevos_completados = []

    for paso in PASOS:
        completado = _cumple(niveles, paso["criterios_salida"])
        disponible = _cumple(niveles, paso["requisitos"])

        if completado and paso["id"] not in fechas_completado:
            fechas_completado[paso["id"]] = ahora
            nuevos_completados.append({"paso": paso["id"], "fecha": ahora})

        if completado:
            estado = "completado"
        elif disponible:
            estado = "en_curso" if paso_actual is None else "disponible"
            if paso_actual is None:
                paso_actual = paso["id"]
        else:
            estado = "bloqueado"

        pasos_vista.append({
            "id": paso["id"],
            "nombre": paso["nombre"],
            "descripcion": paso["descripcion"],
            "habilidad": paso["habilidad"],
            "ejercicios": paso["ejercicios"],
            "requisitos": paso["requisitos"],
            "criterios_salida": paso["criterios_salida"],
            "estado": estado,
            "fecha_completado": fechas_completado.get(paso["id"]),
        })

    # Camino terminado: el "paso actual" es el último (seguir puliendo).
    if paso_actual is None:
        paso_actual = PASOS[-1]["id"]

    # Un refuerzo pendiente tiene prioridad sobre el paso natural.
    if refuerzos:
        paso_actual = refuerzos[0]

    if nuevos_completados:
        camino_usuario.update_one(
            {"usuario": user_id},
            {
                "$push": {"completados": {"$each": nuevos_completados}},
                "$setOnInsert": {"refuerzos_pendientes": []},
            },
            upsert=True,
        )

    return {
        "usuario": user_id,
        "paso_actual": paso_actual,
        "pasos": pasos_vista,
        "refuerzos_pendientes": refuerzos,
        "completados": len(fechas_completado),
        "total_pasos": len(PASOS),
    }


def paso_por_id(paso_id: str) -> dict | None:
    return _PASO_POR_ID.get(paso_id)


def agregar_refuerzo(user_id: str, paso_id: str) -> None:
    """El motor manda al usuario de vuelta a un paso anterior (refuerzo)."""
    if paso_id not in _PASO_POR_ID:
        return
    camino_usuario.update_one(
        {"usuario": user_id},
        {"$addToSet": {"refuerzos_pendientes": paso_id}, "$setOnInsert": {"completados": []}},
        upsert=True,
    )


def resolver_refuerzo(user_id: str, paso_id: str) -> None:
    """Quita un refuerzo cumplido (la habilidad recuperó confianza)."""
    camino_usuario.update_one(
        {"usuario": user_id},
        {"$pull": {"refuerzos_pendientes": paso_id}},
    )
