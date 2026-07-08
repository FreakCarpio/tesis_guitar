"""
Sistema de Habilidades (P1) - dominio.

Cada usuario tiene 12 habilidades independientes, persistidas en MongoDB:
- colección `habilidades`: un documento por usuario con el estado actual
  (nivel 0-10, progreso 0-1 hacia el siguiente nivel, confianza 0-1,
  intentos, fecha de última práctica)
- colección `habilidad_eventos`: historial append-only de cada cambio
  (el "por qué" de cada movimiento, auditable)

La confianza decae con la inactividad. El decaimiento es LAZY e idempotente:
se calcula al leer como función pura de `ultima_practica`, y solo se
persiste un valor nuevo cuando el usuario practica.
"""

from datetime import datetime, timezone

from database import habilidades, habilidad_eventos, usuarios
from ia import motor_config as cfg

# Catálogo fijo de habilidades (el orden es el orden de presentación).
HABILIDADES = [
    "afinacion",
    "ritmo",
    "precision",
    "consistencia",
    "cambios_acordes",
    "acordes_abiertos",
    "acordes_cejilla",
    "arpegios",
    "fingerstyle",
    "escalas",
    "lectura",
    "velocidad",
]

NOMBRES = {
    "afinacion": "Afinación",
    "ritmo": "Ritmo",
    "precision": "Precisión",
    "consistencia": "Consistencia",
    "cambios_acordes": "Cambios de acordes",
    "acordes_abiertos": "Acordes abiertos",
    "acordes_cejilla": "Acordes con cejilla",
    "arpegios": "Arpegios",
    "fingerstyle": "Fingerstyle",
    "escalas": "Escalas",
    "lectura": "Lectura",
    "velocidad": "Velocidad",
}

# Habilidades transversales: se entrenan (un poco) en TODA práctica,
# directamente desde las métricas de la sesión.
TRANSVERSALES = ("precision", "consistencia")

# Niveles semilla según la experiencia declarada en el onboarding.
# La confianza arranca baja: es nivel declarado, no demostrado; el motor
# lo valida (o corrige) con las primeras prácticas reales.
SEMILLAS_EXPERIENCIA = {
    "nunca": {},
    "principiante": {"afinacion": 1, "ritmo": 1, "acordes_abiertos": 1},
    "intermedio": {
        "afinacion": 3, "ritmo": 2, "precision": 2, "consistencia": 2,
        "acordes_abiertos": 3, "cambios_acordes": 2, "escalas": 1,
    },
    "avanzado": {
        "afinacion": 4, "ritmo": 4, "precision": 3, "consistencia": 3,
        "acordes_abiertos": 4, "cambios_acordes": 4, "acordes_cejilla": 3,
        "arpegios": 3, "fingerstyle": 2, "escalas": 3, "velocidad": 2,
    },
}


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def confianza_actual(hab: dict, ahora: datetime | None = None) -> float:
    """Confianza con decaimiento por inactividad aplicado (función pura).

    No escribe nada: idempotente por diseño. La confianza persistida es la
    del momento de la última práctica; aquí se descuenta el decaimiento
    proporcional a los días transcurridos desde entonces.
    """
    confianza = float(hab.get("confianza", 0) or 0)
    ultima = hab.get("ultima_practica")
    if not ultima:
        return round(confianza, 4)
    try:
        fecha = datetime.fromisoformat(str(ultima))
    except ValueError:
        return round(confianza, 4)
    ahora = ahora or datetime.now(timezone.utc)
    dias = max(0, (ahora - fecha).days)
    return round(max(0.0, confianza - cfg.DECAIMIENTO_CONFIANZA_DIA * dias), 4)


def _habilidad_inicial(nivel: int) -> dict:
    return {
        "nivel": nivel,
        "progreso": 0.0,
        "confianza": cfg.CONFIANZA_INICIAL_SEMILLA if nivel > 0 else 0.0,
        "intentos": 0,
        "ultima_practica": None,
    }


def inicializar_habilidades(user_id: str, experiencia: str | None) -> dict:
    """Crea el documento de habilidades del usuario si no existe.

    Los niveles se siembran desde la experiencia del onboarding; cada
    habilidad sembrada deja un evento `inicializacion` en el historial.
    """
    doc = habilidades.find_one({"usuario": user_id})
    if doc is not None:
        return doc

    semillas = SEMILLAS_EXPERIENCIA.get((experiencia or "").lower(), {})
    ahora = _ahora_iso()
    habs = {h: _habilidad_inicial(semillas.get(h, 0)) for h in HABILIDADES}

    doc = {"usuario": user_id, "habilidades": habs, "actualizado": ahora}
    habilidades.insert_one(doc)

    eventos = [
        {
            "usuario": user_id,
            "habilidad": h,
            "sesion_id": None,
            "fecha": ahora,
            "delta_progreso": 0.0,
            "nivel_resultante": habs[h]["nivel"],
            "progreso_resultante": 0.0,
            "confianza_resultante": habs[h]["confianza"],
            "motivo": "inicializacion",
            "detalle": f"Nivel sembrado desde experiencia declarada: {experiencia}",
        }
        for h in HABILIDADES
        if habs[h]["nivel"] > 0
    ]
    if eventos:
        habilidad_eventos.insert_many(eventos)
    return doc


def obtener_habilidades(user_id: str) -> dict | None:
    """Devuelve el estado de habilidades del usuario (con decaimiento aplicado).

    Inicializa lazy el documento si no existe (usando la experiencia del
    usuario). Devuelve None si el usuario no existe.
    """
    usuario = usuarios.find_one({"user_id": user_id})
    if usuario is None:
        return None
    doc = habilidades.find_one({"usuario": user_id})
    if doc is None:
        doc = inicializar_habilidades(user_id, usuario.get("experiencia"))

    ahora = datetime.now(timezone.utc)
    for hab in doc["habilidades"].values():
        hab["confianza"] = confianza_actual(hab, ahora)
    return doc


