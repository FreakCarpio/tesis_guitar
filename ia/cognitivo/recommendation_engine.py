"""
Recommendation Engine (MC5) - Planes diario y semanal personalizados.

Determinístico y estable: el plan del día se genera una vez y se persiste
en `planes` (clave usuario+fecha local); consultarlo de nuevo devuelve el
mismo plan (pedagógicamente importa que la meta no cambie a cada rato).
El plan semanal es estable por semana ISO.

Plan diario = calentamiento (si aún no practicó) + la recomendación del
Adaptive Engine v2 + su canción en aprendizaje (si la hay), con duración
total y XP potencial. Plan semanal = focos por día construidos desde las
debilidades con evidencia, el paso del camino y sus canciones.
"""

from datetime import datetime, timedelta, timezone

from database import planes
from domain import ejercicios as ejercicios_dominio
from domain import habilidades as habilidades_dominio
from ia import motor_config as cfg
from ia.cognitivo import adaptive_engine, learning_profile


def _hoy_local(offset_min: int):
    return (datetime.now(timezone.utc) + timedelta(minutes=offset_min)).date()


def _xp_de(ejercicio: dict) -> int:
    return sum(int(p.get("xp", 0) or 0) for p in ejercicio.get("pasos", []))


def _item(orden: int, ejercicio: dict, razon: str, cancion: dict | None = None) -> dict:
    return {
        "orden": orden,
        "tipo": "cancion" if cancion else "ejercicio",
        "ejercicio_id": ejercicio["id"],
        "titulo": cancion["titulo"] if cancion else ejercicio["nombre"],
        "emoji": ejercicio.get("emoji", "🎸"),
        "cancion_id": cancion["song_id"] if cancion else None,
        "duracion_min": ejercicio["duracion_min"],
        "xp_potencial": _xp_de(ejercicio),
        "razon": razon,
        "completado": False,
    }


def plan_diario(user_id: str, offset_min: int = 0, regenerar: bool = False) -> dict | None:
    """Plan del día (estable). None si el usuario no existe."""
    hoy = _hoy_local(offset_min)
    clave = f"diario|{user_id}|{hoy.isoformat()}"

    if not regenerar:
        existente = planes.find_one({"clave": clave}, {"_id": 0})
        if existente is not None:
            return existente

    decision = adaptive_engine.decidir(user_id, offset_min=offset_min, persistir=False)
    if decision is None:
        return None
    perfil = learning_profile.obtener_perfil(user_id) or {}
    rec = decision["recomendacion"]

    items: list[dict] = []
    if rec["tipo"] == "descanso":
        items.append({
            "orden": 1, "tipo": "descanso", "ejercicio_id": None,
            "titulo": "Descanso merecido", "emoji": "🌙", "cancion_id": None,
            "duracion_min": 0, "xp_potencial": 0,
            "razon": rec["razon"], "completado": False,
        })
    else:
        orden = 1
        # 1) Calentamiento si aún no practicó hoy.
        if (perfil.get("desempeno") or {}).get("minutos_hoy", 0) == 0:
            cal = ejercicios_dominio.obtener_ejercicio("calentamiento")
            items.append(_item(orden, cal, "Activa dedos y muñecas antes de exigir."))
            orden += 1

        # 2) El corazón del día: la recomendación del motor v2.
        ejercicio = decision.get("ejercicio") or ejercicios_dominio.obtener_ejercicio(
            rec.get("ejercicio_id") or "practica_general"
        )
        cancion = None
        if rec.get("cancion_id") is not None:
            cancion = next(
                (c for c in perfil.get("canciones", [])
                 if c["song_id"] == rec["cancion_id"]),
                None,
            )
        items.append(_item(orden, ejercicio, rec["razon"], cancion))
        orden += 1

        # 3) Su canción en aprendizaje, si no fue ya el ítem central.
        if cancion is None:
            en_curso = next(
                (c for c in perfil.get("canciones", []) if c["estado"] == "aprendiendo"),
                None,
            )
            if en_curso is not None:
                ej_cancion = ejercicios_dominio.obtener_ejercicio("primera_cancion")
                items.append(_item(
                    orden, ej_cancion,
                    f"Sigue con «{en_curso['titulo']}»: cada pasada suma.",
                    en_curso,
                ))

    plan = {
        "clave": clave,
        "usuario": user_id,
        "tipo": "diario",
        "fecha": hoy.isoformat(),
        "items": items,
        "duracion_total_min": sum(i["duracion_min"] for i in items),
        "xp_potencial": sum(i["xp_potencial"] for i in items),
        "meta_min": cfg.META_DIARIA_MIN,
        "generado": datetime.now(timezone.utc).isoformat(),
    }
    planes.update_one({"clave": clave}, {"$set": plan}, upsert=True)
    return plan


