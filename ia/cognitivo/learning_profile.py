"""
Learning Profile (MC1) - Perfil dinámico del estudiante.

Documento vivo en `perfil_aprendizaje` (uno por usuario) que se reconstruye
tras cada práctica (hook best-effort en /practica). Es la memoria de largo
plazo del Motor Cognitivo: los demás módulos leen ESTE documento en vez de
repetir agregaciones sobre media base de datos.

Contenido:
- preferencias: objetivo declarado, géneros (inferidos de la biblioteca),
  estilo de aprendizaje (inferido de conducta real)
- habilidades con DOS confianzas separadas:
    · confianza (recencia)  - decae con inactividad (ya existía, P1)
    · evidencia (volumen)   - cuánta información real respalda la evaluación
      (n/(n+K)); etiqueta alta/media/baja. Regla de oro: ninguna decisión
      fuerte sobre evidencia baja.
- estilo de práctica: frecuencia, duración media, modo preferido, enfoque
- resumen de desempeño: racha, puntuación media, tendencia, XP total
- canciones en aprendizaje (intentos y mejor marca por canción)
- hitos_recientes: los llena Progress Intelligence (MC2)
"""

from datetime import datetime, timedelta, timezone

from database import (
    biblioteca_usuario,
    cancion_cache,
    intentos_ejercicio,
    perfil_aprendizaje,
    usuarios,
)
from domain import ejercicios as ejercicios_dominio
from domain import habilidades as habilidades_dominio
from ia import motor_adaptativo_v1 as motor

VERSION_PERFIL = 1

# Saturación de la evidencia: con K muestras la confianza-evidencia es 0.5.
K_EVIDENCIA = 5

