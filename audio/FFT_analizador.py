import numpy as np

class FFTAnalyzer:

    def compute_fft(self, signal, sample_rate):
        N = len(signal)
        spectrum = np.fft.fft(signal)
        magnitude = np.abs(spectrum)[:N // 2]
        frequencies = np.fft.fftfreq(N, 1 / sample_rate)[:N // 2]
        return frequencies, magnitude

    def dominant_frequency(self, signal, sample_rate):
        # Eliminar componente DC (corriente continua)
        signal = signal - np.mean(signal)
        
        # Verificar que haya señal suficiente (evitar procesar silencio)
        if np.max(np.abs(signal)) < 0.001:
            return 0.0
        
        # Aplicar ventana de Hann (mejor para instrumentos musicales que Hamming)
        window = np.hann(len(signal))
        signal = signal * window
        
        frequencies, magnitude = self.compute_fft(signal, sample_rate)
        
        # Rango extendido 70Hz - 1500Hz para todas las cuerdas
        # Incluye: Mi grave (82Hz) hasta armónicos de Mi agudo (330Hz y sus armónicos)
        mask = (frequencies >= 70) & (frequencies <= 1500)
        
        if not np.any(mask):
            return 0.0
        
        filtered_freqs = frequencies[mask]
        filtered_mag = magnitude[mask]
        
        # Encontrar el pico máximo
        peak_index = np.argmax(filtered_mag)
        
        # MEJORA: Interpolación parabólica para precisión sub-bin
        # Esto mejora la detección en frecuencias bajas donde la resolución FFT es baja
        if 0 < peak_index < len(filtered_mag) - 1:
            alpha = filtered_mag[peak_index - 1]
            beta = filtered_mag[peak_index]
            gamma = filtered_mag[peak_index + 1]
            
            # Solo interpolar si tenemos un pico claro (no en los bordes planos)
            if alpha < beta and gamma < beta:
                p = 0.5 * (alpha - gamma) / (alpha - 2*beta + gamma)
                # Calcular delta de frecuencia entre bins
                df = filtered_freqs[1] - filtered_freqs[0] if len(filtered_freqs) > 1 else 1
                refined_freq = filtered_freqs[peak_index] + p * df
            else:
                refined_freq = filtered_freqs[peak_index]
        else:
            refined_freq = filtered_freqs[peak_index]
        
        return float(refined_freq)
    
    def get_harmonics(self, signal, sample_rate, fundamental, n_harmonics=5):
        """
        Detecta los armónicos de una frecuencia fundamental.
        Útil para validar que es una nota musical real.
        """
        frequencies, magnitude = self.compute_fft(signal, sample_rate)
        
        harmonics = []
        for i in range(1, n_harmonics + 1):
            harmonic_freq = fundamental * i
            # Buscar en un rango de ±5% alrededor del armónico teórico
            mask = (frequencies >= harmonic_freq * 0.95) & (frequencies <= harmonic_freq * 1.05)
            if np.any(mask):
                harmonic_mag = np.max(magnitude[mask])
                harmonics.append({
                    'order': i,
                    'frequency': harmonic_freq,
                    'magnitude': float(harmonic_mag)
                })
        
        return harmonics