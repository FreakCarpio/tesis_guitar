import numpy as np
import librosa
from analizador_señales.pitch_detection import harmonic_product_spectrum

class SignalAnalyzer:

    def __init__(self, sr=22050):
        self.sr = sr

    def load_audio(self, file):
        y, sr = librosa.load(file, sr=self.sr)
        return y

    def detect_pitch(self, y):
        pitches, magnitudes = librosa.piptrack(y=y, sr=self.sr)

        pitch_values = []

        for i in range(pitches.shape[1]):
            index = magnitudes[:, i].argmax()
            pitch = pitches[index, i]
            if pitch > 0:
                pitch_values.append(pitch)

        return np.array(pitch_values)

    def rms_energy(self, y):
        rms = librosa.feature.rms(y=y)
        return np.mean(rms)

    def spectral_centroid(self, y):
        centroid = librosa.feature.spectral_centroid(y=y, sr=self.sr)
        return np.mean(centroid)

    def tempo(self, y):
        tempo, _ = librosa.beat.beat_track(y=y, sr=self.sr)
        return tempo