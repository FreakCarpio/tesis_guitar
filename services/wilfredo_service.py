"""
Wilfredo - mi tutor inteligente de guitarra
sin depender de apis externas, todo con reglas
"""

import random
from typing import Optional

# esto lo uso para que wilfredo siempre reaccione igual
PERSONALITY = "Wilfredo, instructor experto y paciente de guitarra acústica. Explica en pasos simples, es motivador."

# saludos random para que no parezca robot
GREETINGS = [
    "¡Hola! Soy Wilfredo. ¿Qué te trae por aquí hoy? 🎸",
    "¡Bienvenido! Soy Wilfredo, tu instructor de guitarra. ¿En qué trabajaremos? 🎸",
    "¡Hola! Practiquemos juntos. ¿Qué quieres aprender hoy?"
]

# opciones de ayuda cuando no sabe qué pedir
HELP_OFFERS = [
    "Puedo ayudarte con: afinación, acordes, digitación, ritmo o ejercicios. ¿Qué prefieres?",
    "Tengo ejercicios de: principiante, intermedio y avanzado. ¿Cuál es tu nivel?",
    "Podemos trabajar técnica, teoría o práctica. ¿Qué te interesa?"
]

# palabras clave para detectar nivel del usuario
LEVEL_KEYWORDS = {
    "principiante": ["nunca", "principiante", "novato", "primera vez", "basic", "empezar", "inicio"],
    "intermedio": ["intermedio", "medium", "ya sé", "llevo", "años", "experiencia"],
    "avanzado": ["avanzado", "experto", "profesional", "avanzada", "master"]
}

def evaluate_user_level(text: str) -> str:
    """saco el nivel segun lo que escriba"""
    text = text.lower()
    for nivel, keywords in LEVEL_KEYWORDS.items():
        if any(k in text for k in keywords):
            return nivel
    return "principiante"


def analyze_tuner_feedback(frecuencia: float, nota: str, cents: float) -> str:
    """feedback segun qué tan desafinado está"""
    abs_cents = abs(cents)
    
    if abs_cents < 5:
        return f"¡Perfecto! La nota {nota} está afinada. 🎵 ¡Sigue así!"
    
    elif abs_cents < 15:
        direccion = "alta" if cents > 0 else "baja"
        return f"Casi ahí. Estás un poco {direccion}. Ajusta la clavija apenas. 🔧"
    
    elif abs_cents < 30:
        direccion = "alta" if cents > 0 else "baja"
        return f"Estás {direccion}. Gira la clavija lento. 🎸"
    
    else:
        direccion = "alta" if cents > 0 else "baja"
        return f"Vamos a afinar: {nota} está muy {direccion}. Gira la clavija hacia el tono correcto. 🔨"


def analyze_chord_feedback(acorde: dict) -> str:
    """feedback del acorde que detectó"""
    if not acorde or acorde.get("tipo") == "Desconocido":
        return "No detecté un acorde claro. Intenta más lento y claro. 🎸"
    
    nombre = acorde.get("nombre", "")
    tipo = acorde.get("tipo", "")
    
    # acordes básicos que todo el mundo aprende primero
    simple_chords = ["C", "G", "D", "Am", "Em", "A", "E"]
    
    if nombre in simple_chords:
        return f"¡Bien! Detecté {nombre}. Este es básico. ¡Sigue practicando! 🎵"
    
    elif tipo in ["Mayor", "Menor"]:
        return f"¡Buena ejecución! {nombre} suena bien. Continúa practicando. 🎸"
    
    else:
        return f"¡Buen trabajo! {nombre} ({tipo}). ¡Sigue así! 🎸"


def generate_practice_feedback(metricas: dict) -> str:
    """genero feedback pedagógico segun las métricas"""
    precision = metricas.get("precision", 0)
    consistencia = metricas.get("consistencia", 0)
    nota = metricas.get("nota_detectada", "N/A")
    
    if precision >= 0.9 and consistencia >= 0.8:
        return f"¡Excelente! Tu ejecución de {nota} fue precisa. ¡Sigue así! 🌟"
    
    elif precision >= 0.7:
        return f"¡Buen trabajo! Procura mantener el ritmo constante. 🥁"
    
    elif precision >= 0.5:
        return f"Vamos bien. Céntrate en la digitación y el tempo. ¡Practica todos los días! 🎸"
    
    else:
        return f"No te preocupes. Todo maestro fue principiante. ¡Sigue intentando! 💪"


