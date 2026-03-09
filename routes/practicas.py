from fastapi import APIRouter, UploadFile, File
from analizador_señales.señal import SignalAnalyzer

router = APIRouter()

analyzer = SignalAnalyzer()

@router.post("/practica")
async def analyze_practice(audio: UploadFile = File(...)):

    file_path = f"/tmp/{audio.filename}"

    with open(file_path, "wb") as f:
        f.write(await audio.read())

    y = analyzer.load_audio(file_path)

    pitches = analyzer.detect_pitch(y)

    result = {
        "pitch_mean": float(pitches.mean()) if len(pitches)>0 else 0,
        "energy": float(analyzer.rms_energy(y)),
        "brightness": float(analyzer.spectral_centroid(y)),
        "tempo": float(analyzer.tempo(y))
    }

    return result