def valor_habilidad(hab: dict) -> float:
    """Valor escalar 0..10 de una habilidad (nivel + progreso parcial)."""
    return float(hab.get("nivel", 0)) + float(hab.get("progreso", 0))


def rendimiento_sesion(precision: float, consistencia: float) -> float:
    """Rendimiento 0..1 de una sesión según los pesos configurados."""
    return cfg.PESO_PRECISION * precision + cfg.PESO_CONSISTENCIA * consistencia


def _aplicar_delta(hab: dict, delta: float) -> bool:
    """Aplica delta de progreso a una habilidad. Devuelve True si subió de nivel."""
    subio = False
    hab["progreso"] = float(hab.get("progreso", 0)) + delta
    while hab["progreso"] >= 1.0 and hab["nivel"] < cfg.NIVEL_MAX:
        hab["progreso"] -= 1.0
        hab["nivel"] += 1
        subio = True
    if hab["nivel"] >= cfg.NIVEL_MAX:
        hab["nivel"] = cfg.NIVEL_MAX
        hab["progreso"] = min(hab["progreso"], 1.0)
    hab["progreso"] = round(min(hab["progreso"], 1.0), 4)
    return subio


def aplicar_practica(
    user_id: str,
    habilidad_principal: str,
    habilidades_secundarias: list[str],
    precision: float,
    consistencia: float,
    dificultad: int,
    aprobado: bool,
    sesion_id: str | None = None,
) -> list[dict]:
    """Actualiza las habilidades del usuario tras una práctica real.

    - Habilidad principal: delta completo.
    - Secundarias: fracción del delta.
    - Transversales (precision/consistencia): delta plano desde su métrica,
      salvo que ya sean principal/secundaria de este ejercicio.

    Persiste el documento, registra eventos en el historial y devuelve la
    lista de actualizaciones (para la respuesta de la API).
    """
    usuario = usuarios.find_one({"user_id": user_id})
    doc = habilidades.find_one({"usuario": user_id})
    if doc is None:
        doc = inicializar_habilidades(
            user_id, (usuario or {}).get("experiencia")
        )

    ahora_dt = datetime.now(timezone.utc)
    ahora = ahora_dt.isoformat()
    rendimiento = rendimiento_sesion(precision, consistencia)
    base = cfg.DELTA_BASE_APROBADO if aprobado else cfg.DELTA_BASE_FALLIDO
    delta_principal = base * cfg.factor_dificultad(dificultad) * rendimiento
    motivo = "practica_aprobada" if aprobado else "practica_fallida"

    # habilidad -> delta a aplicar
    deltas: dict[str, float] = {}
    if habilidad_principal in HABILIDADES:
        deltas[habilidad_principal] = delta_principal
    for sec in habilidades_secundarias:
        if sec in HABILIDADES and sec not in deltas:
            deltas[sec] = delta_principal * cfg.FRACCION_SECUNDARIA
    if "precision" not in deltas:
        deltas["precision"] = cfg.DELTA_TRANSVERSAL * precision
    if "consistencia" not in deltas:
        deltas["consistencia"] = cfg.DELTA_TRANSVERSAL * consistencia

    actualizaciones = []
    eventos = []
    for slug, delta in deltas.items():
        hab = doc["habilidades"].get(slug)
        if hab is None:
            continue
        delta = round(delta, 4)
        # Decaimiento pendiente se consolida antes del incremento por práctica.
        confianza_previa = confianza_actual(hab, ahora_dt)
        subio_nivel = _aplicar_delta(hab, delta)
        hab["confianza"] = round(min(1.0, confianza_previa + cfg.CONFIANZA_POR_PRACTICA), 4)
        hab["intentos"] = int(hab.get("intentos", 0)) + 1
        hab["ultima_practica"] = ahora

        actualizaciones.append({
            "habilidad": slug,
            "nombre": NOMBRES[slug],
            "delta": delta,
            "nivel": hab["nivel"],
            "progreso": hab["progreso"],
            "confianza": hab["confianza"],
            "subio_nivel": subio_nivel,
        })
        eventos.append({
            "usuario": user_id,
            "habilidad": slug,
            "sesion_id": str(sesion_id) if sesion_id else None,
            "fecha": ahora,
            "delta_progreso": delta,
            "nivel_resultante": hab["nivel"],
            "progreso_resultante": hab["progreso"],
            "confianza_resultante": hab["confianza"],
            "subio_nivel": subio_nivel,
            "motivo": motivo,
            "detalle": (
                f"precision={round(precision, 3)} consistencia={round(consistencia, 3)} "
                f"dificultad={dificultad} rendimiento={round(rendimiento, 3)}"
            ),
        })

    habilidades.update_one(
        {"usuario": user_id},
        {"$set": {"habilidades": doc["habilidades"], "actualizado": ahora}},
    )
    if eventos:
        habilidad_eventos.insert_many(eventos)
    return actualizaciones


def historial_habilidad(user_id: str, habilidad: str, limite: int = 30) -> list[dict]:
    """Últimos eventos de una habilidad (para gráficos y auditoría)."""
    cursor = (
        habilidad_eventos.find(
            {"usuario": user_id, "habilidad": habilidad}, {"_id": 0}
        )
        .sort("fecha", -1)
        .limit(limite)
    )
    return list(cursor)
