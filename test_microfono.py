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

# Ejemplo: nota La 440Hz
metrics = extractor.evaluate(signal, sample_rate, 440)

print("Resultados:", metrics)