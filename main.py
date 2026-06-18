"""
Main - Punto de entrada de la aplicación FastAPI
Sirve cómo API REST para la aplicación de guitarra Wilfredo

Autor: Tesis App
Fecha: 2026
"""

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from domain.modelo import UserProfile
from ia.modelo_adaptativo import modelo_adaptativo
from analizador_señales.señal import SignalAnalyzer
from routes.practicas import router as practicas_router
from routes.wilfredo_routes import router as wilfredo_router
from routes.tuner import router as tuner_router
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

model = modelo_adaptativo()
analyzer = SignalAnalyzer()

profiles = {}


@app.post("/practica")
async def practice(user_id: str, file: UploadFile = File(...)):

     # ----------------------------------------------------------------------
    # Verificación de usuario
    # Si el usuario no existe en la base de datos se crea automáticamente
    # con valores iniciales para su perfil de aprendizaje
    # ----------------------------------------------------------------------
    usuario = usuarios.find_one({"user_id": user_id})

    if usuario is None:

     nuevo_usuario = {
        "user_id": user_id,
        "nivel": "principiante",
        "precision": 0,
        "sesiones": 0
    }

    usuarios.insert_one(nuevo_usuario)
     # ----------------------------------------------------------------------
    # Almacenamiento temporal del archivo de audio recibido
    # El audio se guarda localmente para ser procesado por el analizador
    # ----------------------------------------------------------------------

    filepath = f"temp_{file.filename}"

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

 # ----------------------------------------------------------------------
    # Análisis de audio
    # Se obtienen métricas de precisión, consistencia y error
    # ----------------------------------------------------------------------
    metrics = analyzer.analyze_file(filepath)

    os.remove(filepath)

    precision = metrics["precision"]
     # ----------------------------------------------------------------------
    # Actualización de datos generales del usuario
    # Se registra la nueva precisión obtenida y se incrementa el número
    # total de sesiones realizadas
    # ----------------------------------------------------------------------
    usuarios.update_one(
    {"user_id": user_id},
    {
        "$set": {
            "precision": precision
        },
        "$inc": {
            "sesiones": 1
        }
    }
)
    consistencia = metrics["consistencia"]
    error = metrics["error"]
    
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
        "$inc": {
            "ejercicios_completados": 1
        },

        "$set": {
            "ultima_practica": "2026-06-18"
        }
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
        "$inc": {
            "total_horas_practica": 1
        },

        "$set": {
            "precision_promedio": precision
        }
    },

    upsert=True

)

   # ----------------------------------------------------------------------
    # IA Adaptativa
    # Actualiza el perfil del usuario con base en los resultados obtenidos
    # para personalizar futuras recomendaciones y ejercicios
    # ----------------------------------------------------------------------
    profiles[user_id] = model.update(
        profiles[user_id],
        precision,
        consistencia,
        error
    )

    return {
        "metrics": metrics,
        "profile": profiles[user_id]
    }
    