# Umbrales de la etiqueta de evidencia.
EVIDENCIA_ALTA = 0.7    # ~12+ muestras
EVIDENCIA_MEDIA = 0.4   # ~4+ muestras


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _fecha(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _confianza_evidencia(n: int) -> float:
    return round(n / (n + K_EVIDENCIA), 3)


def _etiqueta_evidencia(valor: float) -> str:
    if valor >= EVIDENCIA_ALTA:
        return "alta"
    if valor >= EVIDENCIA_MEDIA:
        return "media"
    return "baja"


# --------------------------------------------------------------------------
# Inferencias
# --------------------------------------------------------------------------

def _evidencia_por_habilidad(intentos: list[dict]) -> dict[str, int]:
    """Muestras de evidencia por skill: cada paso ejecutado cuenta 1; los
    intentos sin pasos (práctica libre) aportan 1 a la habilidad principal
    del ejercicio."""
    conteo: dict[str, int] = {h: 0 for h in habilidades_dominio.HABILIDADES}
    for intento in intentos:
        pasos = intento.get("pasos") or []
        if pasos:
            for p in pasos:
                skill = p.get("skill")
                if skill in conteo:
                    conteo[skill] += 1
        else:
            ej = ejercicios_dominio.obtener_ejercicio(
                intento.get("ejercicio", "practica_general")
            )
            conteo[ej["habilidad"]] += 1
    return conteo


def _preferencias(usuario: dict, canciones_biblioteca: list[dict]) -> dict:
    """Objetivo declarado + géneros inferidos de la biblioteca (iTunes)."""
    generos: dict[str, int] = {}
    for item in canciones_biblioteca:
        det = cancion_cache.find_one({"song_id": item["song_id"]}, {"data.genero": 1})
        genero = ((det or {}).get("data") or {}).get("genero")
        if genero:
            generos[genero] = generos.get(genero, 0) + 1
    top_generos = sorted(generos, key=generos.get, reverse=True)[:3]
    return {
        "objetivo": usuario.get("objetivo"),
        "experiencia_declarada": usuario.get("experiencia"),
        "generos": top_generos,
    }


def _estilo_practica(intentos: list[dict], ahora: datetime) -> dict:
    """Estilo inferido de la conducta real (no de lo declarado)."""
    if not intentos:
        return {
            "frecuencia_7d": 0, "duracion_media_min": 0.0,
            "modo_preferido": "por_descubrir", "enfoque": "por_descubrir",
            "etiqueta": "nuevo",
        }

    hace_7d = ahora - timedelta(days=7)
    ultimos_7d = [i for i in intentos if (_fecha(i.get("fecha")) or ahora) >= hace_7d]

    duraciones = [int(i.get("duracion_seg", 0) or 0) for i in intentos]
    duracion_media_min = round(sum(duraciones) / len(duraciones) / 60.0, 1)

    con_pasos = sum(1 for i in intentos if i.get("pasos"))
    modo = "por_descubrir"
    if len(intentos) >= 3:
        modo = "guiado" if con_pasos >= len(intentos) / 2 else "libre"

    con_cancion = sum(1 for i in intentos if i.get("cancion_id") is not None)
    enfoque = "por_descubrir"
    if len(intentos) >= 3:
        ratio = con_cancion / len(intentos)
        enfoque = "canciones" if ratio >= 0.4 else ("mixto" if ratio >= 0.15 else "ejercicios")

    etiqueta = "constante" if len(ultimos_7d) >= 4 else ("ocasional" if ultimos_7d else "inactivo")

    return {
        "frecuencia_7d": len(ultimos_7d),
        "duracion_media_min": duracion_media_min,
        "modo_preferido": modo,
        "enfoque": enfoque,
        "etiqueta": etiqueta,
    }


def _canciones_aprendiendo(user_id: str, intentos: list[dict]) -> list[dict]:
    """Progreso por canción: intentos y mejor marca, unido a la biblioteca."""
    por_cancion: dict[int, list[dict]] = {}
    for i in intentos:
        cid = i.get("cancion_id")
        if cid is not None:
            por_cancion.setdefault(int(cid), []).append(i)

    items = list(biblioteca_usuario.find({"usuario": user_id}, {"_id": 0}))
    resultado = []
    for item in items:
        cid = int(item["song_id"])
        propios = por_cancion.get(cid, [])
        puntuaciones = [i["puntuacion"] for i in propios if i.get("puntuacion") is not None]
        estrellas = [i["estrellas"] for i in propios if i.get("estrellas") is not None]
        mejor_punt = max(puntuaciones) if puntuaciones else None
        mejor_est = max(estrellas) if estrellas else None
        estado = "nueva"
        if propios:
            estado = "dominada" if (mejor_est == 3 or (mejor_punt or 0) >= 85) else "aprendiendo"
        resultado.append({
            "song_id": cid,
            "titulo": item.get("titulo", ""),
            "artista": item.get("artista", ""),
            "favorita": bool(item.get("favorita")),
            "intentos": len(propios),
            "mejor_puntuacion": mejor_punt,
            "mejores_estrellas": mejor_est,
            "estado": estado,
        })
    # Primero las que están en curso, luego nuevas, luego dominadas.
    orden = {"aprendiendo": 0, "nueva": 1, "dominada": 2}
    return sorted(resultado, key=lambda c: orden.get(c["estado"], 3))


# --------------------------------------------------------------------------
# Construcción y acceso
# --------------------------------------------------------------------------

def reconstruir_perfil(user_id: str) -> dict | None:
    """Reconstruye y persiste el perfil de aprendizaje. None si no hay usuario."""
    usuario = usuarios.find_one({"user_id": user_id})
    if usuario is None:
        return None

    ahora = _ahora()
    doc_hab = habilidades_dominio.obtener_habilidades(user_id)
    senales = motor.recopilar_senales(user_id)
    intentos = list(
        intentos_ejercicio.find({"usuario": user_id}, {"_id": 0}).sort("fecha", -1).limit(200)
    )

    evidencia = _evidencia_por_habilidad(intentos)
    habilidades_resumen = []
    for slug in habilidades_dominio.HABILIDADES:
        hab = doc_hab["habilidades"][slug]
        n = evidencia.get(slug, 0)
        conf_ev = _confianza_evidencia(n)
        habilidades_resumen.append({
            "id": slug,
            "nombre": habilidades_dominio.NOMBRES[slug],
            "nivel": int(hab.get("nivel", 0)),
            "progreso": float(hab.get("progreso", 0)),
            "confianza_recencia": float(hab.get("confianza", 0)),
            "muestras": n,
            "confianza_evidencia": conf_ev,
            "evidencia": _etiqueta_evidencia(conf_ev),
        })

    con_punt = [i for i in intentos if i.get("puntuacion") is not None]
    promedio = round(sum(i["puntuacion"] for i in con_punt) / len(con_punt), 1) if con_punt else None
    xp_total = sum(int(i.get("xp_ganado", 0) or 0) for i in intentos)

    tendencia = None
    if len(con_punt) >= 4:
        recientes = sum(i["puntuacion"] for i in con_punt[:3]) / 3
        previos = sum(i["puntuacion"] for i in con_punt[3:]) / len(con_punt[3:])
        tendencia = ("mejorando" if recientes > previos + 5
                     else "bajando" if recientes < previos - 5 else "estable")

    canciones_bib = list(biblioteca_usuario.find({"usuario": user_id}, {"_id": 0, "song_id": 1}))

    perfil = {
        "usuario": user_id,
        "version": VERSION_PERFIL,
        "actualizado": ahora.isoformat(),
        "nombre": usuario.get("nombre"),
        "nivel": usuario.get("nivel", "principiante"),
        "preferencias": _preferencias(usuario, canciones_bib),
        "habilidades": habilidades_resumen,
        "estilo": _estilo_practica(intentos, ahora),
        "desempeno": {
            "total_intentos": len(intentos),
            "racha": senales["racha"],
            "minutos_hoy": senales["minutos_hoy"],
            "promedio_puntuacion": promedio,
            "tendencia": tendencia,
            "xp_total": xp_total,
        },
        "canciones": _canciones_aprendiendo(user_id, intentos),
        # Los llena Progress Intelligence (MC2); se preservan si ya existen.
        "hitos_recientes": (perfil_aprendizaje.find_one(
            {"usuario": user_id}, {"hitos_recientes": 1}
        ) or {}).get("hitos_recientes", []),
    }

    perfil_aprendizaje.update_one(
        {"usuario": user_id}, {"$set": perfil}, upsert=True
    )
    return perfil


def obtener_perfil(user_id: str, max_edad_min: int = 60) -> dict | None:
    """Perfil del usuario; se reconstruye si no existe o está viejo.

    El hook de /practica lo mantiene fresco; este umbral cubre lecturas de
    usuarios que llevan tiempo sin practicar (decaimientos, racha).
    """
    doc = perfil_aprendizaje.find_one({"usuario": user_id}, {"_id": 0})
    if doc is not None:
        edad = _ahora() - (_fecha(doc.get("actualizado")) or _ahora())
        if edad < timedelta(minutes=max_edad_min):
            return doc
    return reconstruir_perfil(user_id)
