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
        # Duración 10 s (no 60): la práctica en vivo cierra cada paso al
        # validar la cuerda (6 pasos ≈ 15-30 s reales); con 60 s el ejercicio
        # era imposible de aprobar. El filtro de calidad son las métricas.
        "criterios": _crit_sostenido(0.65, 0.85, 10),
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

# ==========================================================================
# PASOS DE PRÁCTICA GUIADA EN VIVO (estilo Yousician)
#
# Tipos de paso soportados (identificadores estables para el cliente y la
# futura IA adaptativa; el usuario los definió explícitamente en inglés):
#   - Validables por pitch monofónico (YIN): NOTE, SEQUENCE, STRING, SCALE,
#     ARPEGGIO, MELODY  -> `objetivos` = notas con octava en orden.
#   - Validables por actividad/ataques (YIN no detecta polifonía): CHORD,
#     CHORD_CHANGE, RHYTHM, SONG_FRAGMENT, CUSTOM -> `objetivos` = etiquetas
#     (acordes/patrón) y la validación en vivo es por energía y pulsos.
#
# Cada paso lleva difficulty (1-5), xp y skill: hoy con valores por defecto
# razonables, mañana insumo directo del motor adaptativo (sin rediseño).
# ==========================================================================

TIPOS_PASO = {
    "NOTE", "SEQUENCE", "RHYTHM", "CHORD", "CHORD_CHANGE", "STRING",
    "SCALE", "ARPEGGIO", "MELODY", "SONG_FRAGMENT", "CUSTOM",
}

# Tipos cuya validación en vivo es por detección de tono (monofónico).
TIPOS_POR_PITCH = {"NOTE", "SEQUENCE", "STRING", "SCALE", "ARPEGGIO", "MELODY"}


def _paso(titulo, instruccion, tipo, objetivos, duracion_seg=30,
          bpm=None, difficulty=None, xp=None, skill=None):
    """Builder de paso con defaults: difficulty/xp/skill se completan al
    fusionar con su ejercicio (difficulty=la del ejercicio, xp=10·difficulty,
    skill=habilidad principal del ejercicio)."""
    assert tipo in TIPOS_PASO, f"tipo de paso inválido: {tipo}"
    return {
        "titulo": titulo,
        "instruccion": instruccion,
        "tipo": tipo,
        "objetivos": objetivos,
        "duracion_seg": duracion_seg,
        "bpm": bpm,
        "difficulty": difficulty,
        "xp": xp,
        "skill": skill,
    }


