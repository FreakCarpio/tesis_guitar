import numpy as np
from audio.metricas_extractor import MetricsExtractor

sample_rate = 44100
t = np.linspace(0, 1, sample_rate)

# Señal simulada 440Hz (La)
signal = np.sin(2 * np.pi * 440 * t)

extractor = MetricsExtractor()

metrics = extractor.evaluate(signal, sample_rate, 440)

print(metrics)
