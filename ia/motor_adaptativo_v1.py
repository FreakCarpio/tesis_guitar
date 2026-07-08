"""
Motor Adaptativo v1 (P1).

Motor determinístico y EXPLICABLE (sin IA generativa). Analiza el historial
real del usuario y decide qué hacer a continuación, dando siempre una razón.

Señales de entrada (todas desde MongoDB):
- historial de sesiones (precisión, consistencia, ejercicio, fecha, duración)
- progreso por habilidad (nivel, confianza con decaimiento)
- posición en el camino de aprendizaje
- tiempo practicado hoy y racha

Decisiones posibles (una principal + celebración opcional):
- practicar / repetir / subir_dificultad / bajar_dificultad / descanso
- felicitar (celebración, no reemplaza la práctica)

Cada decisión se registra en la colección `recomendaciones` con sus señales,
de modo que toda recomendación mostrada al usuario es auditable.
"""

from datetime import datetime, timedelta, timezone

from database import recomendaciones, sesiones
from domain import camino as camino_dominio
from domain import ejercicios as ejercicios_dominio
from domain import habilidades as habilidades_dominio
from ia import motor_config as cfg


# --------------------------------------------------------------------------
# Señales
# --------------------------------------------------------------------------

def _fecha_local(iso: str | None, offset_min: int):
    """Fecha local (según tz del usuario) de una marca ISO, o None."""
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt.astimezone(timezone.utc) + timedelta(minutes=offset_min)).date()


def _rendimiento(doc: dict) -> float:
    return habilidades_dominio.rendimiento_sesion(
        float(doc.get("precision", 0) or 0),
        float(doc.get("consistencia", 0) or 0),
    )


def _cumple_criterios(doc: dict, ejercicio: dict) -> bool:
    crit = ejercicio["criterios"]
    return (
        float(doc.get("precision", 0) or 0) >= crit["precision_min"]
        and float(doc.get("consistencia", 0) or 0) >= crit["consistencia_min"]
        and int(doc.get("duracion_seg", 0) or 0) >= crit["duracion_min_seg"]
    )


def recopilar_senales(user_id: str, offset_min: int = 0) -> dict:
    """Reúne todas las señales que el motor necesita para decidir."""
    docs = list(sesiones.find({"usuario": user_id}).sort("_id", 1))
    ahora = datetime.now(timezone.utc)
    hoy_local = (ahora + timedelta(minutes=offset_min)).date()

    minutos_hoy = 0.0
    dias_practica = set()
    for d in docs:
        fl = _fecha_local(d.get("fecha"), offset_min)
        if fl is not None:
            dias_practica.add(fl)
            if fl == hoy_local:
                minutos_hoy += float(d.get("duracion_seg", 0) or 0) / 60.0

    # Racha (misma semántica que /progreso).
    racha = 0
    if dias_practica:
        inicio = hoy_local if hoy_local in dias_practica else hoy_local - timedelta(days=1)
        if inicio in dias_practica:
            dia = inicio
            while dia in dias_practica:
                racha += 1
                dia -= timedelta(days=1)

    ultima = docs[-1] if docs else None
    ultima_aprobada = None
    if ultima is not None:
        ej = ejercicios_dominio.obtener_ejercicio(ultima.get("ejercicio", "practica_general"))
        ultima_aprobada = _cumple_criterios(ultima, ej)

    return {
        "sesiones": docs,
        "total_sesiones": len(docs),
        "minutos_hoy": round(minutos_hoy, 1),
        "racha": racha,
        "practico_hoy": hoy_local in dias_practica,
        "ultima_sesion": ultima,
        "ultima_aprobada": ultima_aprobada,
        "hoy_local": hoy_local,
    }


def rendimiento_reciente_habilidad(sesiones_docs: list, habilidad: str, n: int) -> float | None:
    """Promedio de rendimiento de los últimos N intentos de una habilidad.

    Considera las sesiones cuyo ejercicio tiene esa habilidad como principal.
    Devuelve None si no hay intentos (sin datos: no se ajusta dificultad).
    """
    relevantes = [
        d for d in sesiones_docs
        if ejercicios_dominio.obtener_ejercicio(
            d.get("ejercicio", "practica_general")
        )["habilidad"] == habilidad
    ]
    if not relevantes:
        return None
    ultimos = relevantes[-n:]
    return sum(_rendimiento(d) for d in ultimos) / len(ultimos)


