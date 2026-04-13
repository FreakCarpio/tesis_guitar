"""
Tuner Routes - Endpoints del afinador

Este módulo define los endpoints REST para la funcionalidad del afinador:
- Detección de nota por frecuencia
- Verificación de nota específica
- Identificación de acordes

Compatible con consumo desde Kotlin/Android vía Retrofit.

Autor: Tesis App
Fecha: 2026
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import numpy as np
import io
from audio.metricas_extractor import MetricsExtractor

# Se crea el router con prefijo /tuner para todas las rutas
# Esto significa que todos los endpoints starts con /tuner/
# Ejemplo: /tuner/pitch, /tuner/chord, /tuner/verify
router = APIRouter(prefix="/tuner", tags=["tuner"])

# Se inicializa el extractor de métricas para análisis de audio
# Este objeto se usa para procesar archivos de audio
extractor = MetricsExtractor()


# ==============================================================================
# MODELOS PYDANTIC - Definen la estructura de datos de entrada y salida
# ==============================================================================

class PitchRequest(BaseModel):
    """
    Solicitud para detectar nota por frecuencia
    
    Parámetros:
    - frecuencia: Frecuencia en Hz (20-5000 Hz)
    """
    frecuencia: float = Field(..., description="Frecuencia en Hz", ge=20, le=5000)


class VerifyRequest(BaseModel):
    """
    Solicitud para verificar si una frecuencia corresponde a una nota específica
    
    Parámetros:
    - frecuencia: Frecuencia en Hz
    - nota_esperada: Nota que se espera detectar (ej: A, E, G)
    """
    frecuencia: float = Field(..., description="Frecuencia en Hz", ge=20, le=5000)
    nota_esperada: str = Field(..., description="Nota esperada (ej: A, E, G)")


class ChordRequest(BaseModel):
    """
    Solicitud para identificar acorde
    
    Parámetros:
    - notas: Lista de notas separadas por coma (ej: "A,C#,E")
    """
    notas: str = Field(..., description="Notas separadas por coma (ej: A,C#,E)")


# ==============================================================================
# RESPUESTAS ESTÁNDAR - Formato uniforme para todas las respuestas
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


def error_response(message: str) -> dict:
    """
    Crea una respuesta de error en formato estándar
    
    Args:
        message: Mensaje de error
        
    Returns:
        Diccionario con formato: {"success": false, "error": "..."}
    """
    return {
        "success": False,
        "error": message
    }


# ==============================================================================
# FUNCIONES AUXILIARES - Helpers para procesamiento de audio
# ==============================================================================

def audio_from_upload(file: UploadFile) -> tuple:
    """
    Convierte un archivo de audio uploadado a numpy array
    
    Usa soundfile si está disponible, sino usa sounddevice.
    Normaliza la señal para análisis.
    
    Args:
        file: Archivo de audio uploadado
        
    Returns:
        Tupla (signal, sample_rate)
    """
    try:
        # Intento usar soundfile para leer el audio
        import soundfile as sf
        bytes_io = io.BytesIO(file.file.read())
        signal, sample_rate = sf.read(bytes_io)
        # Si es estéreo, convertir a mono
        if len(signal.shape) > 1:
            signal = signal.mean(axis=1)
    except ImportError:
        # Si no hay soundfile, usar sounddevice
        import sounddevice as sd
        import tempfile
        import os
        bytes_io = io.BytesIO(file.file.read())
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(bytes_io.read())
            tmp_path = tmp.name
        signal, sample_rate = sd.read(tmp_path)
        os.remove(tmp_path)

    # Normalizo la señal - divido por el valor máximo
    signal = signal.astype(np.float64)
    if np.max(np.abs(signal)) > 0:
        signal = signal / np.max(np.abs(signal))

    return signal, sample_rate


def frequency_to_note_detailed(freq: float) -> dict:
    """
    Convierte frecuencia a nota musical con detalle
    
    Calcula la nota musical, octava, y cents de diferencia.
    
    Args:
        freq: Frecuencia en Hz
        
    Returns:
        Diccionario con nota, octava, frecuencia teórica, cents
    """
    if freq <= 0:
        return {"nota": "N/A", "octava": 0, "freq_teorica": 0, "cents": 0}
    
    # Nombres de las notas musicales
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    
    # Calculo el número MIDI basado en la frecuencia
    # A4 = 440Hz = MIDI 69
    midi_number = round(69 + 12 * np.log2(freq / 440.0))
    
    # Verifico que esté en rango válido (0-127)
    if midi_number < 0 or midi_number > 127:
        return {"nota": "Fuera de rango", "octava": 0, "freq_teorica": 0, "cents": 0}
    
    # Extraigo la nota y octava
    nota = note_names[midi_number % 12]
    octava = (midi_number // 12) - 1
    
    # Calculo la frecuencia teórica de esa nota
    freq_teorica = 440 * 2 ** ((midi_number - 69) / 12)
    
    # Calculo los cents de diferencia
    cents = 1200 * np.log2(freq / freq_teorica)
    
    return {
        "nota": nota,
        "octava": octava,
        "freq_teorica": float(freq_teorica),
        "cents": float(cents)
    }


# ==============================================================================
# ENDPOINTS - Definición de las rutas REST
# ==============================================================================

@router.post("/pitch")
async def detect_pitch_from_json(req: PitchRequest):
    """
    Endpoint para detectar nota desde frecuencia (JSON)
    
    Este endpoint permite enviar una frecuencia en Hz y obtener
    la nota musical correspondiente.
    
    Request (JSON):
        {
            "frecuencia": 440.0
        }
        
    Response (JSON):
        {
            "success": true,
            "data": {
                "nota": "A",
                "octava": 4,
                "afinado": true,
                "cents": 0.0
            }
        }
    """
    try:
        freq = req.frecuencia
        
        # Validación básica
        if freq <= 0 or freq > 5000:
            return error_response("Frecuencia fuera de rango válido (20-5000 Hz)")
        
        # Convierto frecuencia a nota
        detalle = frequency_to_note_detailed(freq)
        
        # Determino si está afinado (dentro de 5 cents)
        afinado = abs(detalle["cents"]) < 5
        
        return success_response({
            "nota": detalle["nota"],
            "octava": detalle["octava"],
            "afinado": afinado,
            "cents": round(detalle["cents"], 1),
            "frecuencia": freq,
            "freq_teorica": round(detalle["freq_teorica"], 1)
        })
        
    except Exception as e:
        return error_response(f"Error al detectar nota: {str(e)}")


@router.post("/verify")
async def verify_pitch(req: VerifyRequest):
    """
    Endpoint para verificar si una frecuencia corresponde a una nota específica
    
    Útil para el modo de afinación donde el usuario selecciona
    la nota que quiere afinar.
    
    Request (JSON):
        {
            "frecuencia": 442.0,
            "nota_esperada": "A"
        }
        
    Response (JSON):
        {
            "success": true,
            "data": {
                "nota": "A",
                "nota_esperada": "A",
                "coincide": true,
                "afinado": false,
                "cents": 7.9
            }
        }
    """
    try:
        freq = req.frecuencia
        nota_esperada = req.nota_esperada.upper()
        
        # Convierto frecuencia a nota
        detalle = frequency_to_note_detailed(freq)
        
        # Verifico si coinciden (misma letra, sin importar octava)
        detalle_nota = detalle["nota"].replace("#", "").replace("S", "#")
        nota_limpia = nota_esperada.replace("#", "").replace("S", "#")
        
        coincide = detalle_nota == nota_limpia
        
        # Determino si está afinado
        afinado = abs(detalle["cents"]) < 5
        
        return success_response({
            "nota": detalle["nota"],
            "nota_esperada": nota_esperada,
            "coincide": coincide,
            "afinado": afinado,
            "cents": round(detalle["cents"], 1)
        })
        
    except Exception as e:
        return error_response(f"Error al verificar nota: {str(e)}")


@router.post("/identify")
async def identify_chord_from_notes(req: ChordRequest):
    """
    Endpoint para identificar acorde desde lista de notas
    
    Toma una lista de notas y determina el tipo de acorde.
    
    Request (JSON):
        {
            "notas": "A,C#,E"
        }
        
    Response (JSON):
        {
            "success": true,
            "data": {
                "acorde": "A Mayor",
                "tipo": "Mayor",
                "raiz": "A",
                "notas": ["A", "C#", "E"]
            }
        }
    """
    try:
        # Parseo las notas
        notas_raw = req.notas.replace(" ", "").split(",")
        notas = [n.upper().replace("S", "#") for n in notas_raw]
        
        # Identifico el acorde usando el extractor
        resultado = extractor.identify_chord_from_notes(notas)
        
        if resultado is None:
            return error_response("No se pudo identificar el acorde")
        
        return success_response({
            "acorde": resultado.get("nombre", "Desconocido"),
            "tipo": resultado.get("tipo", "Desconocido"),
            "raiz": resultado.get("raiz", ""),
            "notas": resultado.get("notas", notas)
        })
        
    except Exception as e:
        return error_response(f"Error al identificar acorde: {str(e)}")


# ==============================================================================
# ENDPOINTS DE AUDIO - Para procesamiento de archivos de audio
# Estos endpoints mantienen compatibilidad con uploads de archivos
# ==============================================================================

@router.post("/pitch/file")
async def detect_pitch_from_file(file: UploadFile = File(...)):
    """
    Endpoint para detectar nota desde archivo de audio
    
    Este endpoint procesa un archivo de audio y detecta
    la nota que se está tocando.
    
    Args:
        file: Archivo de audio (wav, mp3, etc.)
        
    Response (JSON):
        {
            "success": true,
            "data": {
                "frecuencia": 440.0,
                "nota": "A",
                "afinado": true,
                "cents": 0.0
            }
        }
    """
    try:
        # Convierto el archivo a numpy array
        signal, sample_rate = audio_from_upload(file)
        
        # Detecto la frecuencia
        freq, conf, harmonics = extractor.detect_pitch(signal, sample_rate)
        
        if freq <= 0:
            return error_response("Silencio o señal no detectada")
        
        # Convierto a nota
        detalle = frequency_to_note_detailed(freq)
        
        # Determino si está afinado
        afinado = abs(detalle["cents"]) < 5
        
        return success_response({
            "frecuencia": float(freq),
            "nota": f"{detalle['nota']}{detalle['octava']}",
            "afinado": afinado,
            "cents": round(detalle["cents"], 1),
            "confianza": float(conf),
            "armonicos": harmonics
        })
        
    except Exception as e:
        return error_response(f"Error al procesar archivo: {str(e)}")


@router.post("/chord/file")
async def detect_chord_from_file(file: UploadFile = File(...)):
    """
    Endpoint para detectar acorde desde archivo de audio
    
    Este endpoint procesa un archivo de audio y detecta
    el acorde que se está tocando.
    
    Args:
        file: Archivo de audio (wav, mp3, etc.)
        
    Response (JSON):
        {
            "success": true,
            "data": {
                "acorde": "A Mayor",
                "tipo": "Mayor"
            }
        }
    """
    try:
        # Convierto el archivo a numpy array
        signal, sample_rate = audio_from_upload(file)
        
        # Identifico el acorde
        resultado = extractor.identify_chord(signal, sample_rate)
        
        if resultado is None:
            return error_response("No se detectó acorde")
        
        return success_response({
            "acorde": resultado.get("nombre", "Desconocido"),
            "tipo": resultado.get("tipo", "Desconocido"),
            "notas": resultado.get("notas", [])
        })
        
    except Exception as e:
        return error_response(f"Error al procesar archivo: {str(e)}")