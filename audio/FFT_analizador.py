import numpy as np

class FFTAnalyzer:

    def compute_fft(self, signal, sample_rate):
        N = len(signal)
        # Aplicar zero-padding para mejor resolución de frecuencia
        N_padded = 2 ** (int(np.ceil(np.log2(N))) + 2)  # Siguiente potencia de 2 x4
        spectrum = np.fft.fft(signal, n=N_padded)
        magnitude = np.abs(spectrum)[:N_padded // 2]
        frequencies = np.fft.fftfreq(N_padded, 1 / sample_rate)[:N_padded // 2]
        return frequencies, magnitude

    def dominant_frequency(self, signal, sample_rate):
        # Eliminar componente DC
        signal = signal - np.mean(signal)
        
        # Verificar nivel de señal
        max_amp = np.max(np.abs(signal))
        if max_amp < 0.005:  # Umbral más bajo para señales débiles
            return 0.0
        
        # Normalizar para consistencia
        signal = signal / max_amp
        
        # Aplicar ventana de Hann
        window = np.hanning(len(signal))
        signal = signal * window
        
        frequencies, magnitude = self.compute_fft(signal, sample_rate)
        
        # Rango: 70Hz - 1500Hz (guitarra estándar)
        mask = (frequencies >= 70) & (frequencies <= 1500)
        
        if not np.any(mask):
            return 0.0
        
        filtered_freqs = frequencies[mask]
        filtered_mag = magnitude[mask]
        
        # Suavizar el espectro para reduuir picos espurios
        from scipy.ndimage import uniform_filter1d
        if len(filtered_mag) > 10:
            filtered_mag_smooth = uniform_filter1d(filtered_mag, size=3)
        else:
            filtered_mag_smooth = filtered_mag
        
        # Encontrar picos locales (no solo el máximo global)
        peaks = self._find_peaks(filtered_mag_smooth, threshold=0.3)
        
        if not peaks:
            # Si no hay picos claros, usar el máximo global
            peak_index = np.argmax(filtered_mag_smooth)
        else:
            # Seleccionar el pico más prominente en el rango de guitarra
            peak_index = self._select_guitar_peak(filtered_freqs, filtered_mag_smooth, peaks)
        
        # Interpolación parabólica
        refined_freq = self._parabolic_interpolation(
            filtered_freqs, filtered_mag_smooth, peak_index
        )
        
        return float(refined_freq)
    
    def _find_peaks(self, magnitude, threshold=0.3):
        """Encuentra picos locales que superan el umbral relativo."""
        max_mag = np.max(magnitude)
        if max_mag == 0:
            return []
        
        # Umbral absoluto
        threshold_abs = max_mag * threshold
        
        peaks = []
        for i in range(1, len(magnitude) - 1):
            if (magnitude[i] > magnitude[i-1] and 
                magnitude[i] > magnitude[i+1] and 
                magnitude[i] > threshold_abs):
                peaks.append(i)
        
        return peaks
    
    def _select_guitar_peak(self, frequencies, magnitude, peaks):
        """
        Selecciona el mejor pico para guitarra.
        Prioriza frecuencias en rangos comunes de cuerdas.
        """
        # Pesos por rango de cuerda (prioridad a cuerdas graves donde hay más confusión)
        guitar_ranges = [
            (70, 90, 2.0),    # 6ª cuerda (Mi grave) - prioridad alta
            (100, 120, 1.5),  # 5ª cuerda (La)
            (140, 160, 1.2),  # 4ª cuerda (Re)
            (190, 210, 1.0),  # 3ª cuerda (Sol)
            (240, 260, 1.0),  # 2ª cuerda (Si)
            (320, 340, 1.0),  # 1ª cuerda (Mi agudo)
        ]
        
        best_peak = peaks[0]  # Default: primer pico
        best_score = magnitude[peaks[0]]
        
        for peak in peaks:
            freq = frequencies[peak]
            mag = magnitude[peak]
            
            # Aplicar peso por rango
            weight = 1.0
            for low, high, w in guitar_ranges:
                if low <= freq <= high:
                    weight = w
                    break
            
            score = mag * weight
            if score > best_score:
                best_score = score
                best_peak = peak
        
        return best_peak
    
    def _parabolic_interpolation(self, frequencies, magnitude, peak_index):
        """Interpola parabólicamente alrededor del pico para mayor precisión."""
        if peak_index <= 0 or peak_index >= len(magnitude) - 1:
            return frequencies[peak_index]
        
        alpha = magnitude[peak_index - 1]
        beta = magnitude[peak_index]
        gamma = magnitude[peak_index + 1]
        
        # Evitar división por cero
        denom = alpha - 2*beta + gamma
        if abs(denom) < 1e-10:
            return frequencies[peak_index]
        
        p = 0.5 * (alpha - gamma) / denom
        df = frequencies[1] - frequencies[0] if len(frequencies) > 1 else 1
        
        return frequencies[peak_index] + p * df

    def get_harmonics(self, signal, sample_rate, fundamental, n_harmonics=5):
        """Detecta armónicos para validación."""
        frequencies, magnitude = self.compute_fft(signal, sample_rate)
        
        harmonics = []
        for i in range(1, n_harmonics + 1):
            harmonic_freq = fundamental * i
            mask = (frequencies >= harmonic_freq * 0.95) & (frequencies <= harmonic_freq * 1.05)
            if np.any(mask):
                harmonic_mag = np.max(magnitude[mask])
                harmonics.append({
                    'order': i,
                    'frequency': harmonic_freq,
                    'magnitude': float(harmonic_mag)
                })
        
        return harmonics