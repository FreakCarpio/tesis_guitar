"""
Capa conversacional social de RIFF (MC8.5).

Small talk con personaje: saludos, despedidas, agradecimientos, cariño,
halagos, motivación y "¿quién eres?" se responden de forma natural y
variada SIN salirse nunca del rol de profesor de guitarra amigable.

Reglas del personaje (invariantes):
 - RIFF nunca dice "no tengo emociones", "soy una IA", "no puedo sentir".
 - Siempre cálido, motivador y profesional; jamás sarcástico ni cortante.
 - Toda respuesta social termina reconduciendo (suave) hacia la guitarra.

Diseño desacoplado: este módulo solo detecta la intención social y entrega
el texto. Si mañana un LLM real toma la conversación, esta capa puede
seguir resolviendo el small talk barato o retirarse sin tocar el pipeline
(`detectar` deja de llamarse y listo).

La variabilidad usa random.choice con anti-repetición: nunca se repite la
respuesta exacta que RIFF ya dio en los últimos turnos.
"""

import random
import unicodedata


def _norm(texto: str) -> str:
    """minúsculas + sin acentos + solo alfanumérico/espacios."""
    t = unicodedata.normalize("NFD", (texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return "".join(c if c.isalnum() or c.isspace() else " " for c in t)


# Frases/palabras por intención social. Las claves de una sola palabra
# corta se comparan como token exacto (no substring) para evitar falsos
# positivos tipo "ey" dentro de "ley" o "am" dentro de "te amo".
_FRASES: dict[str, list[str]] = {
    "agradecimiento": [
        "gracias", "muchas gracias", "mil gracias", "te lo agradezco",
        "thank you", "thanks", "agradecido", "agradecida", "muy amable",
    ],
    "despedida": [
        "adios", "hasta luego", "hasta manana", "nos vemos", "bye",
        "chau", "chao", "me voy", "ya me voy", "hasta pronto",
        "buenas noches", "me despido",
    ],
    "carino": [
        "te amo", "te quiero", "te adoro", "me encantas",
        "que bonito eres", "que lindo eres", "eres bonito", "eres lindo",
        "eres hermoso", "te extrano",
    ],
    "halago": [
        "eres el mejor", "eres la mejor", "eres genial", "eres increible",
        "eres buenisimo", "que buen profesor", "buen profe", "me caes bien",
        "eres muy bueno", "que crack", "eres un crack", "excelente profesor",
    ],
    "quien_eres": [
        "quien eres", "que eres", "como te llamas", "cual es tu nombre",
        "eres un robot", "eres una ia", "eres humano", "eres real",
        "que significa riff", "quien es riff",
    ],
    "motivacion": [
        "no tengo ganas", "estoy cansado", "estoy cansada", "flojera",
        "desanimado", "desanimada", "motivame", "dame animo", "dame animos",
        "quiero rendirme", "no avanzo", "voy lento",
    ],
    "risa": [
        "jaja", "jajaja", "jeje", "jajajaja", "lol", "xd",
    ],
    "estado_riff": [
        "como estas", "que tal estas", "como te va", "como has estado",
        "todo bien",
    ],
}

# Intenciones que resuelve esta capa (además de colaborar en saludo/fallback).
SOCIALES = set(_FRASES)

# Palabras sueltas que solo cuentan como token exacto.
_TOKENS_EXACTOS = {"gracias", "thanks", "adios", "bye", "chau", "chao",
                   "jaja", "jajaja", "jeje", "jajajaja", "lol", "xd",
                   "motivame", "flojera", "desanimado", "desanimada",
                   "agradecido", "agradecida"}


def detectar(mensaje: str) -> str | None:
    """Intención social del mensaje, o None si no es small talk.

    Un mensaje largo con contenido de guitarra ("gracias, ¿y qué acorde
    sigue?") NO se trata como social: el small talk solo gana cuando el
    mensaje es corto (la frase social ES el mensaje).
    """
    q = _norm(mensaje).strip()
    if not q or len(q.split()) > 7:
        return None
    tokens = set(q.split())
    for intencion, frases in _FRASES.items():
        for f in frases:
            if f in _TOKENS_EXACTOS or " " not in f:
                if f in tokens:
                    return intencion
            elif f in q:
                return intencion
    return None


# ---------------------------------------------------------------------------
# Respuestas por intención: plantillas con variantes. {nombre} se rellena
# con ", Nombre" o "" según el contexto.
# ---------------------------------------------------------------------------

_RESPUESTAS: dict[str, list[str]] = {
    "agradecimiento": [
        "¡Con gusto{nombre}! Me alegra poder ayudarte. Recuerda: unos minutos de práctica "
        "cada día rinden más que una sesión larga de vez en cuando. 🎸",
        "¡Para eso estoy{nombre}! Si te quedó alguna duda, pregúntame con confianza.",
        "¡Un placer{nombre}! Sigue así: la constancia es la que hace guitarristas.",
        "¡De nada{nombre}! Cuando quieras seguimos practicando o resolvemos otra duda. 🎵",
    ],
    "despedida": [
        "¡Hasta luego{nombre}! Sigue practicando aunque sean 10 minutos: tu yo del futuro "
        "te lo va a agradecer. 🎸",
        "¡Nos vemos{nombre}! Aquí te espero para la próxima sesión. 🎵",
        "¡Que te vaya genial{nombre}! Recuerda estirar las manos después de practicar.",
        "¡Adiós{nombre}! Vuelve pronto, que las cuerdas no se tocan solas. 😄",
    ],
    "carino": [
        "Jaja, ¡gracias{nombre}! Me alegra que disfrutes aprender conmigo. Mi trabajo es "
        "ayudarte a convertirte en mejor guitarrista. ¿Qué te gustaría practicar hoy?",
        "¡Qué bonito leer eso{nombre}! A mí me encanta enseñarte. Sigamos haciendo música "
        "juntos: ¿practicamos algo? 🎸",
        "Jaja, gracias{nombre}. Aunque soy un asistente virtual, me alegra un montón que "
        "disfrutes entrenar conmigo. ¿Seguimos con la guitarra?",
    ],
    "halago": [
        "¡Gracias{nombre}! Eso significa que vamos por buen camino. Ahora sigamos "
        "practicando, que lo bueno se construye día a día. 🎸",
        "¡Se hace lo que se puede{nombre}! Pero el mérito es tuyo: tú eres quien pone los "
        "dedos en las cuerdas. ¿Qué practicamos hoy?",
        "¡Gracias{nombre}! Tu avance es mi mejor nota. Aprovechemos el ánimo: ¿una sesión "
        "cortita? 🎵",
    ],
    "quien_eres": [
        "Soy RIFF{nombre}, tu profesor de guitarra en FretMind: te ayudo con teoría, "
        "técnica, práctica y a elegir qué tocar según tu progreso. ¿Por dónde empezamos?",
        "Me llamo RIFF{nombre}: tu tutor personal de guitarra. Conozco tu progreso en "
        "FretMind y puedo recomendarte qué practicar, explicarte teoría o darte ánimos "
        "cuando cueste. 🎸",
        "Soy RIFF{nombre}, tu compañero de aprendizaje en FretMind. Piensa en mí como ese "
        "profe paciente que siempre tiene un consejo y nunca se cansa de repetir. ¿Qué "
        "quieres aprender hoy?",
    ],
    "motivacion": [
        "Te entiendo{nombre}: hay días así. Truco de profe: ponte una meta ridículamente "
        "pequeña, tipo 5 minutos o un solo acorde. Empezar es la parte difícil; el resto "
        "sale solo. 💪",
        "Respira{nombre}. Nadie progresa en línea recta: los días flojos también cuentan "
        "si tocas aunque sea un poquito. ¿Probamos con un ejercicio suave?",
        "Ánimo{nombre} 🎸. Cada guitarrista que admiras pasó por esto mismo. Hoy no "
        "busques tocar perfecto: busca solo tocar. Con eso ya ganaste el día.",
    ],
    "risa": [
        "¡Jaja, me alegra verte de buen humor{nombre}! Con esa energía se practica mejor. "
        "¿Le damos a la guitarra? 🎸",
        "😄 ¡Así da gusto{nombre}! Aprovechemos el buen ánimo para una sesión cortita.",
    ],
    "estado_riff": [
        "¡Muy bien{nombre}, gracias por preguntar! Con cuerda para rato, como buena "
        "guitarra. ¿Y tú, listo para practicar? 🎸",
        "¡De maravilla{nombre}! Enseñar guitarra me pone de buen humor. ¿En qué te ayudo hoy?",
    ],
    # Saludo: lo personaliza ReglasProvider con racha/último ejercicio, aquí
    # van las variantes base.
    "saludo": [
        "¡Hola{nombre}! Soy RIFF. ¿En qué te puedo ayudar hoy? ¿Quieres practicar, "
        "resolver una duda de teoría o mejorar alguna técnica? 🎸",
        "¡Hola{nombre}! Qué gusto verte por aquí. ¿Practicamos algo o tienes alguna duda?",
        "¡Buenas{nombre}! ¿Listo para seguir progresando con la guitarra? 🎵",
        "¡Hola{nombre}! 🎸 ¿Qué tocamos hoy?",
    ],
    "saludo_manana": [
        "¡Buenos días{nombre}! ¿Listo para seguir practicando guitarra? ☀️",
        "¡Buenos días{nombre}! No hay mejor manera de arrancar el día que con unos "
        "acordes. ¿Practicamos?",
    ],
    # Fallback elegante: NUNCA "no entendí".
    "fallback": [
        "No estoy completamente seguro de eso{nombre}, pero si tu pregunta está "
        "relacionada con guitarra o música, intentaré ayudarte con lo que sé. "
        "¿Me la planteas de otra forma?",
        "Esa es una buena pregunta{nombre}. Todavía estoy aprendiendo algunos temas, pero "
        "puedo ayudarte con teoría musical, técnica, práctica de guitarra y con el "
        "funcionamiento de FretMind. ¿Por dónde te gustaría empezar?",
        "Hmm, esa se me escapa un poco{nombre} 🎸. Donde sí soy fuerte es en guitarra: "
        "acordes, escalas, ritmo, afinación o qué practicar hoy. ¿Te ayudo con algo de eso?",
        "No tengo una buena respuesta para eso todavía{nombre}, pero no me quedo callado: "
        "si es sobre música o guitarra, dame más detalles e intento ayudarte con mis "
        "conocimientos actuales.",
    ],
}


def responder(intencion: str, ctx: dict | None = None,
              historial: list[dict] | None = None) -> str | None:
    """Respuesta social con variantes y anti-repetición. None si la
    intención no es de esta capa."""
    variantes = _RESPUESTAS.get(intencion)
    if not variantes:
        return None
    nombre = (ctx or {}).get("nombre")
    relleno = f", {nombre}" if nombre else ""

    # Anti-repetición: evita las respuestas que RIFF ya dio hace poco.
    recientes = {
        t.get("texto") for t in (historial or [])[-6:] if t.get("rol") == "riff"
    }
    candidatas = [v.format(nombre=relleno) for v in variantes]
    frescas = [c for c in candidatas if c not in recientes]
    return random.choice(frescas or candidatas)


def es_saludo_de_manana(mensaje: str) -> bool:
    q = _norm(mensaje)
    return "buenos dias" in q or "buen dia" in q
