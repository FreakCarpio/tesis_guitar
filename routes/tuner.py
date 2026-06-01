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
from audio.tuner_engine import TunerEngine, frequency_to_note_info
from audio.audio_filters import AudioPreprocessor
from audio.noise_reduction import SpectralNoiseReducer, WienerFilterNoiseReducer
from audio.pipeline_validator import PipelineValidator

# Se crea el router con prefijo /tuner para todas las rutas
# Esto significa que todos los endpoints starts con /tuner/
# Ejemplo: /tuner/pitch, /tuner/chord, /tuner/verify
router = APIRouter(prefix="/tuner", tags=["tuner"])

# Se inicializa el extractor de métricas para análisis de audio
# Este objeto se usa para procesar archivos de audio
extractor = MetricsExtractor()

# Motor de afinación con pipeline DSP completo (filtros + detección + estabilización)
# Usado por los endpoints mejorados /tuner/analyze, /tuner/analyze/file
tuner_engine = TunerEngine(sample_rate=44100)

# Validador del pipeline para diagnóstico y comparación antes/después
# Útil para tesis: cuantifica la mejora de cada etapa
pipeline_validator = PipelineValidator(sample_rate=44100)


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
    # Leer el archivo una sola vez para evitar consumir el stream
    audio_bytes = file.file.read()
    
    try:
        # Intento usar soundfile para leer el audio
        import soundfile as sf
        bytes_io = io.BytesIO(audio_bytes)
        signal, sample_rate = sf.read(bytes_io)
        # Si es estéreo, convertir a mono
        if len(signal.shape) > 1:
            signal = signal.mean(axis=1)
    except Exception:
        # Si no hay soundfile o falla, usar sounddevice
        import sounddevice as sd
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            signal, sample_rate = sd.read(tmp_path)
        finally:
            if os.path.exists(tmp_path):
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


# ==============================================================================
# ENDPOINTS MEJORADOS - Con pipeline DSP completo
# ==============================================================================

@router.post("/analyze")
async def tuner_analyze(req: PitchRequest):
    """
    Endpoint mejorado: detecta nota con pipeline DSP completo.

    Este endpoint toma una frecuencia (como el /pitch original) pero
    además retorna información detallada: cuerda de guitarra, dirección
    de ajuste, estado de afinación, etc.

    Útil cuando el cliente ya ha procesado el audio y solo envía
    la frecuencia detectada.

    Request (JSON):
        {
            "frecuencia": 440.0
        }

    Response (JSON):
        {
            "success": true,
            "data": {
                "nota": "A4",
                "frecuencia": 440.0,
                "frecuencia_teorica": 440.0,
                "cents": 0.0,
                "cuerda": "N/A",
                "afinado": true,
                "direccion": "afinado"
            }
        }
    """
    try:
        freq = req.frecuencia
        if freq <= 0 or freq > 5000:
            return error_response("Frecuencia fuera de rango válido (20-5000 Hz)")

        note_info = frequency_to_note_info(freq)

        cents_val = float(note_info["cents"])
        return success_response({
            "nota": note_info["nota_completa"],
            "frecuencia": float(freq),
            "frecuencia_teorica": float(note_info["freq_teorica"]),
            "cents": round(cents_val, 2),
            "cuerda": note_info["cuerda"],
            "afinado": bool(abs(cents_val) < 5),
            "direccion": tuner_engine.get_tuning_direction(cents_val)
        })

    except Exception as e:
        return error_response(f"Error al analizar: {str(e)}")