PASOS_POR_EJERCICIO = {
    "afinacion": [
        _paso("Cuerda 6 (Mi grave)", "Toca la 6ª cuerda al aire y mantenla sonando", "STRING", ["E2"], 15),
        _paso("Cuerda 5 (La)", "Toca la 5ª cuerda al aire", "STRING", ["A2"], 15),
        _paso("Cuerda 4 (Re)", "Toca la 4ª cuerda al aire", "STRING", ["D3"], 15),
        _paso("Cuerda 3 (Sol)", "Toca la 3ª cuerda al aire", "STRING", ["G3"], 15),
        _paso("Cuerda 2 (Si)", "Toca la 2ª cuerda al aire", "STRING", ["B3"], 15),
        _paso("Cuerda 1 (Mi agudo)", "Toca la 1ª cuerda al aire", "STRING", ["E4"], 15),
    ],
    "escalas": [
        _paso("Do Mayor: subida", "Toca la escala nota por nota, lenta y limpia",
              "SCALE", ["C3", "D3", "E3", "F3", "G3", "A3", "B3", "C4"], 45, bpm=60),
        _paso("Do Mayor: bajada", "Ahora en sentido inverso, mismo tempo",
              "SCALE", ["C4", "B3", "A3", "G3", "F3", "E3", "D3", "C3"], 45, bpm=60),
        _paso("Pentatónica de La menor", "Posición 1: cada nota debe sonar clara",
              "SCALE", ["A2", "C3", "D3", "E3", "G3", "A3"], 45, bpm=70, difficulty=3),
    ],
    "acordes": [
        _paso("Acorde Am", "Forma Am y rasguea 4 veces, que suene completo", "CHORD", ["Am"], 25),
        _paso("Acorde C", "Cambia a Do Mayor y rasguea 4 veces", "CHORD", ["C"], 25),
        _paso("Acorde G", "Ahora Sol Mayor, cuida la 6ª cuerda", "CHORD", ["G"], 25),
        _paso("Cambio Am → C", "Alterna entre Am y C cada 4 tiempos",
              "CHORD_CHANGE", ["Am", "C"], 40, bpm=60, skill="cambios_acordes"),
    ],
    "cambios_acordes": [
        _paso("Am → C lento", "Cambia entre Am y C sin pausas, aunque sea lento",
              "CHORD_CHANGE", ["Am", "C"], 40, bpm=50),
        _paso("C → G", "El cambio más difícil del inicio: anticipa los dedos",
              "CHORD_CHANGE", ["C", "G"], 40, bpm=50),
        _paso("Am → C → G", "La progresión completa, un compás por acorde",
              "CHORD_CHANGE", ["Am", "C", "G"], 60, bpm=60, difficulty=3),
    ],
    "ritmo": [
        _paso("Pulso en negras", "Rasguea hacia abajo en cada pulso: 1-2-3-4",
              "RHYTHM", ["↓", "↓", "↓", "↓"], 30, bpm=60),
        _paso("Corcheas", "Abajo-arriba constante: 1-y-2-y-3-y-4-y",
              "RHYTHM", ["↓", "↑"], 30, bpm=70, difficulty=3),
    ],
    "rasgueo": [
        _paso("Rasgueo abajo", "Muñeca relajada, rasgueos hacia abajo parejos",
              "RHYTHM", ["↓", "↓", "↓", "↓"], 30, bpm=60),
        _paso("Patrón D-DU-UDU", "El patrón universal: ↓ ↓↑ ↑↓↑",
              "RHYTHM", ["↓", "↓", "↑", "↑", "↓", "↑"], 45, bpm=70, difficulty=3),
    ],
    "arpegios": [
        _paso("Arpegio de Am", "Toca las notas del acorde una por una",
              "ARPEGGIO", ["A2", "E3", "A3", "C4"], 40, bpm=60),
        _paso("Arpegio de C", "Ahora Do Mayor, notas limpias y parejas",
              "ARPEGGIO", ["C3", "E3", "G3", "C4"], 40, bpm=60),
    ],
    "fingerpicking": [
        _paso("p-i-m-a sobre Em", "Pulgar en 6ª, luego índice, medio y anular",
              "ARPEGGIO", ["E2", "G3", "B3", "E4"], 45, bpm=55),
        _paso("Pulgar alternado", "Alterna el pulgar entre 6ª y 4ª cuerda",
              "SEQUENCE", ["E2", "D3", "E2", "D3"], 40, bpm=60, difficulty=4),
    ],
    "cejilla": [
        _paso("Acorde F", "Forma la cejilla en el traste 1: que suenen las 6 cuerdas",
              "CHORD", ["F"], 40),
        _paso("Cambio C → F", "Del acorde abierto a la cejilla sin detenerte",
              "CHORD_CHANGE", ["C", "F"], 45, bpm=50, difficulty=5, skill="cambios_acordes"),
    ],
    "velocidad": [
        _paso("Cromática a 80", "Dedos 1-2-3-4 en trastes consecutivos",
              "SEQUENCE", ["E2", "F2", "F#2", "G2"], 40, bpm=80),
        _paso("Cromática a 100", "Mismo ejercicio, más rápido y sin errores",
              "SEQUENCE", ["E2", "F2", "F#2", "G2"], 40, bpm=100, difficulty=5),
    ],
    "calentamiento": [
        _paso("Cuerdas al aire", "Toca cada cuerda al aire, limpia y sin trastear",
              "SEQUENCE", ["E2", "A2", "D3", "G3", "B3", "E4"], 30),
        _paso("Araña 1-2-3-4", "Un dedo por traste, despacio",
              "SEQUENCE", ["F2", "F#2", "G2", "G#2"], 30, bpm=60),
    ],
    "lectura": [
        _paso("Lectura a primera vista", "Abre la tablatura y toca leyéndola sin memorizar",
              "CUSTOM", ["lectura"], 90),
    ],
    "primera_cancion": [
        _paso("Progresión de la canción", "Toca Am → C → G, un compás por acorde",
              "CHORD_CHANGE", ["Am", "C", "G"], 60, bpm=60),
        _paso("La canción completa", "De inicio a fin sin detenerte, aunque haya errores",
              "SONG_FRAGMENT", ["Am", "C", "G"], 120, bpm=60, difficulty=3),
    ],
    # practica_general: sin pasos (práctica libre pura).
}

# Fusiona pasos en el catálogo completando defaults por ejercicio.
for _e in EJERCICIOS:
    _pasos = PASOS_POR_EJERCICIO.get(_e["id"], [])
    for _i, _p in enumerate(_pasos):
        _p["id"] = f"{_e['id']}_p{_i + 1}"
        if _p["difficulty"] is None:
            _p["difficulty"] = _e["dificultad"]
        if _p["xp"] is None:
            _p["xp"] = 10 * _p["difficulty"]
        if _p["skill"] is None:
            _p["skill"] = _e["habilidad"]
    _e["pasos"] = _pasos

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
