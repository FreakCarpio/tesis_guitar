import numpy as np

class FFTAnalyzer:

    def compute_fft(self, signal, sample_rate):
        N = len(signal)

        spectrum = np.fft.fft(signal)

        magnitude = np.abs(spectrum)[:N // 2]

        frequencies = np.fft.fftfreq(N, 1 / sample_rate)[:N // 2]

        return frequencies, magnitude

    def dominant_frequency(self, signal, sample_rate):

        signal = signal - np.mean(signal)  # eliminar DC

        window = np.hamming(len(signal))
        signal = signal * window  # aplicar ventana

        frequencies, magnitude = self.compute_fft(signal, sample_rate)

        # limitar rango útil (guitarra)
        mask = (frequencies > 80) & (frequencies < 1200)

        if not np.any(mask):
            return 0.0

        filtered_freqs = frequencies[mask]
        filtered_mag = magnitude[mask]

        index = np.argmax(filtered_mag)
        dominant_freq = filtered_freqs[index]

        return float(dominant_freq)