def plan_semanal(user_id: str, offset_min: int = 0, regenerar: bool = False) -> dict | None:
    """Plan de la semana ISO en curso (estable). None si no hay usuario."""
    hoy = _hoy_local(offset_min)
    iso = hoy.isocalendar()
    clave = f"semanal|{user_id}|{iso[0]}-W{iso[1]:02d}"

    if not regenerar:
        existente = planes.find_one({"clave": clave}, {"_id": 0})
        if existente is not None:
            return existente

    perfil = learning_profile.obtener_perfil(user_id)
    if perfil is None:
        return None

    # Focos: debilidades con evidencia primero, luego las 3 más flojas del
    # perfil, consolidación de la fuerte y su canción en aprendizaje.
    analisis = perfil.get("analisis", {})
    focos: list[str] = [d["id"] for d in analisis.get("debilidades", [])]
    for h in sorted(perfil.get("habilidades", []), key=lambda x: x["nivel"] + x["progreso"]):
        if h["id"] not in focos:
            focos.append(h["id"])
    fuerte = next((f["id"] for f in analisis.get("fortalezas", [])), None)

    cancion = next(
        (c for c in perfil.get("canciones", []) if c["estado"] in ("aprendiendo", "nueva")),
        None,
    )

    lunes = hoy - timedelta(days=hoy.weekday())
    dias = []
    for i in range(7):
        fecha = lunes + timedelta(days=i)
        if i == 6:
            dias.append({"fecha": fecha.isoformat(), "dia": i + 1, "foco": "descanso",
                         "titulo": "Descanso / toca libre", "ejercicio_id": None,
                         "cancion_id": None, "duracion_min": 0})
            continue
        if i == 5 and cancion is not None:
            dias.append({"fecha": fecha.isoformat(), "dia": i + 1, "foco": "cancion",
                         "titulo": f"Canción: {cancion['titulo']}",
                         "ejercicio_id": "primera_cancion",
                         "cancion_id": cancion["song_id"],
                         "duracion_min": 15})
            continue
        if i == 4 and fuerte is not None:
            slug = fuerte
        else:
            slug = focos[i % len(focos)] if focos else "precision"
        ejercicio = ejercicios_dominio.ejercicio_para_habilidad(slug, 2)
        dias.append({
            "fecha": fecha.isoformat(), "dia": i + 1, "foco": slug,
            "titulo": f"{habilidades_dominio.NOMBRES.get(slug, slug)} · {ejercicio['nombre']}",
            "ejercicio_id": ejercicio["id"], "cancion_id": None,
            "duracion_min": ejercicio["duracion_min"],
        })

    plan = {
        "clave": clave,
        "usuario": user_id,
        "tipo": "semanal",
        "semana": f"{iso[0]}-W{iso[1]:02d}",
        "dias": dias,
        "meta_minutos": cfg.META_DIARIA_MIN * 6,
        "meta_xp": 300,
        "generado": datetime.now(timezone.utc).isoformat(),
    }
    planes.update_one({"clave": clave}, {"$set": plan}, upsert=True)
    return plan
