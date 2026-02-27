import numpy as np
from audio.FFT_analizador import FFTAnalyzer

class MetricsExtractor:

    def __init__(self):
        self.fft = FFTAnalyzer()

    def detect_pitch(self, signal, sample_rate):
        return self.fft.dominant_frequency(signal, sample_rate)

    def evaluate(self, signal, sample_rate, target_freq):
        detected_freq = self.detect_pitch(signal, sample_rate)

        error = abs(detected_freq - target_freq)

        precision = max(0, 1 - (error / target_freq))

        consistency = 1 - (np.std(signal) / np.max(np.abs(signal)))

        return {
            "precision": float(precision),
            "consistencia": float(consistency),
            "error": float(error)
        }