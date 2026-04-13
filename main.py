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

    # crear perfil si no existe
    if user_id not in profiles:
        profiles[user_id] = UserProfile()

    filepath = f"temp_{file.filename}"

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # -------- ANALISIS DE AUDIO --------
    metrics = analyzer.analyze_file(filepath)

    os.remove(filepath)

    precision = metrics["precision"]
    consistencia = metrics["consistencia"]
    error = metrics["error"]

    # -------- IA ADAPTATIVA --------
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