def generate_chat_response(mensaje: str, nivel: str = "principiante") -> str:
    """respuesta del chat - sin ia, solo reglas.

    Ahora con la capa social de RIFF por delante (saludos, gracias,
    despedidas, cariño... con variantes) y fallback amable: nunca
    responde "no entendí".
    """
    # Capa social compartida con el Motor Cognitivo (sin dependencia
    # circular: conversacion no importa nada de services).
    from ia.cognitivo import conversacion

    social = conversacion.detectar(mensaje)
    if social:
        r = conversacion.responder(social)
        if r:
            return r

    msg = mensaje.lower()
    tokens = set(msg.replace("¿", " ").replace("?", " ").replace(",", " ").split())

    # saludos (por token: "hola" suelto sí; "hola" dentro de otra palabra no)
    if tokens & {"hola", "hi", "hello", "buenos", "buenas", "hey"}:
        return conversacion.responder(
            "saludo_manana" if conversacion.es_saludo_de_manana(mensaje) else "saludo"
        ) or random.choice(GREETINGS)

    # pide ayuda
    if any(s in msg for s in ["ayuda", "help", "qué puedes", "que puedes", "qué haces",
                              "que haces", "qué sabes", "que sabes"]):
        return random.choice(HELP_OFFERS)

    # tema afinación
    if any(s in msg for s in ["afin", "tuner", "frecuencia"]):
        return ("Para afinar: abre el Afinador, toca una cuerda y mira los cents. "
                "Entre -5 y +5 ya está afinada. Si marca negativo aprieta la clavija; "
                "si marca positivo, afloja. 🎵")

    # tema acordes ("am"/"c"/"g"/"d" solo como palabra exacta: antes "te amo"
    # disparaba esta regla por el "am" interno)
    if ("acorde" in msg or "chord" in msg or
            tokens & {"am", "em", "c", "g", "d", "do", "re", "mi", "fa", "sol", "la", "si"}):
        return f"Nivel {nivel}: Practica acordes básicos: C, G, D, Am, Em. Son la base. 🎸"

    # ejercicios
    if any(s in msg for s in ["ejercicio", "practicar", "practica", "ejerc"]):
        plans = {
            "principiante": "Ejercicios: cambio de C a G, escala pentatónica, ritmo 4/4.",
            "intermedio": "Ejercicios: escalas, arpegios, cambios rápidos de acordes.",
            "avanzado": "Ejercicios: técnica, velocidad, canciones completas."
        }
        return plans.get(nivel, plans["principiante"])

    # pregunta de nivel
    if any(s in msg for s in ["nivel", "experiencia", "llevo"]) or "soy" in tokens:
        nivel_detectado = evaluate_user_level(mensaje)
        return f"Entendido. Eres nivel {nivel_detectado}. ¡Trabajaremos en eso! 🎯"

    # despedidas
    if any(s in msg for s in ["adiós", "adios", "bye", "salir", "nos vemos"]):
        return conversacion.responder("despedida") or "¡Hasta luego! Sigue practicando. 🎸"

    # sin intención clara: fallback amable en personaje (nunca "no entendí")
    return conversacion.responder("fallback") or HELP_OFFERS[0]


