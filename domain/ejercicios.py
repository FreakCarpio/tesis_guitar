"""
Catálogo de Ejercicios (P1) - Prácticas Inteligentes.

El catálogo es CÓDIGO versionado (no una colección Mongo): es diseño
pedagógico, auditable en git, sin migraciones. Mongo guarda solo estado
de usuario.

Cada ejercicio define el contrato de una práctica inteligente:
- objetivo: qué se busca lograr (visible para el usuario)
- habilidad principal + secundarias que entrena
- paso del camino al que pertenece
- dificultad (1-5) y duración sugerida
- criterios de aprobación (evaluados por el backend con las métricas reales)

Los ids de los 6 primeros coinciden con los que la app Android ya envía
en POST /practica (escalas, acordes, fingerpicking, rasgueo, ritmo,
calentamiento). Los nuevos se practican en modo libre hasta que Android
tenga contenido guiado propio.
"""

# --------------------------------------------------------------------------
# Criterios de aprobación CALIBRADOS contra el pipeline de audio real
# (ver tools/calibracion_audio.py). Medición sobre las 6 cuerdas:
#
#   precisión = 1 - |desafinación_cents| / 50   (solo válida en notas sostenidas)
#     · nota afinada (0-10 cents):  precisión 0.75 - 0.97
#     · 20 cents de error:          precisión ~0.56
#     · 30 cents:                   precisión ~0.35
#   consistencia = estabilidad de la frecuencia entre segmentos
#     · nota sostenida afinada:     consistencia ~1.0
#     · pasaje multinota (escala):  consistencia ~0.0  (la frecuencia cambia
#       entre notas por diseño; la métrica NO puntúa musicalidad)
#
# Por eso los umbrales dependen del TIPO de ejercicio:
#  - SOSTENIDO (afinación): precisión y consistencia son plenamente válidas.
#  - MULTINOTA (resto): la consistencia no aplica (se pone en 0) y la precisión
#    de un pasaje bien tocado ronda 0.45; el umbral se fija por debajo. La
#    duración es el criterio principal de "sí practicaste".
#
# LIMITACIÓN CONOCIDA: el analizador no puntúa la corrección de una secuencia
# de notas (qué notas y en qué orden). Puntuar musicalidad requeriría un
# alineamiento nota a nota (DTW) contra la secuencia esperada: fuera de P1.
# --------------------------------------------------------------------------

# Perfil para ejercicios de nota sostenida (afinación).
def _crit_sostenido(precision_min, consistencia_min, dur):
    return {"precision_min": precision_min, "consistencia_min": consistencia_min,
            "duracion_min_seg": dur}

# Perfil para ejercicios multinota: la consistencia no aplica (0.0).
def _crit_multinota(precision_min, dur):
    return {"precision_min": precision_min, "consistencia_min": 0.0,
            "duracion_min_seg": dur}

# Criterios por defecto para ejercicios desconocidos o práctica libre.
CRITERIOS_DEFAULT = _crit_multinota(0.3, 60)

