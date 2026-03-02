import numpy as np
from scipy.signal import stft

class FFTAnalyzer:

    def compute_fft(self, signal, sample_rate):
        """FFT simple para análisis de ventana única."""
        N = len(signal)
        spectrum = np.fft.fft(signal)
        magnitude = np.abs(spectrum)[:N // 2]
        frequencies = np.fft.fftfreq(N, 1 / sample_rate)[:N // 2]
        return frequencies, magnitude

    def compute_stft(self, signal, sample_rate, n_perseg=2048, overlap=0.5):

        noverlap = int(n_perseg * overlap)
        f, t, Zxx = stft(signal, sample_rate, nperseg=n_perseg, noverlap=noverlap, window='hann')
        return f, t, Zxx

    def dominant_frequency(self, signal, sample_rate):
        """
        Detecta frecuencia fundamental con validación de armónicos.
        """
        # Eliminar DC
        signal = signal - np.mean(signal)
        
        # Verificar nivel de señal
        max_amp = np.max(np.abs(signal))
        if max_amp < 0.001:
            return 0.0, 0.0, []
        
        # Aplicar ventana de Hann
        window = np.hanning(len(signal))
        signal_windowed = signal * window
        
        frequencies, magnitude = self.compute_fft(signal_windowed, sample_rate)
        
        # Rango útil para guitarra: 70Hz - 1500Hz
        mask = (frequencies >= 70) & (frequencies <= 1500)
        
        if not np.any(mask):
            return 0.0, 0.0, []
        
        filtered_freqs = frequencies[mask]
        filtered_mag = magnitude[mask]
        
        # Encontrar picos (no solo el máximo global)
        peaks = self._find_peaks(filtered_mag, threshold=0.3)
        
        if not peaks:
            peak_index = np.argmax(filtered_mag)
        else:
            # Seleccionar pico más prominente con armónicos coherentes
            peak_index = self._select_best_peak_with_harmonics(filtered_freqs, filtered_mag, peaks)
        
        # Interpolación parabólica para precisión sub-bin
        refined_freq = self._parabolic_interpolation(filtered_freqs, filtered_mag, peak_index)
        
        # Verificar armónicos
        harmonics = self._check_harmonics(refined_freq, filtered_freqs, filtered_mag)
        
        # Calcular confianza basada en relación señal/ruido y armónicos
        confidence = self._calculate_confidence(refined_freq, harmonics, filtered_freqs, filtered_mag)
        
        return float(refined_freq), float(confidence), harmonics

    def _find_peaks(self, magnitude, threshold=0.3, min_distance=10):
        """
        Encuentra picos locales en el espectro.
        
        Args:
            magnitude: Magnitud espectral
            threshold: Umbral relativo al máximo (0-1)
            min_distance: Distancia mínima entre picos (bins)
        """
        max_mag = np.max(magnitude)
        if max_mag == 0:
            return []
        
        threshold_abs = max_mag * threshold
        peaks = []
        
        for i in range(1, len(magnitude) - 1):
            if (magnitude[i] > magnitude[i-1] and 
                magnitude[i] > magnitude[i+1] and 
                magnitude[i] > threshold_abs):
                # Verificar distancia con picos ya encontrados
                if not peaks or all(abs(i - p) >= min_distance for p in peaks):
                    peaks.append(i)
        
        return peaks

    def _select_best_peak_with_harmonics(self, frequencies, magnitude, peaks):
        """
        Selecciona el pico que tenga armónicos coherentes (múltiplos enteros).
        """
        best_peak = peaks[0]
        best_score = magnitude[peaks[0]]
        
        for peak in peaks:
            freq = frequencies[peak]
            mag = magnitude[peak]
            
            # Buscar armónicos (2x, 3x, 4x la frecuencia)
            harmonic_score = 0
            for h in [2, 3, 4]:
                harmonic_freq = freq * h
                # Buscar pico cercano al armónico teórico (±5%)
                harmonic_mask = (frequencies >= harmonic_freq * 0.95) & (frequencies <= harmonic_freq * 1.05)
                if np.any(harmonic_mask):
                    harmonic_mag = np.max(magnitude[harmonic_mask])
                    harmonic_ratio = harmonic_mag / mag
                    if 0.1 < harmonic_ratio < 0.9:  # Armónico razonable
                        harmonic_score += harmonic_ratio
            
            # Puntuación combinada: magnitud + presencia de armónicos
            score = mag * (1 + harmonic_score)
            
            if score > best_score:
                best_score = score
                best_peak = peak
        
        return best_peak

    def _parabolic_interpolation(self, frequencies, magnitude, peak_index):
        """
        Interpolación parabólica para precisión sub-bin de la frecuencia pico.
        """
        if peak_index <= 0 or peak_index >= len(magnitude) - 1:
            return frequencies[peak_index]
        
        alpha = magnitude[peak_index - 1]
        beta = magnitude[peak_index]
        gamma = magnitude[peak_index + 1]
        
        denom = alpha - 2*beta + gamma
        if abs(denom) < 1e-10:
            return frequencies[peak_index]
        
        p = 0.5 * (alpha - gamma) / denom
        df = frequencies[1] - frequencies[0] if len(frequencies) > 1 else 1
        
        return frequencies[peak_index] + p * df

    def _check_harmonics(self, fundamental, frequencies, magnitude, n_harmonics=5):
        """
        Verifica la presencia de armónicos y retorna sus frecuencias y magnitudes.
        """
        harmonics = []
        
        for i in range(2, n_harmonics + 1):
            harmonic_freq = fundamental * i
            # Buscar en rango ±5%
            mask = (frequencies >= harmonic_freq * 0.95) & (frequencies <= harmonic_freq * 1.05)
            
            if np.any(mask):
                idx = np.argmax(magnitude[mask])
                harmonic_mag = magnitude[mask][idx]
                actual_freq = frequencies[mask][idx]
                
                harmonics.append({
                    'order': i,
                    'theoretical_freq': harmonic_freq,
                    'actual_freq': float(actual_freq),
                    'magnitude': float(harmonic_mag),
                    'deviation_cents': 1200 * np.log2(actual_freq / harmonic_freq)
                })
        
        return harmonics

    def _calculate_confidence(self, fundamental, harmonics, frequencies, magnitude):
        """
        Calcula confianza de la detección (0-1).
        Basado en: relación señal/ruido, claridad del pico, armónicos.
        """
        # Encontrar índice de la fundamental
        idx = np.argmin(np.abs(frequencies - fundamental))
        
        # Relación señal/ruido (pico vs promedio alrededor)
        local_region = magnitude[max(0, idx-20):min(len(magnitude), idx+20)]
        if len(local_region) > 0:
            signal_level = magnitude[idx]
            noise_level = np.mean(np.concatenate([local_region[:10], local_region[-10:]]))
            snr = signal_level / (noise_level + 1e-10)
            snr_score = min(1.0, snr / 10)  # Normalizar
        else:
            snr_score = 0.5
        
        # Puntuación por armónicos
        harmonic_score = min(1.0, len(harmonics) / 3)  # Ideal: 3+ armónicos
        
        # Combinar
        confidence = 0.6 * snr_score + 0.4 * harmonic_score
        
        return confidence

    def analyze_with_stft(self, signal, sample_rate, frame_duration=0.1, overlap=0.5):
        """
        Análisis completo con STFT: evolución temporal de la frecuencia.
        
        Returns:
            frames: Lista de dicts con frecuencia, confianza y tiempo por frame
        """
        f, t, Zxx = self.compute_stft(signal, sample_rate, 
                                       n_perseg=int(sample_rate * frame_duration),
                                       overlap=overlap)
        
        magnitude = np.abs(Zxx)
        frames = []
        
        for i, time_point in enumerate(t):
            frame_mag = magnitude[:, i]
            
            # Encontrar pico en este frame
            mask = (f >= 70) & (f <= 1500)
            if not np.any(mask):
                continue
            
            frame_f = f[mask]
            frame_mag_filtered = frame_mag[mask]
            
            peak_idx = np.argmax(frame_mag_filtered)
            peak_freq = frame_f[peak_idx]
            peak_mag = frame_mag_filtered[peak_idx]
            
            # Solo incluir si hay suficiente energía
            if peak_mag > np.mean(frame_mag_filtered) * 2:
                frames.append({
                    'time': float(time_point),
                    'frequency': float(peak_freq),
                    'magnitude': float(peak_mag)
                })
        
        return frames

    def is_guitar_sound(self, signal, sample_rate, min_confidence=0.6):
        """
        Valida si la señal es probablemente una guitarra (no ruido o voz).
        
        Criterios:
        - Frecuencia fundamental en rango de guitarra (70-1200Hz)
        - Presencia de armónicos característicos
        - Forma del espectro (decaimiento armónico típico)
        """
        freq, confidence, harmonics = self.dominant_frequency(signal, sample_rate)
        
        if confidence < min_confidence:
            return False, "Confianza baja", confidence
        
        if len(harmonics) < 2:
            return False, "Pocos armónicos (no parece cuerda)", confidence
        
        # Verificar decaimiento armónico típico de cuerda (más o menos monotónico)
        if len(harmonics) >= 2:
            magnitudes = [h['magnitude'] for h in harmonics]
            # En guitarra, usualmente magnitudes decrecen o son irregulares
            # pero no crecen fuertemente
            if magnitudes[1] > magnitudes[0] * 1.5:
                return False, "Patrón armónico atípico", confidence
        
        return True, "Probable guitarra", confidence