@router.post("/analyze/file")
async def tuner_analyze_file(file: UploadFile = File(...)):
    """
    Endpoint mejorado: detecta nota desde archivo de audio con pipeline DSP.

    Este endpoint utiliza el pipeline completo:
    1. Notch filters (50/60/120 Hz) - elimina ruido eléctrico
    2. Band-pass filter (60-1200 Hz) - enfoca en rango de guitarra
    3. Noise gate - elimina ruido ambiente
    4. Reducción espectral de ruido (si calibrado)
    5. Detección multi-algoritmo (HPS + Autocorrelación)
    6. Estabilización temporal (mediana móvil)
    7. Validación de cuerda de guitarra

    Response (JSON):
        {
            "success": true,
            "data": {
                "frecuencia": 440.0,
                "nota": "A4",
                "cents": 0.0,
                "cuerda": null,
                "confianza": 0.95,
                "hay_señal": true,
                "afinado": true,
                "direccion": "afinado"
            }
        }
    """
    try:
        signal, sample_rate = audio_from_upload(file)

        result = tuner_engine.analyze_file(signal, sample_rate)

        if result["frames_analizados"] == 0:
            return error_response("Silencio o señal no detectada")

        freq = result["frecuencia"]
        note_info = frequency_to_note_info(freq)

        return success_response({
            "frecuencia": round(freq, 2),
            "frecuencia_promedio": round(result.get("frecuencia_promedio", freq), 2),
            "nota": result["nota"],
            "cents": round(result["cents"], 2),
            "cuerda": note_info["cuerda"],
            "confianza": round(result["confianza_promedio"], 3),
            "estabilidad": round(result.get("estabilidad", 0), 3),
            "frames_analizados": result["frames_analizados"],
            "hay_señal": True,
            "afinado": result["afinado"],
            "direccion": tuner_engine.get_tuning_direction(result["cents"])
        })

    except Exception as e:
        return error_response(f"Error al procesar con pipeline DSP: {str(e)}")


@router.post("/analyze/raw")
async def tuner_analyze_raw(file: UploadFile = File(...)):
    """
    Endpoint para análisis frame a frame (baja latencia).

    Procesa el audio en frames pequeños (~100ms) y retorna resultados
    por cada frame. Ideal para visualización en tiempo real desde la
    app móvil.

    Args:
        file: Archivo de audio corto (recomendado: 0.5-2 segundos)

    Response (JSON):
        {
            "success": true,
            "data": {
                "frames": [
                    {
                        "frecuencia": 440.0,
                        "nota": "A4",
                        "cents": 0.0,
                        "confianza": 0.95
                    }
                ],
                "frame_duration_ms": 100
            }
        }
    """
    try:
        signal, sample_rate = audio_from_upload(file)

        frame_size = int(sample_rate * 0.1)
        hop_size = frame_size // 2

        frames_result = []
        for start in range(0, len(signal) - frame_size + 1, hop_size):
            frame = signal[start:start + frame_size]
            result = tuner_engine.analyze_frame(frame)
            if result["hay_señal"]:
                frames_result.append({
                    "frecuencia": round(result["frecuencia"], 2),
                    "nota": result["nota"],
                    "cents": round(result["cents"], 2),
                    "confianza": round(result["confianza"], 3),
                    "cuerda": result["cuerda"]
                })

        return success_response({
            "frames": frames_result,
            "total_frames": len(frames_result),
            "frame_duration_ms": 100
        })

    except Exception as e:
        return error_response(f"Error en análisis raw: {str(e)}")


@router.post("/calibrate")
async def tuner_calibrate(file: UploadFile = File(...)):
    """
    Endpoint para calibrar la reducción de ruido espectral.

    Envía una muestra de 1-2 segundos de solo ruido ambiente
    (sin tocar la guitarra). El sistema aprende el piso de ruido
    y lo usará para filtrar en análisis posteriores.

    Args:
        file: Muestra de audio ambiental (1-2 segundos, sin guitarra)

    Response (JSON):
        {
            "success": true,
            "data": {
                "calibrado": true,
                "mensaje": "Ruido ambiental calibrado correctamente"
            }
        }
    """
    try:
        signal, sample_rate = audio_from_upload(file)

        tuner_engine.calibrate_noise(signal)

        return success_response({
            "calibrado": True,
            "mensaje": "Ruido ambiental calibrado correctamente. El afinador ahora ignorará el ruido de fondo."
        })

    except Exception as e:
        return error_response(f"Error al calibrar: {str(e)}")


