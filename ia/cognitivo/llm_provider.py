"""
LLMProvider (MC8) - Interfaz de proveedor conversacional.

El Motor Cognitivo NUNCA habla con un modelo concreto: habla con esta
interfaz. Cambiar de proveedor (reglas hoy; Anthropic, OpenAI u otro
mañana) es registrar una implementación nueva y fijar la variable de
entorno LLM_PROVIDER — cero cambios en los módulos cognitivos.

Contrato:
    generar(mensaje, contexto, historial) -> str | None
    - contexto: dict del Context Builder (selectivo por intención)
    - historial: últimos turnos [{rol, texto}] (memoria conversacional)
    - None o excepción => el orquestador cae al fallback determinístico
      (ReglasProvider), que SIEMPRE responde.
"""

import os

from domain import habilidades as habilidades_dominio
from services.wilfredo_service import generate_chat_response


class LLMProvider:
    nombre = "base"

    def generar(self, mensaje: str, contexto: dict, historial: list[dict]) -> str | None:
        raise NotImplementedError


class ReglasProvider(LLMProvider):
    """Proveedor determinístico: respuestas por intención sobre el contexto
    selectivo + Base de Conocimiento. Es el proveedor por defecto Y el
    fallback permanente: no depende de red ni de claves."""

    nombre = "reglas"

    def generar(self, mensaje: str, contexto: dict, historial: list[dict]) -> str | None:
        ctx = contexto
        intencion = ctx.get("intencion", "general")
        nombre = ctx.get("nombre")
        saludo_nombre = f", {nombre}" if nombre else ""

        if intencion == "teoria" and ctx.get("conocimiento"):
            k = ctx["conocimiento"][0]
            extra = ""
            if len(ctx["conocimiento"]) > 1:
                extra = f" Relacionado: {ctx['conocimiento'][1]['titulo']}."
            return f"📚 {k['titulo']}. {k['contenido']}{extra}"

        if intencion == "que_practico":
            rec = ctx.get("recomendacion")
            ej = ctx.get("ejercicio_recomendado")
            if rec and rec.get("tipo") == "descanso":
                return f"Hoy ya practicaste {int(ctx.get('minutos_hoy', 0))} min{saludo_nombre}. {rec['razon']}"
            if rec and ej:
                return (f"Te recomiendo {ej['nombre']} ({ej['duracion_min']} min, "
                        f"dificultad {rec.get('dificultad', ej['dificultad'])}/5). "
                        f"¿Por qué? {rec['razon']}")

        if intencion == "progreso":
            if ctx.get("total_intentos", 0) == 0:
                return (f"Aún no registras prácticas{saludo_nombre}. Completa tu primera "
                        f"sesión y te contaré exactamente cómo avanzas. 🎸")
            d = ctx.get("desempeno", {})
            partes = []
            if ctx.get("racha", 0) > 0:
                partes.append(f"llevas {ctx['racha']} día(s) de racha")
            if d.get("promedio_puntuacion") is not None:
                partes.append(f"tu media reciente es {int(d['promedio_puntuacion'])}/100")
            if d.get("xp_total"):
                partes.append(f"acumulas {d['xp_total']} XP")
            if d.get("tendencia") == "mejorando":
                partes.append("y vas mejorando 📈")
            elif d.get("tendencia") == "bajando":
                partes.append("aunque los últimos intentos bajaron: sin prisa")
            estado = ctx.get("estado", {})
            extra = ""
            if estado.get("en_evolucion"):
                nombres = ", ".join(habilidades_dominio.NOMBRES.get(s, s)
                                    for s in estado["en_evolucion"][:2])
                extra = f" Estás en clara evolución en {nombres}."
            elif ctx.get("debilidades"):
                extra = f" Te conviene reforzar {ctx['debilidades'][0]['nombre']}."
            cuerpo = ", ".join(partes) if partes else f"llevas {ctx['total_intentos']} intentos"
            return f"Vas así{saludo_nombre}: {cuerpo}.{extra}"

        if intencion == "ultimo_intento":
            u = ctx.get("ultimo_intento")
            if not u:
                return "Todavía no tienes intentos registrados. ¡Tu primera práctica te espera! 🎸"
            base = f"Tu último intento fue de «{u['ejercicio']}»"
            if u.get("estrellas") is not None:
                base += f": {u['estrellas']}⭐ con {int(u.get('puntuacion') or 0)}/100"
            consejo = (" ¡Gran trabajo, toca subir la dificultad!" if (u.get("puntuacion") or 0) >= 85
                       else " Una repetición más y lo afianzas." if (u.get("puntuacion") or 0) >= 40
                       else " Bajemos el tempo y vamos por partes. 🐢")
            return base + "." + consejo

        if intencion == "canciones":
            canciones = ctx.get("canciones") or []
            if not canciones:
                return ("Aún no guardas canciones. Busca una que te guste y tócala: "
                        "practicar con música real motiva el doble. 🎵")
            partes = []
            for c in canciones[:3]:
                marca = f" (mejor: {int(c['mejor_puntuacion'])})" if c.get("mejor_puntuacion") else ""
                partes.append(f"«{c['titulo']}» [{c['estado']}{marca}]")
            return (f"Tu biblioteca{saludo_nombre}: {', '.join(partes)}. "
                    f"Elige una y usa Practicar: te preparo objetivos a tu medida. 🎸")

        if intencion == "frustracion":
            debil = (ctx.get("debilidades") or [{}])
            nombre_debil = debil[0].get("nombre", "esa técnica") if debil else "esa técnica"
            racha = ctx.get("racha", 0)
            animo = (f"Llevas {racha} día(s) seguidos practicando: eso ya te separa "
                     f"de la mayoría. " if racha > 0 else "")
            tip = ""
            if ctx.get("conocimiento"):
                tip = f" Consejo concreto: {ctx['conocimiento'][0]['contenido']}"
            return (f"{animo}Es normal que {nombre_debil} cueste{saludo_nombre}. "
                    f"Baja la velocidad a la mitad y celebra cada repetición limpia: el "
                    f"cerebro aprende de la precisión, no de la prisa. 💪{tip}")

        if intencion == "saludo":
            memoria = ""
            u = ctx.get("ultimo_intento")
            if u:
                memoria = f" La última vez practicaste «{u['ejercicio']}»."
            racha = ctx.get("racha", 0)
            r = f" ¡{racha} días de racha! 🔥" if racha >= 2 else ""
            # Memoria conversacional mínima: no repetir el mismo saludo seguido.
            ya_saludo = any(
                t.get("rol") == "riff" and "¡Hola" in (t.get("texto") or "")
                for t in historial[-4:]
            )
            if ya_saludo:
                return f"¡Seguimos{saludo_nombre}! ¿Practicamos o tienes alguna duda? 🎸"
            return f"¡Hola{saludo_nombre}! 🎸{r}{memoria} ¿Practicamos?"

        # General: si hay conocimiento relevante, úsalo; si no, reglas clásicas.
        if ctx.get("conocimiento"):
            k = ctx["conocimiento"][0]
            return f"📚 {k['titulo']}. {k['contenido']}"
        return generate_chat_response(mensaje, ctx.get("nivel", "principiante"))


# Registro de proveedores. Añadir un LLM = nueva clase + entrada aquí.
_PROVIDERS: dict[str, type[LLMProvider]] = {
    "reglas": ReglasProvider,
}

_fallback = ReglasProvider()


def obtener_provider() -> LLMProvider:
    """Proveedor activo según LLM_PROVIDER (default: reglas)."""
    nombre = os.getenv("LLM_PROVIDER", "reglas").lower().strip()
    clase = _PROVIDERS.get(nombre, ReglasProvider)
    try:
        return clase()
    except Exception:
        return _fallback


def fallback_provider() -> LLMProvider:
    return _fallback