# --------------------------------------------------------------------------
# Selección de habilidad débil
# --------------------------------------------------------------------------

def _dias_sin_practica(hab: dict, hoy_local, offset_min: int) -> int:
    fl = _fecha_local(hab.get("ultima_practica"), offset_min)
    if fl is None:
        return cfg.DIAS_SATURACION_ESPACIADO
    return max(0, (hoy_local - fl).days)


def seleccionar_habilidad(doc_habilidades: dict, paso_actual: dict | None,
                          hoy_local, offset_min: int) -> tuple[str, dict, float]:
    """Habilidad con mayor puntaje de necesidad. Devuelve (slug, señales, puntaje)."""
    habs_paso = set()
    if paso_actual is not None:
        habs_paso = {paso_actual["habilidad"]} | {
            ejercicios_dominio.obtener_ejercicio(e)["habilidad"]
            for e in paso_actual.get("ejercicios", [])
        }

    mejor = None
    for slug in habilidades_dominio.HABILIDADES:
        hab = doc_habilidades["habilidades"][slug]
        nivel = int(hab.get("nivel", 0))
        confianza = float(hab.get("confianza", 0))
        dias = _dias_sin_practica(hab, hoy_local, offset_min)
        en_paso = slug in habs_paso

        puntaje = (
            cfg.W_NIVEL_BAJO * (cfg.NIVEL_MAX - nivel) / cfg.NIVEL_MAX
            + cfg.W_CONFIANZA_BAJA * (1.0 - confianza)
            + cfg.W_DIAS_SIN_PRACTICA * min(dias / cfg.DIAS_SATURACION_ESPACIADO, 1.0)
            + (cfg.W_PASO_ACTUAL if en_paso else 0.0)
        )
        senales = {
            "nivel": nivel, "confianza": round(confianza, 3),
            "dias_sin_practica": dias, "en_paso_actual": en_paso,
        }
        if mejor is None or puntaje > mejor[2]:
            mejor = (slug, senales, puntaje)
    return mejor


# --------------------------------------------------------------------------
# Decisión principal
# --------------------------------------------------------------------------

