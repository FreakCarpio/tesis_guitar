"""
Wilfredo Context - Memoria pedagógica del tutor (P1.6).

Construye el contexto REAL del usuario que Wilfredo usa para responder
como un profesor que recuerda el desempeño, no como un chatbot genérico:

- perfil (nombre, nivel, objetivo declarado en el onboarding)
- habilidades débiles/fuertes (con decaimiento de confianza)
- racha, minutos de hoy
- historial de intentos (ExerciseAttempt): último intento, promedio y
  tendencia de puntuación, ejercicio más practicado
- biblioteca (canciones guardadas/favoritas)
- recomendación vigente del motor adaptativo (con su razón)

Todo determinístico y leído de MongoDB; sin IA generativa.
"""

from database import biblioteca_usuario, intentos_ejercicio, usuarios
from domain import habilidades as habilidades_dominio
from ia import motor_adaptativo_v1 as motor


def construir_contexto(user_id: str, tz_offset_min: int = 0) -> dict | None:
    """Contexto completo del usuario para el tutor. None si no existe."""
    usuario = usuarios.find_one({"user_id": user_id})
    if usuario is None:
        return None

    doc_hab = habilidades_dominio.obtener_habilidades(user_id)
    senales = motor.recopilar_senales(user_id, tz_offset_min)

    # Habilidades ordenadas por valor (nivel + progreso).
    vistas = []
    for slug in habilidades_dominio.HABILIDADES:
        hab = doc_hab["habilidades"][slug]
        vistas.append({
            "id": slug,
            "nombre": habilidades_dominio.NOMBRES[slug],
            "nivel": int(hab.get("nivel", 0)),
            "confianza": float(hab.get("confianza", 0)),
            "valor": habilidades_dominio.valor_habilidad(hab),
        })
    debiles = sorted(vistas, key=lambda v: (v["valor"], v["confianza"]))[:3]
    fuertes = [v for v in sorted(vistas, key=lambda v: -v["valor"]) if v["valor"] > 0][:3]

    # Historial de intentos (memoria de desempeño).
    intentos = list(
        intentos_ejercicio.find({"usuario": user_id}, {"_id": 0})
        .sort("fecha", -1)
        .limit(10)
    )
    ultimo = intentos[0] if intentos else None
    con_punt = [i for i in intentos if i.get("puntuacion") is not None]
    prom_punt = (
        sum(i["puntuacion"] for i in con_punt) / len(con_punt) if con_punt else None
    )
    # Tendencia: últimos 3 intentos puntuados vs los anteriores.
    tendencia = None
    if len(con_punt) >= 4:
        recientes = sum(i["puntuacion"] for i in con_punt[:3]) / 3
        previos = sum(i["puntuacion"] for i in con_punt[3:]) / len(con_punt[3:])
        if recientes > previos + 5:
            tendencia = "mejorando"
        elif recientes < previos - 5:
            tendencia = "bajando"
        else:
            tendencia = "estable"
    frecuencia: dict[str, int] = {}
    for i in intentos:
        frecuencia[i["ejercicio"]] = frecuencia.get(i["ejercicio"], 0) + 1
    mas_practicado = max(frecuencia, key=frecuencia.get) if frecuencia else None

    # Biblioteca.
    canciones = list(
        biblioteca_usuario.find({"usuario": user_id}, {"_id": 0, "titulo": 1, "artista": 1, "favorita": 1})
        .sort("fecha_agregada", -1)
        .limit(5)
    )

    # Recomendación vigente del motor (sin persistir en el log).
    decision = motor.decidir(user_id, offset_min=tz_offset_min, persistir=False)
    recomendacion = decision["recomendacion"] if decision else None
    ejercicio_rec = decision.get("ejercicio") if decision else None

    return {
        "nombre": (usuario.get("nombre") or "").split(" ")[0] or None,
        "nivel": usuario.get("nivel", "principiante"),
        "objetivo": usuario.get("objetivo"),
        "debiles": debiles,
        "fuertes": fuertes,
        "racha": senales["racha"],
        "minutos_hoy": senales["minutos_hoy"],
        "total_sesiones": senales["total_sesiones"],
        "intentos": intentos,
        "ultimo_intento": ultimo,
        "promedio_puntuacion": round(prom_punt, 1) if prom_punt is not None else None,
        "tendencia": tendencia,
        "mas_practicado": mas_practicado,
        "canciones": canciones,
        "recomendacion": recomendacion,
        "ejercicio_recomendado": ejercicio_rec,
    }
