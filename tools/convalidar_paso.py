"""
Convalida un paso del camino para un usuario existente (one-shot, auditable).

Uso:
    python tools/convalidar_paso.py --email correo@ejemplo.com [--paso afinacion]

Qué hace (sin tocar el flujo normal de nadie más):
1. Busca el usuario por email en `usuarios` (identidad = sub de Google).
2. Sube la habilidad del paso al nivel exigido por sus criterios de salida
   (solo si el nivel actual es menor: idempotente y nunca degrada).
3. Registra el ajuste en `habilidad_eventos` con motivo `convalidacion_manual`
   para que el historial siga siendo auditable.
4. Recalcula el camino (el estado se DERIVA de habilidades, igual que
   siempre) y muestra el resultado: paso completado + siguiente desbloqueado.

Los usuarios nuevos siguen empezando desde cero: esto solo escribe el estado
del usuario indicado, por la misma vía de dominio que usa la app.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import usuarios, habilidades, habilidad_eventos  # noqa: E402
from domain import camino as camino_dominio                    # noqa: E402
from domain import habilidades as habilidades_dominio          # noqa: E402
from ia import motor_config as cfg                             # noqa: E402


def convalidar(email: str, paso_id: str) -> int:
    paso = camino_dominio.paso_por_id(paso_id)
    if paso is None:
        print(f"ERROR: paso desconocido '{paso_id}'.")
        return 1

    usuario = usuarios.find_one({"email": email})
    if usuario is None:
        print(f"ERROR: no existe un usuario con email {email}.")
        return 1
    user_id = usuario["user_id"]
    print(f"Usuario: {usuario.get('nombre') or email} (user_id={user_id})")

    doc = habilidades_dominio.obtener_habilidades(user_id)
    if doc is None:
        print("ERROR: el usuario no tiene documento de habilidades.")
        return 1

    ahora = datetime.now(timezone.utc).isoformat()
    eventos = []
    cambios = False

    for slug, nivel_min in paso["criterios_salida"].items():
        hab = doc["habilidades"].get(slug)
        if hab is None:
            print(f"ERROR: habilidad desconocida '{slug}'.")
            return 1
        if hab["nivel"] >= nivel_min:
            print(f"- {slug}: nivel {hab['nivel']} ya cumple el criterio ({nivel_min}). Sin cambios.")
            continue
        nivel_previo = hab["nivel"]
        hab["nivel"] = nivel_min
        hab["progreso"] = 0.0
        hab["confianza"] = round(
            max(float(hab.get("confianza") or 0.0), cfg.CONFIANZA_INICIAL_SEMILLA), 4
        )
        hab["ultima_practica"] = ahora
        cambios = True
        eventos.append({
            "usuario": user_id,
            "habilidad": slug,
            "sesion_id": None,
            "fecha": ahora,
            "delta_progreso": 0.0,
            "nivel_resultante": hab["nivel"],
            "progreso_resultante": 0.0,
            "confianza_resultante": hab["confianza"],
            "subio_nivel": True,
            "motivo": "convalidacion_manual",
            "detalle": (
                f"Paso '{paso_id}' convalidado por el operador: "
                f"nivel {nivel_previo} -> {nivel_min}."
            ),
        })
        print(f"- {slug}: nivel {nivel_previo} -> {nivel_min} (convalidado)")

    if cambios:
        habilidades.update_one(
            {"usuario": user_id},
            {"$set": {"habilidades": doc["habilidades"], "actualizado": ahora}},
        )
        habilidad_eventos.insert_many(eventos)

    # El camino se deriva de habilidades: leerlo registra la fecha de
    # completado y nos deja verificar el desbloqueo del siguiente paso.
    camino = camino_dominio.obtener_camino(user_id)
    print(f"\nCamino de {email}:")
    for p in camino["pasos"]:
        marca = {"completado": "[x]", "en_curso": "[>]", "disponible": "[ ]"}.get(p["estado"], "[#]")
        print(f"  {marca} {p['nombre']:<20} {p['estado']}")
    print(f"\nPaso actual: {camino['paso_actual']} | completados: {camino['completados']}/{camino['total_pasos']}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convalida un paso del camino para un usuario.")
    parser.add_argument("--email", required=True, help="Email del usuario (colección usuarios)")
    parser.add_argument("--paso", default="afinacion", help="Id del paso del camino (default: afinacion)")
    args = parser.parse_args()
    raise SystemExit(convalidar(args.email, args.paso))
