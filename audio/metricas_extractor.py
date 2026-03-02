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
        Evaluación completa de una nota objetivo.
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
        
        # Precisión normalizada (1 = perfecto, 0 = muy desafinado)
        # Consideramos 50 cents (medio semitono) como límite de aceptación
        precision = max(0, 1 - abs(error_cents) / 50)
        
        # Consistencia basada en estabilidad temporal (STFT)
        consistency = self._calculate_temporal_consistency(signal, sample_rate, detected_freq)
        
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

    def evaluate_sequence(self, signal, sample_rate, target_freq, frame_duration=0.1):
        """
        Evaluación frame por frame para análisis temporal completo.
        """
        frames = self.fft.analyze_with_stft(signal, sample_rate, frame_duration)
        
        if not frames:
            return self.evaluate(signal, sample_rate, target_freq)  # Fallback a método simple
        
        # Analizar cada frame válido
        valid_frames = []
        for frame in frames:
            # Calcular error en cents para cada frame
            error_cents = 1200 * np.log2(frame['frequency'] / target_freq)
            frame['error_cents'] = error_cents
            frame['precision'] = max(0, 1 - abs(error_cents) / 50)
            valid_frames.append(frame)
        
        if not valid_frames:
            return self.evaluate(signal, sample_rate, target_freq)
        
        # Métricas agregadas
        frequencies = [f['frequency'] for f in valid_frames]
        precisions = [f['precision'] for f in valid_frames]
        
        # Consistencia: inversamente proporcional a la variación de frecuencia
        freq_variation = np.std(frequencies) / np.mean(frequencies) if np.mean(frequencies) > 0 else 1
        consistency = max(0, 1 - freq_variation * 10)  # Escalar para que 10% var = 0 consistencia
        
        # Promedio de precisión
        avg_precision = np.mean(precisions)
        
        # Error promedio
        avg_freq = np.mean(frequencies)
        avg_error = abs(avg_freq - target_freq)
        avg_error_cents = 1200 * np.log2(avg_freq / target_freq) if avg_freq > 0 else 0
        
        return {
            "precision": float(avg_precision),
            "consistencia": float(consistency),
            "error": float(avg_error),
            "error_cents": float(avg_error_cents),
            "detected_freq": float(avg_freq),
            "nota_detectada": self.frequency_to_note(avg_freq),
            "confianza": float(np.mean([f.get('magnitude', 0) for f in valid_frames]) / max([f.get('magnitude', 1) for f in valid_frames])),
            "frames_analizados": len(valid_frames),
            "evolucion_temporal": valid_frames  # Para graficar
        }

    def _calculate_temporal_consistency(self, signal, sample_rate, detected_freq, n_segments=8):
        """
        Calcula consistencia basada en estabilidad de frecuencia temporal.
        Divide la señal en segmentos y mide variación de frecuencia detectada.
        """
        segment_length = len(signal) // n_segments
        frequencies = []
        
        for i in range(n_segments):
            start = i * segment_length
            end = start + segment_length
            segment = signal[start:end]
            
            # Solo analizar segmentos con suficiente energía
            if np.max(np.abs(segment)) > 0.01:
                freq, conf, _ = self.fft.dominant_frequency(segment, sample_rate)
                if freq > 0 and conf > 0.3:
                    frequencies.append(freq)
        
        if len(frequencies) < 2:
            return 0.0
        
        # Coeficiente de variación inverso
        mean_freq = np.mean(frequencies)
        std_freq = np.std(frequencies)
        
        if mean_freq == 0:
            return 0.0
        
        cv = std_freq / mean_freq
        consistency = max(0.0, 1.0 - (cv / 0.1))  # CV < 10% = consistencia alta
        
        return float(consistency)

    def frequency_to_note(self, freq):
        """Convierte frecuencia a nombre de nota musical."""
        if freq <= 0:
            return "N/A"
        
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        
        # Fórmula MIDI
        midi_number = round(69 + 12 * np.log2(freq / 440.0))
        
        # Validar rango
        if midi_number < 0 or midi_number > 127:
            return "Fuera de rango"
        
        note = note_names[midi_number % 12]
        octave = (midi_number // 12) - 1
        
        return f"{note}{octave}"

    def validate_guitar_string(self, signal, sample_rate, detected_freq):
        """Valida si es una cuerda de guitarra real."""
        return self.fft.is_guitar_sound(signal, sample_rate)