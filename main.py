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
from datetime import date
from domain.modelo import UserProfile
from ia.modelo_adaptativo import modelo_adaptativo
from analizador_señales.señal import SignalAnalyzer
from audio.metricas_extractor import MetricsExtractor
from routes.practicas import router as practicas_router
from routes.wilfredo_routes import router as wilfredo_router
from routes.tuner import router as tuner_router
from routes.auth import router as auth_router
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

model = modelo_adaptativo()
analyzer = SignalAnalyzer()
extractor = MetricsExtractor()

# Perfiles adaptativos en memoria por usuario.
# NOTA: estado en RAM; se pierde al reiniciar y no es seguro en multi-worker.
# Para persistencia real habría que serializar UserProfile en MongoDB (ver reporte).
profiles = {}


@app.post("/practica")
async def practice(user_id: str, file: UploadFile = File(...)):
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
    sesiones.insert_one({
        "usuario": user_id,
        "ejercicio": "practica_general",
        "precision": precision,
        "consistencia": consistencia,
        "error": error
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
    # Guarda información acumulada sobre el desempeño del usuario
    # ----------------------------------------------------------------------
    estadisticas.update_one(
        {"usuario": user_id},
        {
            "$inc": {"total_horas_practica": 1},
            "$set": {"precision_promedio": precision}
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

    return {
        "metrics": metrics,
        "profile": profiles[user_id]
    }
