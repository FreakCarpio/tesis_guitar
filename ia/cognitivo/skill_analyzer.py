"""
Skill Analyzer (MC3) - Fortalezas y debilidades por EVIDENCIA real.

A diferencia del nivel/confianza de P1 (que resume progreso), este módulo
analiza los PASOS ejecutados en los intentos (ExerciseAttempt): qué skills
rinden bien de verdad, cuáles fallan, y qué TIPOS de paso le cuestan al
alumno (p. ej. domina SCALE pero falla CHORD_CHANGE sistemáticamente).

Regla de oro heredada del perfil: nada se declara fortaleza o debilidad
sin evidencia suficiente; con pocas muestras se dice "evidencia
insuficiente" en vez de inventar un diagnóstico.
"""

from domain import ejercicios as ejercicios_dominio
from domain import habilidades as habilidades_dominio

# Muestras mínimas para emitir un diagnóstico por skill o por tipo de paso.
MIN_MUESTRAS_SKILL = 4
MIN_MUESTRAS_TIPO = 4

# Umbrales de tasa de acierto (aciertos / esperados de los pasos).
TASA_FORTALEZA = 0.75
TASA_DEBILIDAD = 0.5


def _acumular(destino: dict, clave: str, paso: dict) -> None:
    d = destino.setdefault(clave, {
        "muestras": 0, "aciertos": 0, "esperados": 0,
        "completados": 0, "suma_puntuacion": 0.0, "suma_dificultad": 0,
    })
    d["muestras"] += 1
    d["aciertos"] += int(paso.get("aciertos", 0) or 0)
    d["esperados"] += int(paso.get("total", 0) or 0)
    d["completados"] += 1 if paso.get("completado") else 0
    d["suma_puntuacion"] += float(paso.get("puntuacion", 0) or 0)
    d["suma_dificultad"] += int(paso.get("difficulty", 0) or 0)


def _resumir(d: dict) -> dict:
    n = d["muestras"]
    esperados = d["esperados"]
    return {
        "muestras": n,
        "tasa_acierto": round(d["aciertos"] / esperados, 3) if esperados else None,
        "tasa_completado": round(d["completados"] / n, 3) if n else None,
        "puntuacion_media": round(d["suma_puntuacion"] / n, 1) if n else None,
        "dificultad_media": round(d["suma_dificultad"] / n, 1) if n else None,
    }


def analizar(user_id: str, intentos: list[dict]) -> dict:
    """Análisis de skills y tipos de paso desde los intentos dados.

    Recibe los intentos ya cargados (el Learning Profile los tiene) para no
    duplicar queries. Devuelve fortalezas/debilidades con evidencia y los
    tipos de paso con error frecuente.
    """
    por_skill: dict[str, dict] = {}
    por_tipo: dict[str, dict] = {}

    for intento in intentos:
        for paso in (intento.get("pasos") or []):
            skill = paso.get("skill")
            tipo = paso.get("tipo")
            if skill in habilidades_dominio.NOMBRES:
                _acumular(por_skill, skill, paso)
            if tipo in ejercicios_dominio.TIPOS_PASO:
                _acumular(por_tipo, tipo, paso)

    skills = {slug: _resumir(d) for slug, d in por_skill.items()}
    tipos = {t: _resumir(d) for t, d in por_tipo.items()}

    fortalezas, debilidades, sin_evidencia = [], [], []
    for slug, s in skills.items():
        nombre = habilidades_dominio.NOMBRES[slug]
        if s["muestras"] < MIN_MUESTRAS_SKILL or s["tasa_acierto"] is None:
            sin_evidencia.append({"id": slug, "nombre": nombre, "muestras": s["muestras"]})
        elif s["tasa_acierto"] >= TASA_FORTALEZA:
            fortalezas.append({"id": slug, "nombre": nombre, **s})
        elif s["tasa_acierto"] < TASA_DEBILIDAD:
            debilidades.append({"id": slug, "nombre": nombre, **s})

    errores_frecuentes = [
        {"tipo": t, **r}
        for t, r in tipos.items()
        if r["muestras"] >= MIN_MUESTRAS_TIPO
        and r["tasa_acierto"] is not None
        and r["tasa_acierto"] < TASA_DEBILIDAD
    ]

    return {
        "skills": skills,
        "tipos_paso": tipos,
        "fortalezas": sorted(fortalezas, key=lambda x: -(x["tasa_acierto"] or 0)),
        "debilidades": sorted(debilidades, key=lambda x: x["tasa_acierto"] or 0),
        "sin_evidencia": sin_evidencia,
        "errores_frecuentes": sorted(errores_frecuentes, key=lambda x: x["tasa_acierto"] or 0),
    }
