"""
Context Builder v2 (MC7).

Construye el contexto que recibe el proveedor conversacional (LLMProvider)
seleccionando SOLO la información relevante según la INTENCIÓN del mensaje:
una duda de teoría trae entradas de la Base de Conocimiento, no la
biblioteca; una pregunta de progreso trae desempeño y análisis, no teoría.

Lee el Learning Profile (1 documento) en vez de repetir agregaciones, y
aplica presupuesto: listas recortadas a top-3 y textos cortos. El mismo
contexto sirve para el ReglasProvider de hoy y para un LLM futuro
(render_texto lo convierte en system prompt).
"""

from domain import conocimiento
from ia.cognitivo import adaptive_engine, learning_profile

INTENCIONES = {
    "que_practico": ["qué practico", "que practico", "qué hago", "que hago", "recomien",
                     "siguiente", "hoy toca", "practicar hoy", "plan de hoy", "rutina"],
    "progreso": ["cómo voy", "como voy", "progreso", "avance", "estadística", "estadistica",
                 "racha", "mejorando", "nivel voy"],
    "ultimo_intento": ["última", "ultima", "último", "ultimo", "me fue", "resultado", "ayer"],
    "canciones": ["canción", "cancion", "biblioteca", "guardad", "favorit", "tocar una"],
    "frustracion": ["difícil", "dificil", "no me sale", "no puedo", "frustra", "duro",
                    "me rindo", "imposible"],
    "saludo": ["hola", "buenos", "buenas", "hello", "hey", "ey"],
}


def detectar_intencion(mensaje: str) -> str:
    msg = mensaje.lower()
    for intencion, claves in INTENCIONES.items():
        if any(c in msg for c in claves):
            return intencion
    # Teoría/técnica: si la Base de Conocimiento tiene algo relevante.
    if conocimiento.buscar(mensaje, k=1):
        return "teoria"
    return "general"


def _top(lista, n=3):
    return (lista or [])[:n]


def construir(user_id: str, mensaje: str, tz_offset_min: int = 0) -> dict | None:
    """Contexto selectivo por intención. None si el usuario no existe."""
    perfil = learning_profile.obtener_perfil(user_id)
    if perfil is None:
        return None

    intencion = detectar_intencion(mensaje)
    desempeno = perfil.get("desempeno", {})

    # Base común, siempre pequeña.
    ctx: dict = {
        "intencion": intencion,
        "nombre": (perfil.get("nombre") or "").split(" ")[0] or None,
        "nivel": perfil.get("nivel", "principiante"),
        "objetivo": (perfil.get("preferencias") or {}).get("objetivo"),
        "racha": desempeno.get("racha", 0),
        "total_intentos": desempeno.get("total_intentos", 0),
    }

    if intencion in ("que_practico", "general"):
        decision = adaptive_engine.decidir(user_id, offset_min=tz_offset_min, persistir=False)
        if decision:
            ctx["recomendacion"] = decision["recomendacion"]
            ctx["ejercicio_recomendado"] = decision.get("ejercicio")
        ctx["minutos_hoy"] = desempeno.get("minutos_hoy", 0)

    if intencion in ("progreso", "frustracion", "saludo"):
        analisis = perfil.get("analisis", {})
        ctx["desempeno"] = {
            "promedio_puntuacion": desempeno.get("promedio_puntuacion"),
            "tendencia": desempeno.get("tendencia"),
            "xp_total": desempeno.get("xp_total", 0),
            "minutos_hoy": desempeno.get("minutos_hoy", 0),
        }
        ctx["fortalezas"] = _top(analisis.get("fortalezas"))
        ctx["debilidades"] = _top(analisis.get("debilidades"))
        ctx["estado"] = perfil.get("estado", {})
        ctx["hitos_recientes"] = _top(perfil.get("hitos_recientes"), 2)

    if intencion in ("ultimo_intento", "saludo"):
        intentos_ctx = perfil.get("hitos_recientes")  # hitos como color adicional
        ctx.setdefault("hitos_recientes", _top(intentos_ctx, 2))
        # Último intento desde el perfil de canciones/desempeño no basta:
        # el Context Builder lo pide directo (barato, 1 query).
        from database import intentos_ejercicio
        ultimo = intentos_ejercicio.find_one(
            {"usuario": user_id}, {"_id": 0}, sort=[("fecha", -1)]
        )
        if ultimo:
            ctx["ultimo_intento"] = {
                "ejercicio": ultimo.get("ejercicio"),
                "puntuacion": ultimo.get("puntuacion"),
                "estrellas": ultimo.get("estrellas"),
                "aprobado": ultimo.get("aprobado"),
            }

    if intencion == "canciones":
        ctx["canciones"] = _top(perfil.get("canciones"), 3)

    if intencion in ("teoria", "general", "frustracion"):
        entradas = conocimiento.buscar(mensaje, nivel=ctx["nivel"], k=2)
        if entradas:
            ctx["conocimiento"] = [
                {"id": e["id"], "titulo": e["titulo"], "contenido": e["contenido"],
                 "categoria": e["categoria"]}
                for e in entradas
            ]

    return ctx


def render_texto(ctx: dict) -> str:
    """Contexto como texto plano (system prompt para un LLM futuro)."""
    lineas = [
        f"Alumno: {ctx.get('nombre') or 'sin nombre'} | nivel {ctx.get('nivel')} | "
        f"objetivo: {ctx.get('objetivo') or 'no declarado'} | racha {ctx.get('racha')} días",
    ]
    if ctx.get("desempeno"):
        d = ctx["desempeno"]
        lineas.append(f"Desempeño: media {d.get('promedio_puntuacion')} | "
                      f"tendencia {d.get('tendencia')} | XP {d.get('xp_total')}")
    if ctx.get("recomendacion"):
        r = ctx["recomendacion"]
        lineas.append(f"Recomendación vigente: {r.get('ejercicio_id')} — {r.get('razon')}")
    if ctx.get("ultimo_intento"):
        u = ctx["ultimo_intento"]
        lineas.append(f"Último intento: {u.get('ejercicio')} "
                      f"{u.get('estrellas')}⭐ {u.get('puntuacion')}/100")
    for c in ctx.get("canciones", []):
        lineas.append(f"Canción: {c['titulo']} ({c['estado']}, mejor {c.get('mejor_puntuacion')})")
    for k in ctx.get("conocimiento", []):
        lineas.append(f"[Conocimiento] {k['titulo']}: {k['contenido']}")
    return "\n".join(lineas)
