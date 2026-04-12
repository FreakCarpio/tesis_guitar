from fastapi import APIRouter, UploadFile, File
import numpy as np
import io

from audio.metricas_extractor import MetricsExtractor

router = APIRouter(prefix="/tuner", tags=["tuner"])
extractor = MetricsExtractor()


def audio_from_upload(file: UploadFile) -> tuple:
    """convierto audio a numpy"""
    try:
        import soundfile as sf
        bytes_io = io.BytesIO(file.file.read())
        signal, sample_rate = sf.read(bytes_io)
        if len(signal.shape) > 1:
            signal = signal.mean(axis=1)
    except ImportError:
        import sounddevice as sd
        import tempfile
        import os
        bytes_io = io.BytesIO(file.file.read())
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(bytes_io.read())
            tmp_path = tmp.name
        signal, sample_rate = sd.read(tmp_path)
        os.remove(tmp_path)

    # normalizo la señal
    signal = signal.astype(np.float64)
    if np.max(np.abs(signal)) > 0:
        signal = signal / np.max(np.abs(signal))

    return signal, sample_rate


@router.post("/pitch")
async def detect_pitch(file: UploadFile = File(...)):
    """detecto la nota"""
    signal, sample_rate = audio_from_upload(file)

    freq, conf, harmonics = extractor.detect_pitch(signal, sample_rate)

    if freq <= 0:
        return {"error": "Silencio o señal no detectada", "frecuencia": 0}

    nota = extractor.frequency_to_note(freq)

    # calculo cents参考 A4=440Hz
    A4 = 440
    semitonos = 12 * np.log2(freq / A4)
    semIndex = round(semitonos) + 69
    freqIdeal = A4 * 2 ** ((semIndex - 69) / 12)
    cents = 1200 * np.log2(freq / freqIdeal)

    return {
        "frecuencia": float(freq),
        "nota": nota,
        "confianza": float(conf),
        "cents": float(cents),
        "armonicos": harmonics
    }


@router.post("/chord")
async def detect_chord(file: UploadFile = File(...)):
    """detecto el acorde"""
    signal, sample_rate = audio_from_upload(file)
    resultado = extractor.identify_chord(signal, sample_rate)

    if resultado is None:
        return {"error": "No se detectó acorde", "acorde": None}

    return {"acorde": resultado}