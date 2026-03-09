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

        # Rango típico guitarra
        mask = (frequencies >= 70) & (frequencies <= 800)
        if not np.any(mask):
            return 0.0, 0.0, []

        freqs = frequencies[mask]
        mags = magnitude[mask]
        mags = self.harmonic_product_spectrum(mags)

        # Tomar los 15 picos más fuertes
        n_peaks = 15
        peak_indices = np.argsort(mags)[-n_peaks:]

        candidates = []
        for idx in peak_indices:
            candidates.append({
                "freq": freqs[idx],
                "mag": mags[idx],
                "idx": idx
            })

        # Ordenar por frecuencia ascendente (clave)
        candidates = sorted(candidates, key=lambda x: x["freq"])

        best = None

        # Buscar fundamental por coherencia armónica
        for candidate in candidates:
            f0 = candidate["freq"]

            harmonic_hits = 0

            for h in [2, 3]:
                target = f0 * h
                tolerance = 6  # Hz

                for other in candidates:
                    if abs(other["freq"] - target) < tolerance:
                        harmonic_hits += 1
                        break

            # Si tiene al menos un armónico coherente → aceptar
            if harmonic_hits >= 1:
                best = candidate
                break

        # Fallback: usar el más bajo
        if best is None:
            best = candidates[0]

        # Interpolación parabólica
        refined_freq = self._parabolic_interpolation(
            freqs,
            mags,
            best["idx"]
        )

        confidence = min(1.0, best["mag"] / np.max(mags))

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