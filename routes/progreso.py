"""
Progreso - Endpoint de lectura del progreso real del usuario.

Todo se calcula desde MongoDB (colecciones `sesiones`, `progreso`, `usuarios`):
- total de sesiones y minutos practicados (hoy y acumulados)
- precisión y consistencia promedio (agregación sobre sesiones reales)
- racha de días consecutivos con práctica
- historial de las últimas sesiones (para gráficos)

Un usuario nuevo sin sesiones devuelve todo en cero: no hay datos inventados.
"""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from database import progreso, sesiones, usuarios

router = APIRouter(prefix="/progreso", tags=["progreso"])


def _parse_fecha(valor) -> date | None:
    """Convierte el campo `fecha` de una sesión (ISO string) a date, si existe."""
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor)).date()
    except ValueError:
        return None


def _racha_dias(dias_con_practica: set[date], hoy: date) -> int:
    """Días consecutivos con práctica contando hacia atrás desde hoy.

    Si hoy aún no se practicó, la racha sigue viva si se practicó ayer
    (comportamiento estándar tipo Duolingo).
    """
    if not dias_con_practica:
        return 0
    inicio = hoy if hoy in dias_con_practica else hoy - timedelta(days=1)
    if inicio not in dias_con_practica:
        return 0
    racha = 0
    dia = inicio
    while dia in dias_con_practica:
        racha += 1
        dia -= timedelta(days=1)
    return racha


@router.get("/{user_id}")
async def get_progreso(user_id: str):
    """Devuelve el progreso real agregado del usuario desde MongoDB."""
    usuario = usuarios.find_one({"user_id": user_id})
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    docs = list(sesiones.find({"usuario": user_id}).sort("_id", 1))
    hoy = datetime.now(timezone.utc).date()

    total_sesiones = len(docs)
    precisiones = [float(d.get("precision", 0) or 0) for d in docs]
    consistencias = [float(d.get("consistencia", 0) or 0) for d in docs]
    precision_prom = sum(precisiones) / total_sesiones if total_sesiones else 0.0
    consistencia_prom = sum(consistencias) / total_sesiones if total_sesiones else 0.0

    minutos_totales = 0.0
    minutos_hoy = 0.0
    dias_con_practica: set[date] = set()
    for d in docs:
        fecha = _parse_fecha(d.get("fecha"))
        minutos = float(d.get("duracion_seg", 0) or 0) / 60.0
        minutos_totales += minutos
        if fecha is not None:
            dias_con_practica.add(fecha)
            if fecha == hoy:
                minutos_hoy += minutos

    prog = progreso.find_one({"usuario": user_id}) or {}

    historial = [
        {
            "fecha": d.get("fecha"),
            "ejercicio": d.get("ejercicio", "practica_general"),
            "precision": round(float(d.get("precision", 0) or 0), 4),
            "consistencia": round(float(d.get("consistencia", 0) or 0), 4),
            "duracion_seg": int(d.get("duracion_seg", 0) or 0),
        }
        for d in docs[-7:]
    ]

    return {
        "user_id": user_id,
        "nivel": usuario.get("nivel", "principiante"),
        "sesiones": total_sesiones,
        "precision_promedio": round(precision_prom, 4),
        "consistencia_promedio": round(consistencia_prom, 4),
        "racha_dias": _racha_dias(dias_con_practica, hoy),
        "minutos_hoy": round(minutos_hoy, 1),
        "minutos_totales": round(minutos_totales, 1),
        "ejercicios_completados": int(prog.get("ejercicios_completados", 0) or 0),
        "ultima_practica": prog.get("ultima_practica"),
        "historial": historial,
    }
