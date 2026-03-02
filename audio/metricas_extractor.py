import numpy as np
from audio.FFT_analizador import FFTAnalyzer

class MetricsExtractor:

    def __init__(self):
        self.fft = FFTAnalyzer()

    def detect_pitch(self, signal, sample_rate):
        """Detecta frecuencia fundamental con confianza."""
        freq, confidence, harmonics = self.fft.dominant_frequency(signal, sample_rate)
        return freq, confidence, harmonics

    def evaluate(self, signal, sample_rate, target_freq):
        """
        Evaluación completa de una nota objetivo (método simple).
        """
        detected_freq, confidence, harmonics = self.detect_pitch(signal, sample_rate)
        
        if detected_freq == 0 or confidence < 0.3:
            return {
                "precision": 0.0,
                "consistencia": 0.0,
                "error": float(target_freq),
                "error_cents": 0.0,
                "detected_freq": 0.0,
                "nota_detectada": "Silencio/Error",
                "confianza": 0.0,
                "armonicos": []
            }
        
        # Error en Hz y cents
        error = abs(detected_freq - target_freq)
        error_cents = 1200 * np.log2(detected_freq / target_freq) if detected_freq > 0 else 0
        
        # Precisión normalizada (50 cents = límite de aceptación)
        precision = max(0, 1 - abs(error_cents) / 50)
        
        # Consistencia simple basada en relación señal/ruido
        consistency = confidence
        
        # Convertir a nota musical
        nota_detectada = self.frequency_to_note(detected_freq)
        
        return {
            "precision": float(precision),
            "consistencia": float(consistency),
            "error": float(error),
            "error_cents": float(error_cents),
            "detected_freq": float(detected_freq),
            "nota_detectada": nota_detectada,
            "confianza": float(confidence),
            "armonicos": harmonics
        }

    def evaluate_sequence(self, signal, sample_rate, target_freq, n_segments=8):
        """
        Evaluación por segmentos temporales (versión simplificada y robusta).
        """
        segment_length = len(signal) // n_segments
        frequencies = []
        confidences = []
        
        for i in range(n_segments):
            start = i * segment_length
            end = start + segment_length
            segment = signal[start:end]
            
            # Solo analizar segmentos con suficiente energía
            seg_max = np.max(np.abs(segment))
            if seg_max > 0.01:
                freq, conf, _ = self.detect_pitch(segment, sample_rate)
                if freq > 0 and conf > 0.3:
                    frequencies.append(freq)
                    confidences.append(conf)
        
        if not frequencies:
            # Fallback: analizar señal completa
            return self.evaluate(signal, sample_rate, target_freq)
        
        # Calcular métricas agregadas
        mean_freq = np.mean(frequencies)
        std_freq = np.std(frequencies)
        
        # Consistencia: inversamente proporcional a la variación
        cv = std_freq / mean_freq if mean_freq > 0 else 1
        consistency = max(0, 1 - cv * 5)
        
        # Error promedio
        error = abs(mean_freq - target_freq)
        error_cents = 1200 * np.log2(mean_freq / target_freq) if mean_freq > 0 else 0
        precision = max(0, 1 - abs(error_cents) / 50)
        
        return {
            "precision": float(precision),
            "consistencia": float(consistency),
            "error": float(error),
            "error_cents": float(error_cents),
            "detected_freq": float(mean_freq),
            "nota_detectada": self.frequency_to_note(mean_freq),
            "confianza": float(np.mean(confidences)),
            "frames_analizados": len(frequencies)
        }

    def frequency_to_note(self, freq):
        """Convierte frecuencia a nombre de nota musical."""
        if freq <= 0:
            return "N/A"
        
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        midi_number = round(69 + 12 * np.log2(freq / 440.0))
        
        if midi_number < 0 or midi_number > 127:
            return "Fuera de rango"
        
        note = note_names[midi_number % 12]
        octave = (midi_number // 12) - 1
        
        return f"{note}{octave}"

    def validate_guitar_string(self, signal, sample_rate, detected_freq):
        """
        Validación simplificada: verificar rango y confianza.
        """
        freq, confidence, harmonics = self.detect_pitch(signal, sample_rate)
        
        # Criterios simples
        is_valid = (
            70 <= detected_freq <= 1200 and  # Rango de guitarra
            confidence > 0.5 and              # Confianza razonable
            len(harmonics) >= 1               # Al menos un armónico
        )
        
        msg = "Válida" if is_valid else "Dudosa"
        
        return is_valid, msg, confidence