EJERCICIOS = [
    {
        "id": "afinacion",
        "nombre": "Afinación de cuerdas",
        "emoji": "🎵",
        "descripcion": "Afina y verifica las 6 cuerdas al aire",
        "habilidad": "afinacion",
        "secundarias": [],
        "paso": "afinacion",
        "dificultad": 1,
        "duracion_min": 5,
        "objetivo": "Tocar cuerdas al aire afinadas y estables",
        "criterios": _crit_sostenido(0.65, 0.85, 60),
    },
    {
        "id": "acordes",
        "nombre": "Acordes",
        "emoji": "🎸",
        "descripcion": "Abiertos y con cejilla",
        "habilidad": "acordes_abiertos",
        "secundarias": ["cambios_acordes"],
        "paso": "acordes_abiertos",
        "dificultad": 2,
        "duracion_min": 10,
        "objetivo": "Lograr que los acordes abiertos suenen limpios y sin trasteo",
        "criterios": _crit_multinota(0.35, 120),
    },
    {
        "id": "cambios_acordes",
        "nombre": "Cambios de acordes",
        "emoji": "🔁",
        "descripcion": "Transiciones lentas y limpias entre acordes",
        "habilidad": "cambios_acordes",
        "secundarias": ["acordes_abiertos", "ritmo"],
        "paso": "cambios_lentos",
        "dificultad": 2,
        "duracion_min": 10,
        "objetivo": "Cambiar entre Am, C y G sin pausas largas",
        "criterios": _crit_multinota(0.35, 120),
    },
    {
        "id": "ritmo",
        "nombre": "Ritmo",
        "emoji": "🥁",
        "descripcion": "Compás y subdivisión",
        "habilidad": "ritmo",
        "secundarias": ["consistencia"],
        "paso": "ritmo_basico",
        "dificultad": 2,
        "duracion_min": 10,
        "objetivo": "Mantener un pulso constante en 4/4",
        "criterios": _crit_multinota(0.30, 120),
    },
    {
        "id": "rasgueo",
        "nombre": "Rasgueo",
        "emoji": "⚡",
        "descripcion": "Strumming y patrones rítmicos",
        "habilidad": "ritmo",
        "secundarias": ["consistencia", "velocidad"],
        "paso": "ritmo_basico",
        "dificultad": 2,
        "duracion_min": 10,
        "objetivo": "Dominar el patrón D-DU-UDU con muñeca relajada",
        "criterios": _crit_multinota(0.30, 120),
    },
    {
        "id": "primera_cancion",
        "nombre": "Primera canción",
        "emoji": "🎤",
        "descripcion": "Toca una canción sencilla de 3 acordes",
        "habilidad": "cambios_acordes",
        "secundarias": ["ritmo", "consistencia"],
        "paso": "primera_cancion",
        "dificultad": 3,
        "duracion_min": 15,
        "objetivo": "Tocar una progresión Am-C-G completa sin detenerte",
        "criterios": _crit_multinota(0.38, 180),
    },
    {
        "id": "fingerpicking",
        "nombre": "Fingerpicking",
        "emoji": "🤌",
        "descripcion": "Patrones p-i-m-a",
        "habilidad": "fingerstyle",
        "secundarias": ["arpegios", "precision"],
        "paso": "fingerstyle",
        "dificultad": 3,
        "duracion_min": 10,
        "objetivo": "Ejecutar el patrón p-i-m-a de forma fluida",
        "criterios": _crit_multinota(0.38, 120),
    },
    {
        "id": "arpegios",
        "nombre": "Arpegios",
        "emoji": "🌊",
        "descripcion": "Notas del acorde una por una",
        "habilidad": "arpegios",
        "secundarias": ["precision", "consistencia"],
        "paso": "arpegios",
        "dificultad": 3,
        "duracion_min": 10,
        "objetivo": "Arpegiar acordes abiertos con notas limpias y parejas",
        "criterios": _crit_multinota(0.38, 120),
    },
    {
        "id": "cejilla",
        "nombre": "Acordes con cejilla",
        "emoji": "🤏",
        "descripcion": "F, Bm y las formas con barra",
        "habilidad": "acordes_cejilla",
        "secundarias": ["acordes_abiertos", "precision"],
        "paso": "cejillas",
        "dificultad": 4,
        "duracion_min": 10,
        "objetivo": "Lograr que el acorde F suene completo sin cuerdas muertas",
        "criterios": _crit_multinota(0.35, 120),
    },
    {
        "id": "escalas",
        "nombre": "Escalas",
        "emoji": "🎼",
        "descripcion": "Mayor, menor y pentatónica",
        "habilidad": "escalas",
        "secundarias": ["precision", "velocidad"],
        "paso": "escalas",
        "dificultad": 3,
        "duracion_min": 10,
        "objetivo": "Subir y bajar la escala sin errores de digitación",
        "criterios": _crit_multinota(0.38, 120),
    },
    {
        "id": "lectura",
        "nombre": "Lectura de tablatura",
        "emoji": "📖",
        "descripcion": "Toca leyendo tabs sin memorizar",
        "habilidad": "lectura",
        "secundarias": ["precision"],
        "paso": "canciones_completas",
        "dificultad": 3,
        "duracion_min": 10,
        "objetivo": "Tocar un fragmento nuevo leyéndolo a primera vista",
        "criterios": _crit_multinota(0.32, 120),
    },
    {
        "id": "velocidad",
        "nombre": "Velocidad",
        "emoji": "🚀",
        "descripcion": "Ejercicios con metrónomo progresivo",
        "habilidad": "velocidad",
        "secundarias": ["precision", "consistencia"],
        "paso": "canciones_completas",
        "dificultad": 4,
        "duracion_min": 10,
        "objetivo": "Aumentar el tempo manteniendo notas limpias",
        "criterios": _crit_multinota(0.38, 120),
    },
    {
        "id": "calentamiento",
        "nombre": "Calentamiento",
        "emoji": "🔥",
        "descripcion": "Ejercicios de dedos",
        "habilidad": "velocidad",
        "secundarias": ["precision"],
        "paso": None,
        "dificultad": 1,
        "duracion_min": 5,
        "objetivo": "Activar dedos y muñecas antes de practicar",
        "criterios": _crit_multinota(0.28, 60),
    },
    {
        "id": "practica_general",
        "nombre": "Práctica libre",
        "emoji": "🎶",
        "descripcion": "Toca lo que quieras: Wilfredo escucha",
        "habilidad": "precision",
        "secundarias": ["consistencia"],
        "paso": None,
        "dificultad": 1,
        "duracion_min": 10,
        "objetivo": "Práctica libre con evaluación de precisión y consistencia",
        "criterios": CRITERIOS_DEFAULT,
    },
]

_POR_ID = {e["id"]: e for e in EJERCICIOS}
_DEFAULT = _POR_ID["practica_general"]


def obtener_ejercicio(ejercicio_id: str) -> dict:
    """Ejercicio por id; ids desconocidos caen en práctica libre."""
    return _POR_ID.get(ejercicio_id, _DEFAULT)


def ejercicios_por_habilidad(habilidad: str) -> list[dict]:
    """Ejercicios cuya habilidad principal es la dada (orden: dificultad)."""
    return sorted(
        (e for e in EJERCICIOS if e["habilidad"] == habilidad),
        key=lambda e: e["dificultad"],
    )


def ejercicio_para_habilidad(habilidad: str, dificultad_objetivo: int) -> dict:
    """El ejercicio de esa habilidad con dificultad más cercana a la pedida.

    Si la habilidad no tiene ejercicio propio, se entrena con práctica libre.
    """
    candidatos = ejercicios_por_habilidad(habilidad)
    if not candidatos:
        return _DEFAULT
    return min(candidatos, key=lambda e: abs(e["dificultad"] - dificultad_objetivo))
