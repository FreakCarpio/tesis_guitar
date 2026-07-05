"""
Main - Punto de entrada de la aplicación FastAPI
Sirve cómo API REST para la aplicación de guitarra Wilfredo

Autor: Tesis App
Fecha: 2026
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import tempfile
import math
from datetime import date, datetime, timezone
from domain.modelo import UserProfile
from ia.modelo_adaptativo import modelo_adaptativo
from analizador_señales.señal import SignalAnalyzer
from audio.metricas_extractor import MetricsExtractor
from routes.practicas import router as practicas_router
from routes.wilfredo_routes import router as wilfredo_router
from routes.tuner import router as tuner_router
from routes.auth import router as auth_router
from routes.progreso import router as progreso_router
from routes.habilidades import router as habilidades_router
from routes.camino import router as camino_router
from routes.entrenador import router as entrenador_router
from domain import ejercicios as ejercicios_dominio
from domain import habilidades as habilidades_dominio
from domain import camino as camino_dominio
# --------------------------------------------------------------------------
# Importación de colecciones MongoDB
# Permiten almacenar información persistente de usuarios, sesiones,
# progreso y estadísticas de práctica
# --------------------------------------------------------------------------
from database import (
    usuarios,
    sesiones,
    progreso,
    estadisticas
)

app = FastAPI(
    title="Wilfredo - API de Guitarra",
    description="API REST para tutor inteligente de guitarra. Sin APIs externas, todo con lógica basada en reglas.",
    version="1.0.0"
)

# --------------------------------------------------------------------------
# CORS - Configuración para permite desde Android/Kotlin
# Este middleware permite que la aplicación móvil en Kotlin pueda consumir
# los endpoints sin problemas de origen cruzado
# --------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios específicos
    allow_credentials=True,
    allow_methods=["*"],  # Métodos permitidos: GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Todos los headers
)

# Se incluyen los routers para mantener las rutas existentes
# cada router tiene su propio prefijo definido en su archivo
app.include_router(practicas_router)
app.include_router(wilfredo_router)
app.include_router(tuner_router)
app.include_router(auth_router)
app.include_router(progreso_router)
app.include_router(habilidades_router)
app.include_router(camino_router)
app.include_router(entrenador_router)

model = modelo_adaptativo()
analyzer = SignalAnalyzer()
extractor = MetricsExtractor()

# Perfiles adaptativos en memoria por usuario.
# NOTA: estado en RAM; se pierde al reiniciar y no es seguro en multi-worker.
# Para persistencia real habría que serializar UserProfile en MongoDB (ver reporte).
profiles = {}


@app.post("/practica")
async def practice(
    user_id: str,
    file: UploadFile = File(...),
    duracion_seg: int = 0,
    ejercicio: str = "practica_general",
):
    """
    Registra una sesión de práctica completa:
    1. Crea el usuario si no existe.
    2. Analiza el audio (precisión, consistencia, error) de forma headless.
    3. Persiste usuario, sesión, progreso y estadísticas en MongoDB.
    4. Actualiza el perfil adaptativo del usuario.
    """
    # ----------------------------------------------------------------------
    # Verificación de usuario
    # Si el usuario no existe en la base de datos se crea automáticamente
    # con valores iniciales para su perfil de aprendizaje
    # ----------------------------------------------------------------------
    usuario = usuarios.find_one({"user_id": user_id})
    if usuario is None:
        usuarios.insert_one({
            "user_id": user_id,
            "nivel": "principiante",
            "precision": 0,
            "sesiones": 0
        })

    # ----------------------------------------------------------------------
    # Almacenamiento temporal del archivo de audio recibido
    # Se usa tempfile para no depender de rutas fijas en el CWD; en un entorno
    # Linux efímero (Railway) el archivo vive en el directorio temporal del SO.
    # ----------------------------------------------------------------------
    suffix = os.path.splitext(file.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as buffer:
        shutil.copyfileobj(file.file, buffer)
        filepath = buffer.name

    # ----------------------------------------------------------------------
    # Análisis de audio (headless, sin micrófono)
    # Se carga con librosa y se evalúa con MetricsExtractor contra el
    # semitono más cercano a la frecuencia detectada, obteniendo
    # precisión (afinación), consistencia (estabilidad) y error (Hz).
    # ----------------------------------------------------------------------
    try:
        y = analyzer.load_audio(filepath)
        freq, _conf, _harm = extractor.detect_pitch(y, analyzer.sr)
        if freq is None or freq <= 0:
            raise HTTPException(status_code=422, detail="No se detectó señal de audio válida en la grabación.")
        # Semitono (nota) más cercano como objetivo de referencia
        target_freq = 440.0 * 2 ** (round(12 * math.log2(freq / 440.0)) / 12)
        metrics = extractor.evaluate_sequence(y, analyzer.sr, target_freq)
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    precision = metrics["precision"]
    consistencia = metrics["consistencia"]
    error = metrics["error"]

    # ----------------------------------------------------------------------
    # Actualización de datos generales del usuario
    # Se registra la nueva precisión obtenida y se incrementa el número
    # total de sesiones realizadas
    # ----------------------------------------------------------------------
    usuarios.update_one(
        {"user_id": user_id},
        {
            "$set": {"precision": precision},
            "$inc": {"sesiones": 1}
        }
    )

    # ----------------------------------------------------------------------
    # Registro de sesión de práctica
    # Guarda los resultados individuales obtenidos durante la ejecución
    # ----------------------------------------------------------------------
    sesion_result = sesiones.insert_one({
        "usuario": user_id,
        "ejercicio": ejercicio,
        "precision": precision,
        "consistencia": consistencia,
        "error": error,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "duracion_seg": max(duracion_seg, 0)
    })

    # ----------------------------------------------------------------------
    # Actualización de progreso del usuario
    # Se incrementa el contador de ejercicios completados y se registra
    # la fecha de la última práctica
    # ----------------------------------------------------------------------
    progreso.update_one(
        {"usuario": user_id},
        {
            "$inc": {"ejercicios_completados": 1},
            "$set": {"ultima_practica": date.today().isoformat()}
        },
        upsert=True
    )

    # ----------------------------------------------------------------------
    # Actualización de estadísticas generales
    # precision_promedio es el promedio REAL sobre todas las sesiones del
    # usuario (agregación en Mongo), no la última precisión obtenida.
    # ----------------------------------------------------------------------
    agg = list(sesiones.aggregate([
        {"$match": {"usuario": user_id}},
        {"$group": {"_id": None, "avg_precision": {"$avg": "$precision"}}}
    ]))
    precision_promedio = agg[0]["avg_precision"] if agg else precision

    estadisticas.update_one(
        {"usuario": user_id},
        {
            "$inc": {"minutos_practica": round(max(duracion_seg, 0) / 60.0, 2)},
            "$set": {"precision_promedio": precision_promedio}
        },
        upsert=True
    )

    # ----------------------------------------------------------------------
    # IA Adaptativa
    # Actualiza el perfil del usuario con base en los resultados obtenidos
    # para personalizar futuras recomendaciones y ejercicios
    # ----------------------------------------------------------------------
    if user_id not in profiles:
        profiles[user_id] = UserProfile()
    profiles[user_id] = model.update(profiles[user_id], precision, consistencia, error)

    # ----------------------------------------------------------------------
    # Sistema adaptativo P1 (aditivo y best-effort)
    # Evalúa criterios de aprobación del ejercicio y actualiza las
    # habilidades correspondientes. Si algo falla aquí, la sesión ya quedó
    # persistida arriba: nunca se pierde una práctica por el motor.
    # ----------------------------------------------------------------------
    adaptativo = _actualizar_adaptativo(
        user_id, ejercicio, precision, consistencia,
        max(duracion_seg, 0), str(sesion_result.inserted_id)
    )

    return {
        "metrics": metrics,
        "profile": profiles[user_id],
        **adaptativo,
    }


def _actualizar_adaptativo(user_id, ejercicio_id, precision, consistencia,
                           duracion_seg, sesion_id) -> dict:
    """Actualiza habilidades y camino tras la práctica (P1). Nunca lanza."""
    vacio = {
        "aprobado": None, "criterios": None,
        "habilidades_actualizadas": [], "subio_nivel": False,
        "paso_completado": None,
    }
    try:
        ej = ejercicios_dominio.obtener_ejercicio(ejercicio_id)
        crit = ej["criterios"]
        aprobado = (
            precision >= crit["precision_min"]
            and consistencia >= crit["consistencia_min"]
            and duracion_seg >= crit["duracion_min_seg"]
        )

        # Estado del camino ANTES, para detectar un paso recién completado.
        camino_antes = camino_dominio.obtener_camino(user_id)
        completados_antes = {
            p["id"] for p in camino_antes["pasos"] if p["estado"] == "completado"
        } if camino_antes else set()

        actualizaciones = habilidades_dominio.aplicar_practica(
            user_id,
            habilidad_principal=ej["habilidad"],
            habilidades_secundarias=ej.get("secundarias", []),
            precision=precision,
            consistencia=consistencia,
            dificultad=ej["dificultad"],
            aprobado=aprobado,
            sesion_id=sesion_id,
        )

        camino_despues = camino_dominio.obtener_camino(user_id)
        completados_despues = {
            p["id"] for p in camino_despues["pasos"] if p["estado"] == "completado"
        } if camino_despues else set()
        nuevos = completados_despues - completados_antes
        paso_completado = None
        if nuevos:
            paso = camino_dominio.paso_por_id(next(iter(nuevos)))
            paso_completado = {"id": paso["id"], "nombre": paso["nombre"]} if paso else None

        return {
            "aprobado": aprobado,
            "criterios": crit,
            "habilidades_actualizadas": actualizaciones,
            "subio_nivel": any(a["subio_nivel"] for a in actualizaciones),
            "paso_completado": paso_completado,
        }
    except Exception:
        return vacio
