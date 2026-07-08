"""
Wilfredo Routes - Endpoints del tutor inteligente de guitarra

Este módulo define los endpoints REST para la funcionalidad de Wilfredo:
- Chat interactivo
- Análisis de práctica
- Planes de práctica
- Feedback de afinador
- Feedback de acordes

NO usa APIs externas (OpenAI, Gemini) - todo con lógica basada en reglas.

Compatible con consumo desde Kotlin/Android vía Retrofit.

Autor: Tesis App
Fecha: 2026
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from services.wilfredo_service import (
    generate_chat_response,
    evaluate_user_level,
    analyze_tuner_feedback,
    analyze_chord_feedback,
    generate_practice_feedback,
    generate_practice_plan
)

# Se crea el router con prefijo /wilfredo para todas las rutas
# Esto significa que todos los endpoints starts con /wilfredo/
# Ejemplo: /wilfredo/chat, /wilfredo/analyze, etc.
router = APIRouter(prefix="/wilfredo", tags=["wilfredo"])


# ==============================================================================
# MODELOS PYDANTIC - Definen la estructura de datos de entrada y salida
# Estos modelos aseguran que los datos que llegan desde Kotlin/Android
# sean válidos y tengan el formato correcto
# ==============================================================================

class ChatRequest(BaseModel):
    """
    Solicitud para el endpoint de chat
    
    Parámetros:
    - mensaje: El texto que el usuario quiere enviar
    - nivel: Nivel del usuario (principiante, intermedio, avanzado)
    - historial: Historial de mensajes anteriores (opcional)
    """
    mensaje: str = Field(..., description="Mensaje del usuario")
    nivel: str = Field(default="principiante", description="Nivel del usuario")
    historial: List[str] = Field(default_factory=list, description="Historial de mensajes")
    # P1.6: con user_id Wilfredo responde como TUTOR con memoria del
    # desempeño real del usuario. Sin user_id: comportamiento clásico.
    user_id: Optional[str] = Field(default=None, description="Usuario para respuestas personalizadas")


class AnalyzeRequest(BaseModel):
    """
    Solicitud para análisis de práctica
    
    Parámetros:
    - precision: Precisión de la ejecución (0.0 a 1.0)
    - ritmo: Consistencia del ritmo (0.0 a 1.0)
    - bpm: Beats por minuto
    - nota: Nota que se estaba tocando (opcional)
    """
    precision: float = Field(..., description="Precisión de 0.0 a 1.0", ge=0.0, le=1.0)
    ritmo: float = Field(default=0.0, description="Ritmo/consistencia de 0.0 a 1.0", ge=0.0, le=1.0)
    bpm: int = Field(default=120, description="Beats por minuto", ge=40, le=240)
    nota: Optional[str] = Field(default=None, description="Nota tocada")


class PlanRequest(BaseModel):
    """
    Solicitud para generar plan de práctica
    
    Parámetros:
    - nivel: Nivel actual del usuario
    - objetivo: Área específica a trabajar (opcional)
    """
    nivel: str = Field(default="principiante", description="Nivel del usuario")
    objetivo: Optional[str] = Field(default=None, description="Objetivo específico")


class TunerFeedbackRequest(BaseModel):
    """
    Solicitud para feedback del afinador
    
    Parámetros:
    - frecuencia: Frecuencia detectada en Hz
    - nota: Nota musical detectada (ej: A4, E2)
    - cents: Diferencia en cents (-50 a +50)
    """
    frecuencia: float = Field(..., description="Frecuencia en Hz", ge=20, le=5000)
    nota: str = Field(..., description="Nota musical (ej: A4, E2)")
    cents: float = Field(..., description="Diferencia en cents (-50 a +50)", ge=-50, le=50)


class ChordFeedbackRequest(BaseModel):
    """
    Solicitud para feedback de acorde
    
    Parámetros:
    - notas: Lista de notas detectadas en el acorde
    """
    notas: List[str] = Field(..., description="Lista de notas detectadas")


# ==============================================================================
# RESPUESTAS ESTÁNDAR - Formato uniforme para todas las respuestas
# Esto facilita el parsing desde Kotlin/Android
# ==============================================================================

def success_response(data: dict) -> dict:
    """
    Crea una respuesta exitosa en formato estándar
    
    Args:
        data: Diccionario con los datos de respuesta
        
    Returns:
        Diccionario con formato: {"success": true, "data": {...}}
    """
    return {
        "success": True,
        "data": data
    }


def error_response(message: str, status_code: int = 400) -> dict:
    """
    Crea una respuesta de error en formato estándar
    
    Args:
        message: Mensaje de error
        status_code: Código HTTP (default 400)
        
    Returns:
        Diccionario con formato: {"success": false, "error": "..."}
    """
    return {
        "success": False,
        "error": message
    }


# ==============================================================================
# ENDPOINTS - Definición de las rutas REST
# ==============================================================================

@router.post("/chat")
async def wilfredo_chat(req: ChatRequest):
    """
    Endpoint de chat con Wilfredo
    
    Permite al usuario tener una conversación interactiva con el tutor.
    Usa lógica basada en reglas (sin IA externa).
    
    Request (JSON):
        {
            "mensaje": "hola quiero aprender guitarra",
            "nivel": "principiante"
        }
        
    Response (JSON):
        {
            "success": true,
            "data": {
                "respuesta": "¡Hola! Soy Wilfredo. ¿Qué te trae por aquí hoy? 🎸",
                "nivel": "principiante"
            }
        }
    """
    try:
        # MC8: Motor Cognitivo (RIFF) — Context Builder selectivo +
        # LLMProvider con fallback determinístico y memoria conversacional.
        if req.user_id:
            try:
                from ia.cognitivo import riff
                resultado = riff.responder(req.user_id, req.mensaje)
                if resultado is not None:
                    return success_response(resultado)
            except Exception:
                pass  # cae al tutor P1.6 de abajo (retrocompatibilidad)

            # Fallback P1.6: tutor clásico con contexto (código intacto).
            from services.wilfredo_context import construir_contexto
            from services.wilfredo_service import generate_tutor_response
            ctx = construir_contexto(req.user_id)
            if ctx is not None:
                return success_response({
                    "respuesta": generate_tutor_response(req.mensaje, ctx),
                    "nivel": ctx.get("nivel", req.nivel),
                })

        # Modo clásico (sin usuario): reglas genéricas.
        nivel_detectado = evaluate_user_level(req.mensaje)
        nivel = nivel_detectado if nivel_detectado != "principiante" else req.nivel
        respuesta = generate_chat_response(req.mensaje, nivel)
        return success_response({
            "respuesta": respuesta,
            "nivel": nivel
        })

    except Exception as e:
        # Manejo de errores - se retorna mensaje claro
        return error_response(f"Error al procesar chat: {str(e)}")


@router.post("/analyze")
async def wilfredo_analyze(req: AnalyzeRequest):
    """
    Endpoint para analizar métricas de práctica
    
    Analiza las métricas de ejecución y proporciona feedback pedagógico.
    
    Request (JSON):
        {
            "precision": 0.8,
            "ritmo": 0.7,
            "bpm": 120,
            "nota": "A4"
        }
        
    Response (JSON):
        {
            "success": true,
            "data": {
                "feedback": "¡Buen trabajo! Procura mantener el ritmo constante. 🥁",
                "precision": 0.8,
                "ritmo": 0.7
            }
        }
    """
    try:
        # Se crea diccionario con las métricas
        metricas = {
            "precision": req.precision,
            "consistencia": req.ritmo,
            "bpm": req.bpm,
            "nota_detectada": req.nota or "N/A"
        }
        
        # Se genera el feedback usando la lógica de reglas
        feedback = generate_practice_feedback(metricas)
        
        return success_response({
            "feedback": feedback,
            "precision": req.precision,
            "ritmo": req.ritmo
        })
        
    except Exception as e:
        return error_response(f"Error al analizar: {str(e)}")


@router.post("/plan")
async def wilfredo_plan(req: PlanRequest):
    """
    Endpoint para generar plan de práctica
    
    Genera un plan de práctica personalizado según el nivel y objetivo.
    
    Request (JSON):
        {
            "nivel": "principiante",
            "objetivo": "acordes"
        }
        
    Response (JSON):
        {
            "success": true,
            "data": {
                "ejercicios": ["Cambio C→G", "Escala Do", "Ritmo básico"],
                "duracion": "15 min/día",
                "consejo": "Céntrate en la digitación correcta primero."
            }
        }
    """
    try:
        # Se genera el plan de práctica
        plan = generate_practice_plan(req.nivel, req.objetivo)
        
        return success_response(plan)
        
    except Exception as e:
        return error_response(f"Error al generar plan: {str(e)}")


@router.post("/tuner")
async def wilfredo_tuner(req: TunerFeedbackRequest):
    """
    Endpoint para feedback del afinador
    
    Proporciona feedback sobre la afinación de una nota.
    
    Request (JSON):
        {
            "frecuencia": 440.0,
            "nota": "A4",
            "cents": -3.5
        }
        
    Response (JSON):
        {
            "success": true,
            "data": {
                "feedback": "Casi ahí. Estás un poco bajo. Ajusta la clavija apenas. 🔧",
                "nota": "A4",
                "cents": -3.5,
                "afinado": false
            }
        }
    """
    try:
        # Se genera el feedback del afinador
        feedback = analyze_tuner_feedback(req.frecuencia, req.nota, req.cents)
        
        # Se determina si está afinado (dentro de 5 cents)
        afinado = abs(req.cents) < 5
        
        return success_response({
            "feedback": feedback,
            "nota": req.nota,
            "cents": req.cents,
            "afinado": afinado
        })
        
    except Exception as e:
        return error_response(f"Error en afinador: {str(e)}")


@router.post("/chord")
async def wilfredo_chord(req: ChordFeedbackRequest):
    """
    Endpoint para feedback de acorde
    
    Proporciona feedback sobre el acorde detectado.
    
    Request (JSON):
        {
            "notas": ["A", "C#", "E"]
        }
        
    Response (JSON):
        {
            "success": true,
            "data": {
                "feedback": "¡Buena ejecución! A Mayor suena bien. Continúa praticando. 🎸",
                "acorde": "A Mayor",
                "notas": ["A", "C#", "E"]
            }
        }
    """
    try:
        # Se crea el diccionario de acorde
        acorde = {
            "nombre": req.notas[0] if req.notas else "?",
            "tipo": "Mayor" if len(req.notas) >= 3 else "Unknown",
            "notas": req.notas
        }
        
        # Se genera el feedback
        feedback = analyze_chord_feedback(acorde)
        
        # Se determina el tipo de acorde
        tipo = "Mayor" if len(req.notas) >= 3 else "Unknown"
        
        return success_response({
            "feedback": feedback,
            "acorde": f"{req.notas[0] if req.notas else '?'} {tipo}",
            "notas": req.notas
        })
        
    except Exception as e:
        return error_response(f"Error en acorde: {str(e)}")