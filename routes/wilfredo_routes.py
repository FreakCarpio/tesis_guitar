"""
wilfredo routes - aqui定义 los endpoints sin ia externa
"""
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from services.wilfredo_service import (
    generate_chat_response,
    evaluate_user_level,
    analyze_tuner_feedback,
    analyze_chord_feedback,
    generate_practice_feedback,
    generate_practice_plan
)

router = APIRouter(prefix="/wilfredo", tags=["wilfredo"])

# modelo para el chat
class ChatRequest(BaseModel):
    mensaje: str
    nivel: str = "principiante"
    historial: list = []


@router.post("/chat")
async def wilfredo_chat(req: ChatRequest):
    """chat con wilfredo - sin api externa"""
    nivel_detectado = evaluate_user_level(req.mensaje)
    if nivel_detectado != "principiante":
        nivel = nivel_detectado
    
    respuesta = generate_chat_response(req.mensaje, nivel)
    
    return {"respuesta": respuesta, "nivel": nivel}


@router.post("/analyze")
async def wilfredo_analyze(metricas: dict):
    """analiza métricas y da feedback"""
    feedback = generate_practice_feedback(metricas)
    return {"feedback": feedback}


@router.post("/plan")
async def wilfredo_plan(nivel: str = "principiante", objetivo: str = None):
    """genera plan de práctica"""
    plan = generate_practice_plan(nivel, objetivo)
    return {"plan": plan}


@router.post("/tuner")
async def wilfredo_tuner(frecuencia: float, nota: str, cents: float):
    """feedback del afinador"""
    feedback = analyze_tuner_feedback(frecuencia, nota, cents)
    return {"feedback": feedback, "nota": nota, "cents": cents}


@router.post("/chord")
async def wilfredo_chord(acorde: dict):
    """feedback del acorde"""
    feedback = analyze_chord_feedback(acorde)
    return {"feedback": feedback, "acorde": acorde}