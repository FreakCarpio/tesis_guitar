"""
Progress Intelligence (MC2) - Detección de evolución, estancamiento,
recaídas y logros.

Se ejecuta tras cada práctica (hook best-effort en /practica). Cada
detección se persiste en la colección `hitos` con una `clave` única que
evita duplicados (upsert): el mismo logro nunca se celebra dos veces.

Tipos de hito:
- logro         : primera práctica, primeras 3 estrellas, racha 7/14/...,
                  canción dominada, subida de nivel de habilidad, XP hitos
- evolucion     : mejora sostenida en una habilidad (ventanas de 3 intentos)
- estancamiento : repite un ejercicio sin mejorar su mejor marca
- recaida       : regreso tras una pausa larga (señal de refuerzo, no castigo)

Todo determinístico y con evidencia mínima: nada se detecta con menos de
las muestras requeridas.
"""

from datetime import datetime, timedelta, timezone

from database import habilidad_eventos, hitos, intentos_ejercicio
from domain import ejercicios as ejercicios_dominio
from domain import habilidades as habilidades_dominio

# Umbrales (mismo espíritu de motor_config: constantes visibles y auditables).
PAUSA_RECAIDA_DIAS = 7
ESTANCAMIENTO_MIN_INTENTOS = 5
ESTANCAMIENTO_VENTANA_DIAS = 14
EVOLUCION_MIN_INTENTOS = 6          # 3 recientes vs 3 previos
EVOLUCION_DELTA = 8.0               # puntos de mejora entre ventanas
XP_HITOS = [100, 250, 500, 1000, 2500, 5000]
RACHA_HITO = 7


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _fecha(iso) -> datetime | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _semana(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _registrar(user_id: str, clave: str, tipo: str, titulo: str,
               detalle: str, datos: dict | None = None) -> dict | None:
    """Inserta el hito si su clave no existe. Devuelve el hito si es nuevo."""
    existente = hitos.find_one({"usuario": user_id, "clave": clave})
    if existente is not None:
        return None
    doc = {
        "usuario": user_id,
        "clave": clave,
        "tipo": tipo,
        "titulo": titulo,
        "detalle": detalle,
        "datos": datos or {},
        "fecha": _ahora().isoformat(),
    }
    hitos.insert_one(doc)
    doc.pop("_id", None)
    return doc


def _skills_de_intento(intento: dict) -> set[str]:
    pasos = intento.get("pasos") or []
    if pasos:
        return {p.get("skill") for p in pasos if p.get("skill")}
    ej = ejercicios_dominio.obtener_ejercicio(intento.get("ejercicio", "practica_general"))
    return {ej["habilidad"]}


def analizar_tras_practica(user_id: str, racha: int = 0, xp_total: int = 0) -> list[dict]:
    """Corre todas las detecciones tras una práctica. Devuelve hitos NUEVOS."""
    intentos = list(
        intentos_ejercicio.find({"usuario": user_id}, {"_id": 0})
        .sort("fecha", -1)
        .limit(100)
    )
    if not intentos:
        return []

    nuevos: list[dict] = []
    ultimo = intentos[0]
    ahora = _ahora()

    # ---------- LOGROS ----------
    if len(intentos) == 1:
        h = _registrar(user_id, "primera_practica", "logro",
                       "¡Primera práctica!",
                       "Completaste tu primera sesión en FretMind. El viaje empezó. 🎸")
        if h: nuevos.append(h)

    if ultimo.get("estrellas") == 3:
        h = _registrar(user_id, "tres_estrellas", "logro",
                       "¡Primeras 3 estrellas!",
                       f"Sesión perfecta en «{ultimo['ejercicio']}» con "
                       f"{int(ultimo.get('puntuacion') or 0)}/100. ⭐⭐⭐")
        if h: nuevos.append(h)

    if racha >= RACHA_HITO and racha % RACHA_HITO == 0:
        h = _registrar(user_id, f"racha_{racha}", "logro",
                       f"¡{racha} días de racha!",
                       "La constancia es la habilidad maestra. 🔥",
                       {"racha": racha})
        if h: nuevos.append(h)

    cid = ultimo.get("cancion_id")
    if cid is not None and (
        ultimo.get("estrellas") == 3 or (ultimo.get("puntuacion") or 0) >= 85
    ):
        h = _registrar(user_id, f"cancion_dominada_{cid}", "logro",
                       "¡Canción dominada!",
                       "Marcaste tu mejor versión de esta canción. 🎶",
                       {"cancion_id": cid})
        if h: nuevos.append(h)

    for umbral in XP_HITOS:
        if xp_total >= umbral:
            h = _registrar(user_id, f"xp_{umbral}", "logro",
                           f"¡{umbral} XP acumulados!",
                           "Cada punto es evidencia de trabajo real. 💪",
                           {"xp": umbral})
            if h: nuevos.append(h)

    # Subidas de nivel de habilidad (desde el historial de eventos P1).
    for ev in habilidad_eventos.find(
        {"usuario": user_id, "subio_nivel": True}
    ).sort("fecha", -1).limit(10):
        slug = ev["habilidad"]
        nivel = ev["nivel_resultante"]
        nombre = habilidades_dominio.NOMBRES.get(slug, slug)
        h = _registrar(user_id, f"nivel_{slug}_{nivel}", "logro",
                       f"{nombre} subió a nivel {nivel}",
                       f"Tu {nombre} alcanzó el nivel {nivel}. 📈",
                       {"habilidad": slug, "nivel": nivel})
        if h: nuevos.append(h)

    # ---------- RECAÍDA (regreso tras pausa) ----------
    if len(intentos) >= 2:
        f_ultimo = _fecha(ultimo.get("fecha"))
        f_previo = _fecha(intentos[1].get("fecha"))
        if f_ultimo and f_previo:
            pausa = (f_ultimo - f_previo).days
            if pausa >= PAUSA_RECAIDA_DIAS:
                h = _registrar(user_id, f"regreso_{f_ultimo.date().isoformat()}",
                               "recaida", "¡De vuelta!",
                               f"Volviste tras {pausa} días. Lo difícil era regresar: "
                               f"hoy toca refuerzo suave, no récords. 🌱",
                               {"dias_pausa": pausa})
                if h: nuevos.append(h)

    # ---------- EVOLUCIÓN y ESTANCAMIENTO ----------
    semana = _semana(ahora)

    # Evolución por habilidad: 3 intentos recientes vs 3 previos que la tocan.
    for slug in _skills_de_intento(ultimo):
        relevantes = [
            i for i in intentos
            if i.get("puntuacion") is not None and slug in _skills_de_intento(i)
        ]
        if len(relevantes) >= EVOLUCION_MIN_INTENTOS:
            recientes = sum(i["puntuacion"] for i in relevantes[:3]) / 3
            previos = sum(i["puntuacion"] for i in relevantes[3:6]) / 3
            if recientes >= previos + EVOLUCION_DELTA:
                nombre = habilidades_dominio.NOMBRES.get(slug, slug)
                h = _registrar(user_id, f"evolucion_{slug}_{semana}", "evolucion",
                               f"{nombre} en clara mejora",
                               f"Tus últimos intentos suben de {int(previos)} a "
                               f"{int(recientes)} de media. 📈",
                               {"habilidad": slug, "antes": round(previos, 1),
                                "ahora": round(recientes, 1)})
                if h: nuevos.append(h)

    # Estancamiento por ejercicio: N intentos recientes sin superar la mejor marca.
    ejercicio = ultimo.get("ejercicio")
    ventana = ahora - timedelta(days=ESTANCAMIENTO_VENTANA_DIAS)
    mismos = [
        i for i in intentos
        if i.get("ejercicio") == ejercicio
        and i.get("puntuacion") is not None
        and (_fecha(i.get("fecha")) or ahora) >= ventana
    ]
    if len(mismos) >= ESTANCAMIENTO_MIN_INTENTOS:
        recientes = [i["puntuacion"] for i in mismos[:2]]
        previos = [i["puntuacion"] for i in mismos[2:]]
        if previos and max(recientes) <= max(previos):
            h = _registrar(user_id, f"estancamiento_{ejercicio}_{semana}",
                           "estancamiento", f"Meseta en {ejercicio}",
                           "Varias sesiones sin superar tu marca: cambiemos de "
                           "estrategia (más lento, otra variante o descanso). 🔄",
                           {"ejercicio": ejercicio, "intentos": len(mismos),
                            "mejor": max(previos)})
            if h: nuevos.append(h)

    return nuevos


def obtener_hitos(user_id: str, limite: int = 20) -> list[dict]:
    """Hitos del usuario, más recientes primero."""
    limite = max(1, min(100, limite))
    return list(
        hitos.find({"usuario": user_id}, {"_id": 0}).sort("fecha", -1).limit(limite)
    )


def estado_aprendizaje(user_id: str) -> dict:
    """Estado resumido para el perfil y el motor: qué está pasando ahora."""
    ahora = _ahora()
    hace_7d = (ahora - timedelta(days=7)).isoformat()
    recientes = list(
        hitos.find({"usuario": user_id, "fecha": {"$gte": hace_7d}}, {"_id": 0})
    )
    return {
        "en_evolucion": sorted({
            h["datos"].get("habilidad") for h in recientes
            if h["tipo"] == "evolucion" and h["datos"].get("habilidad")
        }),
        "estancado_en": sorted({
            h["datos"].get("ejercicio") for h in recientes
            if h["tipo"] == "estancamiento" and h["datos"].get("ejercicio")
        }),
        "regreso_reciente": any(h["tipo"] == "recaida" for h in recientes),
        "logros_7d": sum(1 for h in recientes if h["tipo"] == "logro"),
    }
