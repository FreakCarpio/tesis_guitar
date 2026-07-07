"""
Adaptive Learning Engine v2 (MC4).

Envuelve al motor v1 (que sigue intacto) y aplica encima las señales del
Learning Profile que v1 no conocía. Sigue determinístico, explicable y
auditable: cada decisión final se persiste en `recomendaciones` con la
fuente ("motor_v2") y las señales que la modificaron.

Reglas nuevas (en orden, sobre la decisión base de v1):
1. REGRESO tras pausa (recaída): refuerzo suave con la habilidad más
   fuerte a dificultad baja — reconstruir confianza antes que exigir.
2. ESTANCAMIENTO: si v1 insiste en el ejercicio estancado, cambia de
   estrategia (variante de la misma habilidad o bajar dificultad).
3. OBJETIVO declarado en el onboarding (por fin explotado): quien declaró
   "aprender_canciones" y tiene una canción en aprendizaje recibe sesgo
   hacia practicarla.
4. EVIDENCIA: nunca subir dificultad con evidencia baja en esa habilidad
   (regla de oro del perfil).
"""

from datetime import datetime, timezone

from database import recomendaciones
from domain import ejercicios as ejercicios_dominio
from domain import habilidades as habilidades_dominio
from ia import motor_adaptativo_v1 as motor_v1
from ia.cognitivo import learning_profile

DIFICULTAD_REFUERZO = 1


def _persistir(user_id: str, decision: dict) -> None:
    recomendaciones.insert_one({
        "usuario": user_id,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "tipo": decision["tipo"],
        "habilidad": decision.get("habilidad"),
        "ejercicio_id": decision.get("ejercicio_id"),
        "dificultad": decision.get("dificultad"),
        "duracion_min": decision.get("duracion_min"),
        "razon": decision["razon"],
        "senales": {**decision.get("senales", {}), "fuente": "motor_v2"},
        "consumida": False,
    })


def _habilidad_perfil(perfil: dict, slug: str) -> dict | None:
    return next((h for h in perfil.get("habilidades", []) if h["id"] == slug), None)


def decidir(user_id: str, offset_min: int = 0, persistir: bool = True) -> dict | None:
    """Decisión v2: v1 como base + señales del perfil. Shape idéntico a v1."""
    base = motor_v1.decidir(user_id, offset_min=offset_min, persistir=False)
    if base is None:
        return None
    perfil = learning_profile.obtener_perfil(user_id) or {}
    decision = base["recomendacion"]
    estado = perfil.get("estado", {})
    objetivo = (perfil.get("preferencias") or {}).get("objetivo")

    # El descanso y las celebraciones de v1 se respetan siempre.
    if decision["tipo"] != "descanso":

        # --- Regla 1: regreso tras pausa -> refuerzo suave ---
        if estado.get("regreso_reciente"):
            fuerte = next(
                (h for h in perfil.get("habilidades", [])
                 if h["nivel"] > 0 and h["evidencia"] != "baja"),
                None,
            ) or (perfil.get("habilidades") or [{}])[0]
            slug = fuerte.get("id", decision.get("habilidad") or "afinacion")
            ejercicio = ejercicios_dominio.ejercicio_para_habilidad(slug, DIFICULTAD_REFUERZO)
            decision = {
                "tipo": "practicar",
                "habilidad": slug,
                "ejercicio_id": ejercicio["id"],
                "dificultad": DIFICULTAD_REFUERZO,
                "duracion_min": ejercicio["duracion_min"],
                "razon": (f"Volviste tras una pausa: retomamos con "
                          f"{habilidades_dominio.NOMBRES.get(slug, slug)} a dificultad "
                          f"baja para recuperar sensaciones antes de exigir. 🌱"),
                "senales": {"regla": "regreso", "habilidad_fuerte": slug},
            }
            base["ejercicio"] = ejercicio

        # --- Regla 2: estancamiento -> cambiar de estrategia ---
        elif decision.get("ejercicio_id") in (estado.get("estancado_en") or []):
            slug = decision.get("habilidad")
            alternativas = [
                e for e in ejercicios_dominio.ejercicios_por_habilidad(slug or "")
                if e["id"] != decision["ejercicio_id"]
            ]
            if alternativas:
                nuevo = alternativas[0]
                razon = (f"Llevas varias sesiones en «{decision['ejercicio_id']}» sin "
                         f"superar tu marca: probamos «{nuevo['nombre']}» para atacar "
                         f"la misma habilidad desde otro ángulo. 🔄")
            else:
                nuevo = ejercicios_dominio.ejercicio_para_habilidad(
                    slug or "precision", max(1, (decision.get("dificultad") or 2) - 1)
                )
                razon = (f"Meseta en «{decision['ejercicio_id']}»: bajamos la "
                         f"dificultad para consolidar la base y romper el "
                         f"estancamiento. 🔄")
            decision = {
                "tipo": "practicar",
                "habilidad": nuevo["habilidad"],
                "ejercicio_id": nuevo["id"],
                "dificultad": nuevo["dificultad"],
                "duracion_min": nuevo["duracion_min"],
                "razon": razon,
                "senales": {"regla": "estancamiento",
                            "ejercicio_estancado": base["recomendacion"]["ejercicio_id"]},
            }
            base["ejercicio"] = nuevo

        # --- Regla 3: objetivo "aprender_canciones" -> sesgo a su canción ---
        elif (objetivo == "aprender_canciones"
              and decision["tipo"] == "practicar"):
            en_curso = next(
                (c for c in perfil.get("canciones", []) if c["estado"] == "aprendiendo"),
                None,
            )
            if en_curso is not None:
                ejercicio = ejercicios_dominio.obtener_ejercicio("primera_cancion")
                decision = {
                    "tipo": "practicar",
                    "habilidad": ejercicio["habilidad"],
                    "ejercicio_id": ejercicio["id"],
                    "dificultad": ejercicio["dificultad"],
                    "duracion_min": ejercicio["duracion_min"],
                    "razon": (f"Tu objetivo es aprender canciones y tienes "
                              f"«{en_curso['titulo']}» a medio dominar "
                              f"(mejor marca: {int(en_curso['mejor_puntuacion'] or 0)}). "
                              f"Hoy le toca a ella. 🎶"),
                    "senales": {"regla": "objetivo_canciones",
                                "cancion_id": en_curso["song_id"]},
                    "cancion_id": en_curso["song_id"],
                }
                base["ejercicio"] = ejercicio

        # --- Regla 4: no subir dificultad con evidencia baja ---
        if decision["tipo"] == "subir_dificultad":
            hab = _habilidad_perfil(perfil, decision.get("habilidad") or "")
            if hab is not None and hab.get("evidencia") == "baja":
                decision = {
                    **decision,
                    "tipo": "practicar",
                    "dificultad": max(1, (decision.get("dificultad") or 2) - 1),
                    "razon": (f"Vas muy bien en "
                              f"{habilidades_dominio.NOMBRES.get(hab['id'], hab['id'])}, "
                              f"pero con pocas muestras aún ({hab['muestras']}). Una "
                              f"sesión más al mismo nivel para confirmar antes de subir. 🧪"),
                    "senales": {**decision.get("senales", {}),
                                "regla": "evidencia_insuficiente",
                                "muestras": hab["muestras"]},
                }

    base["recomendacion"] = decision
    if persistir:
        _persistir(user_id, decision)
    return base
