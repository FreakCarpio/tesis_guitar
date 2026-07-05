import numpy as np


class FFTAnalyzer:

    def compute_fft(self, signal, sample_rate):
        """
        FFT con ventana Hann y zero-padding para mejor resolución espectral.
        """
        N = len(signal)

        window = np.hanning(N)
        signal_windowed = signal * window

        N_fft = 4 * N  # zero padding
        spectrum = np.fft.fft(signal_windowed, n=N_fft)

        magnitude = np.abs(spectrum)[:N_fft // 2]
        frequencies = np.fft.fftfreq(N_fft, 1 / sample_rate)[:N_fft // 2]

        return frequencies, magnitude

    def dominant_frequency(self, signal, sample_rate):
        """
        Detección robusta de fundamental basada en coherencia armónica.
        """

        # Eliminar DC
        signal = signal - np.mean(signal)

        rms = np.sqrt(np.mean(signal ** 2))
        if rms < 0.002:
            return 0.0, 0.0, []

        frequencies, magnitude = self.compute_fft(signal, sample_rate)

        # Harmonic Product Spectrum sobre el espectro COMPLETO desde DC.
        # HPS multiplica el espectro por copias decimadas (hps[i] = mag[i]·
        # mag[2i]·mag[3i]·mag[4i]), por lo que el índice del bin DEBE ser
        # proporcional a la frecuencia. Aplicarlo sobre un sub-rango que empieza
        # en 70 Hz (no en 0) rompe esa proporcionalidad y hace que el detector
        # se enganche a armónicos (devolvía 3·f0). Se calcula antes de recortar.
        hps = self.harmonic_product_spectrum(magnitude)

        # Rango típico guitarra (solo para elegir la fundamental).
        mask = (frequencies >= 70) & (frequencies <= 800)
        if not np.any(mask):
            return 0.0, 0.0, []

        # La fundamental es el máximo del HPS dentro de la banda de guitarra:
        # ése es justamente el propósito del Harmonic Product Spectrum.
        hps_band = np.where(mask, hps, 0.0)
        best_idx = int(np.argmax(hps_band))

        # Corrección de suboctava: el HPS a veces elige f0/2. Si en el ESPECTRO
        # original (no HPS) hay mucha más energía en 2·f0 que en f0, entonces el
        # pico elegido era un subarmónico y la fundamental real es 2·f0.
        df = frequencies[1] - frequencies[0]
        idx_doble = int(round(2 * best_idx))
        if idx_doble < len(magnitude):
            if magnitude[idx_doble] > 4.0 * magnitude[best_idx] and frequencies[idx_doble] <= 800:
                best_idx = idx_doble

        # Interpolación parabólica sub-bin sobre el HPS.
        refined_freq = self._parabolic_interpolation(frequencies, hps, best_idx)

        # Confianza = prominencia del pico de HPS respecto a la media de la
        # banda (0 = espectro plano/ruido; →1 = pico tonal marcado).
        band_vals = hps[mask]
        media = float(np.mean(band_vals)) + 1e-12
        confidence = float(min(1.0, max(0.0, 1.0 - media / (hps[best_idx] + 1e-12))))

        harmonics = []
        for h in [2, 3, 4]:
            h_freq = refined_freq * h
            if h_freq <= 1200:
                harmonics.append({
                    "order": h,
                    "frequency": h_freq
                })

        return float(refined_freq), float(confidence), harmonics

    def _parabolic_interpolation(self, frequencies, magnitude, peak_index):
        """
        Refinamiento sub-bin mediante interpolación parabólica.
        """

        if peak_index <= 0 or peak_index >= len(magnitude) - 1:
            return frequencies[peak_index]

        alpha = magnitude[peak_index - 1]
        beta = magnitude[peak_index]
        gamma = magnitude[peak_index + 1]

        denom = alpha - 2 * beta + gamma
        if abs(denom) < 1e-10:
            return frequencies[peak_index]

        p = 0.5 * (alpha - gamma) / denom
        df = frequencies[1] - frequencies[0]

        return frequencies[peak_index] + p * df

    def harmonic_product_spectrum(self, magnitude):

        hps = magnitude.copy()

        for factor in range(2, 5):
            decimated = magnitude[::factor]
            hps[:len(decimated)] *= decimated

        return hps