def generate_tutor_response(mensaje: str, ctx: dict) -> str:
    """Respuesta de Wilfredo como TUTOR con memoria de desempeño (P1.6).

    Usa el contexto real del usuario (perfil, habilidades, racha, intentos,
    biblioteca, recomendación del motor) para responder como un profesor
    que recuerda cómo toca el alumno. Determinístico: intenciones por
    palabras clave; si ninguna aplica, cae en las reglas genéricas.
    """
    msg = mensaje.lower()
    nombre = ctx.get("nombre")
    saludo_nombre = f", {nombre}" if nombre else ""

    # --- ¿Qué practico ahora? -> recomendación real del motor ---
    if any(s in msg for s in ["qué practico", "que practico", "qué hago", "que hago",
                              "recomien", "siguiente", "ahora", "hoy toca", "practicar hoy"]):
        rec = ctx.get("recomendacion")
        ej = ctx.get("ejercicio_recomendado")
        if rec and rec.get("tipo") == "descanso":
            return f"Hoy ya practicaste {int(ctx['minutos_hoy'])} min{saludo_nombre}. {rec['razon']}"
        if rec and ej:
            return (f"Te recomiendo {ej['nombre']} ({ej['duracion_min']} min, "
                    f"dificultad {rec.get('dificultad', ej['dificultad'])}/5). "
                    f"¿Por qué? {rec['razon']}")

    # --- ¿Cómo voy? -> progreso real ---
    if any(s in msg for s in ["cómo voy", "como voy", "progreso", "avance", "estadística",
                              "estadistica", "racha", "mejorando"]):
        partes = []
        if ctx.get("total_sesiones", 0) == 0:
            return (f"Aún no registras prácticas{saludo_nombre}. Completa tu primera "
                    f"sesión y podré contarte exactamente cómo avanzas. 🎸")
        if ctx.get("racha", 0) > 0:
            partes.append(f"llevas {ctx['racha']} día(s) de racha")
        if ctx.get("promedio_puntuacion") is not None:
            partes.append(f"tu puntuación media reciente es {int(ctx['promedio_puntuacion'])}/100")
        if ctx.get("tendencia") == "mejorando":
            partes.append("y vas mejorando 📈")
        elif ctx.get("tendencia") == "bajando":
            partes.append("aunque tus últimos intentos bajaron un poco: sin prisa, vuelve a lo básico")
        fuerte = (ctx.get("fuertes") or [{}])[0].get("nombre")
        debil = (ctx.get("debiles") or [{}])[0].get("nombre")
        extra = f" Tu punto fuerte es {fuerte} y te conviene reforzar {debil}." if fuerte and debil else ""
        cuerpo = ", ".join(partes) if partes else f"llevas {ctx['total_sesiones']} sesiones registradas"
        return f"Vas así{saludo_nombre}: {cuerpo}.{extra}"

    # --- ¿Cómo me fue? -> último intento (memoria) ---
    if any(s in msg for s in ["última", "ultima", "último", "ultimo", "me fue", "resultado", "ayer"]):
        u = ctx.get("ultimo_intento")
        if not u:
            return "Todavía no tienes intentos registrados. ¡Tu primera práctica te espera! 🎸"
        base = f"Tu último intento fue de «{u['ejercicio']}»"
        if u.get("estrellas") is not None:
            base += f": {u['estrellas']}⭐ con {int(u.get('puntuacion') or 0)}/100"
        elif u.get("precision") is not None:
            base += f": precisión {int(u['precision'] * 100)}%"
        consejo = (" ¡Gran trabajo, sube la dificultad!" if (u.get("puntuacion") or 0) >= 85
                   else " Repítelo una vez más para afianzarlo." if (u.get("puntuacion") or 0) >= 40
                   else " Bajemos el tempo y vamos por partes, sin frustrarse. 🐢")
        return base + "." + consejo

    # --- Canciones -> biblioteca real ---
    if any(s in msg for s in ["canción", "cancion", "biblioteca", "guardad", "favorit", "tocar una"]):
        canciones = ctx.get("canciones") or []
        if not canciones:
            return ("Aún no guardas canciones. Busca una que te guste y tócala: "
                    "practicar con música real motiva el doble. 🎵")
        nombres = ", ".join(f"«{c['titulo']}»" for c in canciones[:3])
        return (f"En tu biblioteca tienes {nombres}. Elige una y usa el botón "
                f"Practicar: te preparo objetivos a tu medida. 🎸")

    # --- Frustración -> apoyo con datos ---
    if any(s in msg for s in ["difícil", "dificil", "no me sale", "no puedo", "frustra", "mal", "duro"]):
        debil = (ctx.get("debiles") or [{}])[0].get("nombre", "esa técnica")
        racha = ctx.get("racha", 0)
        animo = f"Llevas {racha} día(s) seguidos practicando: eso ya te separa de la mayoría. " if racha > 0 else ""
        return (f"{animo}Es normal que {debil} cueste al principio{saludo_nombre}. "
                f"Baja la velocidad a la mitad y celebra cada repetición limpia: "
                f"el cerebro aprende de la precisión, no de la prisa. 💪")

    # --- Saludo personalizado con memoria ---
    if any(s in msg for s in ["hola", "hi", "hello", "buenos", "buenas", "ey"]):
        memoria = ""
        u = ctx.get("ultimo_intento")
        if u:
            memoria = f" La última vez practicaste «{u['ejercicio']}»."
        racha = ctx.get("racha", 0)
        r = f" ¡{racha} días de racha! 🔥" if racha >= 2 else ""
        return f"¡Hola{saludo_nombre}! 🎸{r}{memoria} ¿Practicamos?"

    # Sin intención clara: reglas genéricas de siempre.
    return generate_chat_response(mensaje, ctx.get("nivel", "principiante"))


