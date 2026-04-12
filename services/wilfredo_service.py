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
    """respuesta del chat - sin ia, solo reglas"""
    msg = mensaje.lower()
    
    # saludos
    if any(s in msg for s in ["hola", "hi", "hello", "buenos", "ey"]):
        return random.choice(GREETINGS)
    
    # pide ayuda
    if any(s in msg for s in ["ayuda", "help", "qué puedes", "qué haces", "cómo"]):
        return HELP_OFFERS[random.randint(0, 2)]
    
    # tema afinación
    if any(s in msg for s in ["afin", "tuner", "afinar", "frecuencia"]):
        return "Para afinar: toca la cuerda y observa los cents. Menos de 5 = afinado. 🎵"
    
    # tema acordes
    if any(s in msg for s in ["acorde", "chord", "acordes", "am", "em", "c", "g", "d"]):
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
    if any(s in msg for s in ["nivel", "soy", "experiencia", "llevo"]):
        nivel_detectado = evaluate_user_level(mensaje)
        return f"Entendido. Eres nivel {nivel_detectado}. ¡Trabajaremos en eso! 🎯"
    
    # despedidas
    if any(s in msg for s in ["adiós", "bye", "salir", "nos vemos"]):
        return "¡Hasta luego! Sigue practicando. 🎸"
    
    # si no entiendo nada
    responses = [
        "¡Interesante! Cuéntame más sobre lo que quieres practicar. 🎵",
        "¿Te refieres a digitación, ritmo o teoría? Dime para ayudarte mejor. 🎸",
        "Practiquemos juntos. Dime qué área te interesa. 🎯"
    ]
    return responses[random.randint(0, 2)]


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