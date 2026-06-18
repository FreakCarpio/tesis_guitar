import os
import tempfile
from fastapi import APIRouter, UploadFile, File
from analizador_señales.señal import SignalAnalyzer

router = APIRouter()

analyzer = SignalAnalyzer()

@router.post("/practica/analyze")
async def analyze_practice(audio: UploadFile = File(...)):

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename or ".wav")[1])
    file_path = tmp.name
    tmp.write(await audio.read())
    tmp.close()

    y = analyzer.load_audio(file_path)

    pitches = analyzer.detect_pitch(y)

    result = {
        "pitch_mean": float(pitches.mean()) if len(pitches)>0 else 0,
        "energy": float(analyzer.rms_energy(y)),
        "brightness": float(analyzer.spectral_centroid(y)),
        "tempo": float(analyzer.tempo(y))
    }

    os.unlink(file_path)

    return result