def generate_song_plan(titulo: str, artista: str, dificultad: Optional[str] = None,
                       tiene_acordes: bool = True, nivel: str = "principiante") -> dict:
    """Objetivos de práctica para una canción concreta (determinístico).

    Se usa cuando el usuario pulsa "Practicar" en el detalle de una canción:
    Wilfredo genera objetivos según la dificultad de la tablatura, si tiene
    acordes y el nivel del usuario.
    """
    objetivos = [f"Escucha «{titulo}» completa y ubica las partes difíciles"]

    if tiene_acordes:
        objetivos.append("Repasa la progresión de acordes en bucle, lenta y limpia")
    else:
        objetivos.append("Practica el riff principal en bucle, lento y limpio")

    if dificultad == "Avanzado":
        objetivos.append("Divide la canción en secciones cortas y domina una por sesión")
    elif dificultad == "Intermedio":
        objetivos.append("Sube el tempo solo cuando toques 3 veces seguidas sin errores")
    else:
        objetivos.append("Mantén un pulso constante aunque sea muy lento")

    objetivos.append("Toca de inicio a fin sin detenerte, aunque haya errores")

    consejos = {
        "principiante": f"No busques velocidad en «{titulo}»: busca que cada acorde suene completo. 🐢",
        "intermedio": f"Usa metrónomo con «{titulo}» y sube 5 BPM por sesión limpia. 🎯",
        "avanzado": f"Trabaja la dinámica de «{titulo}»: que se distingan versos de coros. 🎸",
    }

    return {
        "objetivos": objetivos,
        "consejo": consejos.get(nivel, consejos["principiante"]),
        "duracion_sugerida_min": 20 if dificultad == "Avanzado" else 15,
    }


def generate_practice_plan(nivel: str, goal: Optional[str] = None) -> dict:
    """genero plan de práctica segun nivel"""
    plans = {
        "principiante": {
            "ejercicios": ["Cambio C→G", "Escala Do", "Ritmo básico"],
            "duracion": "15 min/día",
            "consejo": "Céntrate en la digitación correcta primero."
        },
        "intermedio": {
            "ejercicios": ["Escalas mayores", "Arpegios", "Cambios rápidos"],
            "duracion": "30 min/día",
            "consejo": "Trabaja velocidad y precisión."
        },
        "avanzado": {
            "ejercicios": ["Técnica avanzada", "Canciones", "Improvisación"],
            "duracion": "45+ min/día",
            "consejo": "Enfócate en expresión y dinámicas."
        }
    }
    
    plan = plans.get(nivel, plans["principiante"])
    
    if goal:
        goal_lower = goal.lower()
        if "acorde" in goal_lower:
            plan["consejo"] += " Practica cambios de acordes todos los días."
        elif "ritmo" in goal_lower:
            plan["consejo"] += " Usa metrónomo."
    
    return plan