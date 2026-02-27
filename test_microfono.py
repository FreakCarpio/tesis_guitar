import numpy as np
import sounddevice as sd
from audio.metricas_extractor import MetricsExtractor

duration = 3  # segundos
sample_rate = 44100

print("Grabando... Toca una nota ahora.")

audio = sd.rec(int(duration * sample_rate),
               samplerate=sample_rate,
               channels=1,
               dtype='float64')

sd.wait()

print("Grabación completa.")

signal = audio.flatten()

extractor = MetricsExtractor()

# 1️⃣ Detectar frecuencia fundamental
freq_detected = extractor.detect_pitch(signal, sample_rate)

# 2️⃣ Convertir frecuencia a nota musical
def frequency_to_note(freq):
    note_names = ["C", "C#", "D", "D#", "E", "F",
                  "F#", "G", "G#", "A", "A#", "B"]
    
    midi_number = round(69 + 12 * np.log2(freq / 440.0))
    note = note_names[midi_number % 12]
    octave = (midi_number // 12) - 1
    
    return f"{note}{octave}"

note_detected = frequency_to_note(freq_detected)

print("Frecuencia detectada:", round(freq_detected, 2), "Hz")
print("Nota detectada:", note_detected)