import librosa
import numpy as np

def analyze_audio(file_path):

    y, sr = librosa.load(file_path)

    # detectar tempo
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

    # detectar pitch promedio
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)

    pitch_values = pitches[magnitudes > np.median(magnitudes)]
    
    avg_pitch = float(np.mean(pitch_values)) if len(pitch_values) > 0 else 0

    return {
        "tempo": float(tempo),
        "avg_pitch": avg_pitch
    }