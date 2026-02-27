import numpy as np
from audio.FFT_analizador import FFTAnalyzer

class MetricsExtractor:

    def __init__(self):
        self.fft = FFTAnalyzer()

    def detect_pitch(self, signal, sample_rate):
        return self.fft.dominant_frequency(signal, sample_rate)

    def evaluate(self, signal, sample_rate, target_freq):
        detected_freq = self.detect_pitch(signal, sample_rate)
        
        # Si no detecta frecuencia (silencio o señal muy débil)
        if detected_freq == 0:
            return {
                "precision": 0.0,
                "consistencia": 0.0,
                "error": float(target_freq),
                "detected_freq": 0.0,
                "nota_detectada": "Silencio/Error"
            }
        
        # Calcular error y precisión
        error = abs(detected_freq - target_freq)
        precision = max(0, 1 - (error / target_freq))
        
        # 🔧 CORREGIDO: Consistencia basada en estabilidad de frecuencia temporal
        # Divide la señal en ventanas y mide qué tan estable es la frecuencia
        consistency = self._calculate_frequency_stability(signal, sample_rate)
        
        # Convertir a nota musical para feedback
        nota_detectada = self.frequency_to_note(detected_freq)
        
        return {
            "precision": float(precision),
            "consistencia": float(consistency),
            "error": float(error),
            "detected_freq": float(detected_freq),
            "nota_detectada": nota_detectada
        }
    
    def _calculate_frequency_stability(self, signal, sample_rate, n_segments=8):
        """
        Calcula la estabilidad de la frecuencia dividiendo la señal en segmentos.
        Una cuerda suelta bien tocada debe mantener frecuencia estable en el tiempo.
        """
        segment_length = len(signal) // n_segments
        frequencies = []
        
        for i in range(n_segments):
            start = i * segment_length
            end = start + segment_length
            segment = signal[start:end]
            
            # Solo analizar segmentos con suficiente energía (>1% del máximo)
            max_amp = np.max(np.abs(signal))
            if max_amp > 0 and np.max(np.abs(segment)) > (max_amp * 0.1):
                freq = self.fft.dominant_frequency(segment, sample_rate)
                if freq > 0:
                    frequencies.append(freq)
        
        if len(frequencies) < 2:
            return 0.0
        
        # Calcular coeficiente de variación (CV) inverso
        freq_mean = np.mean(frequencies)
        freq_std = np.std(frequencies)
        
        if freq_mean == 0:
            return 0.0
        
        cv = freq_std / freq_mean
        
        # Convertir CV a score de consistencia (0-1)
        # CV < 0.01 (1% de variación) = consistencia perfecta (1.0)
        # CV > 0.1 (10% de variación) = consistencia nula (0.0)
        consistency = max(0.0, 1.0 - (cv / 0.1))
        
        return float(consistency)

    def frequency_to_note(self, freq):
        """Convierte frecuencia a nombre de nota musical."""
        if freq <= 0:
            return "N/A"
        
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        
        # Fórmula MIDI: 69 = A4 (440Hz)
        midi_number = round(69 + 12 * np.log2(freq / 440.0))
        note = note_names[midi_number % 12]
        octave = (midi_number // 12) - 1
        
        return f"{note}{octave}"
    
    def validate_guitar_string(self, signal, sample_rate, detected_freq):
        """
        Valida si la frecuencia detectada corresponde a una cuerda de guitarra real
        verificando sus armónicos característicos.
        """
        harmonics = self.fft.get_harmonics(signal, sample_rate, detected_freq, n_harmonics=3)
        
        if len(harmonics) < 2:
            return False, "Pocos armónicos detectados"
        
        # Verificar que los armónicos sigan la relación esperada (2x, 3x, etc.)
        fundamental = harmonics[0]['magnitude'] if harmonics else 0
        if fundamental == 0:
            return False, "No se detectó fundamental"
        
        # Calcular relación señal/ruido de armónicos
        harmonic_ratios = [h['magnitude'] / fundamental for h in harmonics[1:]]
        avg_ratio = np.mean(harmonic_ratios) if harmonic_ratios else 0
        
        # Si hay armónicos claros, probablemente es una cuerda real
        is_valid = avg_ratio > 0.1  # Los armónicos deben ser al menos 10% del fundamental
        
        return is_valid, f"Armónicos válidos: {len(harmonics)}, ratio promedio: {avg_ratio:.3f}"