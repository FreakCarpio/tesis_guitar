import numpy as np

class FFTAnalyzer:

    def compute_fft(self, signal, sample_rate):
        """
        signal: arreglo numpy con señal en dominio tiempo
        sample_rate: frecuencia de muestreo (ej. 44100 Hz)
        """

        N = len(signal)

        # FFT
        spectrum = np.fft.fft(signal)

        # Magnitud
        magnitude = np.abs(spectrum)[:N // 2]

        # Frecuencias asociadas
        frequencies = np.fft.fftfreq(N, 1 / sample_rate)[:N // 2]

        return frequencies, magnitude
    def dominant_frequency(self, signal, sample_rate):
        frequencies, magnitude = self.compute_fft(signal, sample_rate)

        index = np.argmax(magnitude)
        dominant_freq = frequencies[index]

        return dominant_freq