@router.get("/pipeline")
async def tuner_pipeline_info():
    """
    Endpoint informativo: retorna la descripción del pipeline DSP.

    Útil para documentación de tesis y debugging.
    Muestra cada etapa del procesamiento con su justificación técnica.

    Response (JSON):
        {
            "success": true,
            "data": {
                "pipeline": [
                    {
                        "etapa": 1,
                        "nombre": "Notch Filter (50/60/120 Hz)",
                        "proposito": "Eliminar zumbido eléctrico de red",
                        "tipo": "IIR Notch, Q=30"
                    }
                ]
            }
        }
    """
    try:
        preprocessor = AudioPreprocessor()
        etapas = preprocessor.get_pipeline_description()

        return success_response({
            "pipeline": etapas,
            "algoritmos_pitch": [
                "FFT directo con interpolación parabólica (principal)",
                "Autocorrelación YIN simplificado (verificación)",
                "HPS - Harmonic Product Spectrum (coherencia armónica)"
            ],
            "fusion_sensores": "Sensor fusion por mayoría ponderada (FFT + AC + HPS)",
            "estabilizacion": "Mediana móvil ponderada por confianza sobre 7 frames",
            "deteccion_ataque": "Onset detection por RMS envelope follower",
            "validacion_guitarra": "Template matching armónico por cuerda",
            "cuerdas_soportadas": ["E2 (82 Hz)", "A2 (110 Hz)", "D3 (146 Hz)", "G3 (196 Hz)", "B3 (246 Hz)", "E4 (329 Hz)"],
            "tolerancia_afinacion": "±5 cents",
            "tipos_reduccion_ruido": [
                "Spectral Gating (umbral espectral adaptativo)",
                "Wiener Filter adaptativo (estimación MMSE)"
            ]
        })

    except Exception as e:
        return error_response(f"Error al obtener pipeline: {str(e)}")


@router.post("/validate")
async def validate_guitar_note(file: UploadFile = File(...)):
    """
    Valida si el audio corresponde a una nota de guitarra acústica.

    Analiza coherencia armónica, proximidad a cuerdas de guitarra,
    y calidad de señal. Ideal para filtrar ruido antes del afinador.

    Para tesis: Este endpoint demuestra que el sistema puede distinguir
    entre una cuerda de guitarra y otras fuentes de sonido usando
    análisis de templates armónicos.
    """
    try:
        signal, sample_rate = audio_from_upload(file)

        result = pipeline_validator.validate_guitar_note(signal, sample_rate)

        return success_response(result)

    except Exception as e:
        return error_response(f"Error al validar nota: {str(e)}")


@router.post("/pipeline/compare")
async def compare_pipeline_effect(file: UploadFile = File(...)):
    """
    Compara la señal antes y después del pipeline DSP completo.

    Retorna métricas de calidad (SNR, confianza, frecuencia) para
    la señal original y la procesada, demostrando cuantitativamente
    la mejora del preprocesamiento.

    Para tesis: Este endpoint es la herramienta principal para
    demostrar experimentalmente la efectividad de cada etapa
    del pipeline de filtrado.
    """
    try:
        signal, sample_rate = audio_from_upload(file)

        comparison = pipeline_validator.compare_pipeline_stages(signal)

        return success_response(comparison)

    except Exception as e:
        return error_response(f"Error al comparar pipeline: {str(e)}")


@router.post("/quality")
async def analyze_audio_quality(file: UploadFile = File(...)):
    """
    Analiza la calidad de la señal de audio grabada.

    Detecta: clipping, silencio, SNR, nivel de ruido.
    Recomienda ajustes al usuario para mejorar la grabación.

    Para tesis: Muestra que el sistema es consciente de la calidad
    de la señal de entrada y puede diagnosticar problemas comunes.
    """
    try:
        signal, _ = audio_from_upload(file)

        quality = pipeline_validator.analyze_signal_quality(signal)

        recomendaciones = []
        if quality.get("has_clipping"):
            recomendaciones.append("Aleja el micrófono o toca más suave (hay distorsión)")
        if quality.get("is_too_quiet"):
            recomendaciones.append("Acerca el micrófono a la guitarra o toca más fuerte")
        if quality.get("snr_estimate_db", 0) < 10:
            recomendaciones.append("Reduce el ruido ambiental o usa un micrófono direccional")

        return success_response({
            **quality,
            "recomendaciones": recomendaciones
        })

    except Exception as e:
        return error_response(f"Error al analizar calidad: {str(e)}")