def _dificultad_objetivo(nivel: int) -> int:
    return max(1, min(5, nivel // 2 + 1))


def _celebracion(user_id: str, senales: dict, hoy_local, offset_min: int) -> dict | None:
    """Detecta un motivo de felicitación (no reemplaza la recomendación)."""
    from database import habilidad_eventos

    # ¿Subió de nivel alguna habilidad hoy?
    for ev in habilidad_eventos.find({"usuario": user_id, "subio_nivel": True}):
        if _fecha_local(ev.get("fecha"), offset_min) == hoy_local:
            nombre = habilidades_dominio.NOMBRES.get(ev["habilidad"], ev["habilidad"])
            return {
                "tipo": "felicitar",
                "titulo": "¡Subiste de nivel!",
                "mensaje": f"Alcanzaste el nivel {ev['nivel_resultante']} en {nombre}. ¡Excelente!",
            }

    # ¿Racha en hito (7, 14, ...) y practicó hoy?
    if senales["practico_hoy"] and senales["racha"] > 0 and senales["racha"] % cfg.RACHA_HITO_DIAS == 0:
        return {
            "tipo": "felicitar",
            "titulo": f"¡{senales['racha']} días de racha!",
            "mensaje": "Tu constancia es la clave del progreso. ¡Sigue así!",
        }

    # ¿Cumplió la meta diaria hoy?
    if senales["minutos_hoy"] >= cfg.META_DIARIA_MIN:
        return {
            "tipo": "felicitar",
            "titulo": "¡Objetivo del día cumplido!",
            "mensaje": f"Practicaste {int(senales['minutos_hoy'])} min hoy. Meta lograda. 🎯",
        }
    return None


def _consejo_personalizado(slug_debil: str, senales_debil: dict, senales: dict) -> str:
    """Consejo determinístico de Wilfredo basado en datos reales del usuario."""
    nombre = habilidades_dominio.NOMBRES[slug_debil]
    if senales["total_sesiones"] == 0:
        return ("Empieza con calma: toca despacio y prioriza que cada nota suene "
                "limpia antes que la velocidad. 🎸")
    if senales_debil["dias_sin_practica"] >= cfg.DIAS_SATURACION_ESPACIADO:
        return (f"Hace días que no trabajas {nombre}. Retomarla hoy, aunque sea "
                f"5 minutos, evita que pierdas lo avanzado. 🔁")
    if senales_debil["confianza"] < 0.4:
        return (f"Tu {nombre} aún es inestable. Repite el ejercicio a velocidad baja "
                f"y sube el tempo solo cuando salga sin errores. 🐢")
    return (f"Vas bien. Para mejorar tu {nombre}, mantén el metrónomo y busca "
            f"constancia en cada repetición. 💪")


def decidir(user_id: str, offset_min: int = 0, persistir: bool = True) -> dict | None:
    """Decisión completa del motor para un usuario. None si el usuario no existe."""
    doc_hab = habilidades_dominio.obtener_habilidades(user_id)
    if doc_hab is None:
        return None

    senales = recopilar_senales(user_id, offset_min)
    camino = camino_dominio.obtener_camino(user_id)
    paso_actual = camino_dominio.paso_por_id(camino["paso_actual"]) if camino else None
    hoy_local = senales["hoy_local"]

    slug_debil, senales_debil, puntaje = seleccionar_habilidad(
        doc_hab, paso_actual, hoy_local, offset_min
    )
    celebracion = _celebracion(user_id, senales, hoy_local, offset_min)

    # --- Regla 1: descanso ---
    if senales["minutos_hoy"] >= cfg.META_DIARIA_MIN * cfg.FACTOR_DESCANSO:
        decision = {
            "tipo": "descanso",
            "habilidad": None,
            "ejercicio_id": None,
            "dificultad": None,
            "duracion_min": None,
            "razon": (f"Ya practicaste {int(senales['minutos_hoy'])} min hoy, el doble "
                      f"de tu meta. Descansar consolida lo aprendido. 🌙"),
            "senales": {"minutos_hoy": senales["minutos_hoy"], "meta": cfg.META_DIARIA_MIN},
        }
        return _finalizar(user_id, decision, celebracion, camino, senales, persistir)

    # --- Regla 3: repetir si la última sesión no se aprobó ---
    if (senales["ultima_aprobada"] is False and senales["ultima_sesion"] is not None):
        ej_id = senales["ultima_sesion"].get("ejercicio", "practica_general")
        ej = ejercicios_dominio.obtener_ejercicio(ej_id)
        decision = {
            "tipo": "repetir",
            "habilidad": ej["habilidad"],
            "ejercicio_id": ej["id"],
            "dificultad": ej["dificultad"],
            "duracion_min": ej["duracion_min"],
            "razon": (f"Tu última sesión de {ej['nombre']} no alcanzó los criterios. "
                      f"Repetirla a la misma dificultad afianza la técnica. 🔁"),
            "senales": {"ultima_aprobada": False},
        }
        return _finalizar(user_id, decision, celebracion, camino, senales, persistir)

    # --- Reglas 4/5: continuidad con ajuste de dificultad ---
    # Si la última sesión fue aprobada y la habilidad recién trabajada muestra
    # una señal clara (muy floja o ya dominada), el motor MANTIENE esa
    # habilidad ajustando la dificultad. Da continuidad tipo Duolingo y hace
    # que subir/bajar dificultad sean decisiones reales. Sin señal clara,
    # cae al selector de habilidad débil (variedad).
    if senales["ultima_sesion"] is not None:
        ej_ult = ejercicios_dominio.obtener_ejercicio(
            senales["ultima_sesion"].get("ejercicio", "practica_general")
        )
        slug_ult = ej_ult["habilidad"]
        hab_ult = doc_hab["habilidades"][slug_ult]
        nivel_ult = int(hab_ult.get("nivel", 0))
        conf_ult = float(hab_ult.get("confianza", 0))
        rend_ult = rendimiento_reciente_habilidad(
            senales["sesiones"], slug_ult, cfg.N_INTENTOS_TENDENCIA
        )
        nombre_ult = habilidades_dominio.NOMBRES[slug_ult]

        if rend_ult is not None and rend_ult < cfg.UMBRAL_BAJAR_DIFICULTAD and nivel_ult < cfg.NIVEL_MAX:
            dif = max(1, _dificultad_objetivo(nivel_ult) - 1)
            ejercicio = ejercicios_dominio.ejercicio_para_habilidad(slug_ult, dif)
            decision = {
                "tipo": "bajar_dificultad", "habilidad": slug_ult,
                "ejercicio_id": ejercicio["id"], "dificultad": dif,
                "duracion_min": ejercicio["duracion_min"],
                "razon": (f"Tus últimos intentos de {nombre_ult} promediaron "
                          f"{int(rend_ult * 100)}%. Bajamos la dificultad para afianzar "
                          f"la base antes de avanzar. 🐢"),
                "senales": {"habilidad": slug_ult, "rendimiento_reciente": round(rend_ult, 3)},
            }
            return _finalizar(user_id, decision, celebracion, camino, senales, persistir)

        if (rend_ult is not None and rend_ult >= cfg.UMBRAL_SUBIR_DIFICULTAD
                and conf_ult >= cfg.CONFIANZA_MIN_PARA_SUBIR and nivel_ult < cfg.NIVEL_MAX):
            dif = min(5, _dificultad_objetivo(nivel_ult) + 1)
            ejercicio = ejercicios_dominio.ejercicio_para_habilidad(slug_ult, dif)
            decision = {
                "tipo": "subir_dificultad", "habilidad": slug_ult,
                "ejercicio_id": ejercicio["id"], "dificultad": dif,
                "duracion_min": ejercicio["duracion_min"],
                "razon": (f"Dominas {nombre_ult} con {int(rend_ult * 100)}% de rendimiento. "
                          f"Subimos la dificultad para seguir progresando. 🚀"),
                "senales": {"habilidad": slug_ult, "rendimiento_reciente": round(rend_ult, 3),
                            "confianza": round(conf_ult, 3)},
            }
            return _finalizar(user_id, decision, celebracion, camino, senales, persistir)

    # --- Regla 6: practicar la habilidad débil (variedad / repetición espaciada) ---
    nivel_debil = senales_debil["nivel"]
    dificultad_obj = _dificultad_objetivo(nivel_debil)
    tipo = "practicar"
    razon_ajuste = ""

    ejercicio = ejercicios_dominio.ejercicio_para_habilidad(slug_debil, dificultad_obj)
    nombre_hab = habilidades_dominio.NOMBRES[slug_debil]

    # Razón principal según por qué se eligió la habilidad.
    if senales["total_sesiones"] == 0:
        razon_base = (f"Empieza tu camino por {nombre_hab.lower()}: es el primer paso "
                      f"para construir una base sólida.")
    elif senales_debil["en_paso_actual"]:
        razon_base = (f"{nombre_hab} es la habilidad de tu paso actual "
                      f"«{paso_actual['nombre']}» y la que más te conviene reforzar ahora.")
    elif senales_debil["dias_sin_practica"] >= cfg.DIAS_SATURACION_ESPACIADO:
        razon_base = (f"Hace {senales_debil['dias_sin_practica']} días que no practicas "
                      f"{nombre_hab.lower()} y tu confianza bajó. Toca recuperarla.")
    else:
        razon_base = (f"{nombre_hab} es tu habilidad más floja ahora mismo "
                      f"(nivel {nivel_debil}). Trabajarla sube tu nivel general.")

    decision = {
        "tipo": tipo,
        "habilidad": slug_debil,
        "ejercicio_id": ejercicio["id"],
        "dificultad": dificultad_obj,
        "duracion_min": ejercicio["duracion_min"],
        "razon": razon_base + razon_ajuste,
        "senales": {**senales_debil, "puntaje": round(puntaje, 3)},
    }
    return _finalizar(user_id, decision, celebracion, camino, senales, persistir)


def _finalizar(user_id, decision, celebracion, camino, senales, persistir) -> dict:
    """Empaqueta la decisión, la persiste (auditoría) y la devuelve."""
    ejercicio = (
        ejercicios_dominio.obtener_ejercicio(decision["ejercicio_id"])
        if decision.get("ejercicio_id") else None
    )
    resultado = {
        "usuario": user_id,
        "recomendacion": decision,
        "ejercicio": ejercicio,
        "celebracion": celebracion,
        "consejo": None,  # lo completa el llamador con contexto de habilidad débil
        "paso_actual": camino["paso_actual"] if camino else None,
    }
    if persistir:
        recomendaciones.insert_one({
            "usuario": user_id,
            "fecha": datetime.now(timezone.utc).isoformat(),
            "tipo": decision["tipo"],
            "habilidad": decision.get("habilidad"),
            "ejercicio_id": decision.get("ejercicio_id"),
            "dificultad": decision.get("dificultad"),
            "duracion_min": decision.get("duracion_min"),
            "razon": decision["razon"],
            "senales": decision.get("senales", {}),
            "consumida": False,
        })
    return resultado
