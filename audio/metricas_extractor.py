import numpy as np
from audio.FFT_analizador import FFTAnalyzer

class MetricsExtractor:
    """extrae métricas del audio para el afinador"""

    def __init__(self):
        self.fft = FFTAnalyzer()

    def detect_pitch(self, signal, sample_rate):
        """saco la frecuencia principal"""
        freq, confidence, harmonics = self.fft.dominant_frequency(signal, sample_rate)
        return freq, confidence, harmonics

    def evaluate(self, signal, sample_rate, target_freq):
        """evaluo una nota contra la objetivo"""
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
        
        # error en hz y cents
        error = abs(detected_freq - target_freq)
        error_cents = 1200 * np.log2(detected_freq / target_freq) if detected_freq > 0 else 0
        
        # precisión: 50 cents es el límite
        precision = max(0, 1 - abs(error_cents) / 50)
        
        # consistencia basada en confianza
        consistency = confidence
        
        # convierto a nota musical
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
        """evaluo por segmentos para mayor precisión"""
        segment_length = len(signal) // n_segments
        frequencies = []
        confidences = []
        
        for i in range(n_segments):
            start = i * segment_length
            end = start + segment_length
            segment = signal[start:end]
            
            # solo analizo segmentos con energía
            seg_max = np.max(np.abs(segment))
            if seg_max > 0.01:
                freq, conf, _ = self.detect_pitch(segment, sample_rate)
                if freq > 0 and conf > 0.3:
                    frequencies.append(freq)
                    confidences.append(conf)
        
        if not frequencies:
            return self.evaluate(signal, sample_rate, target_freq)
        
        # métricas agregadas
        mean_freq = np.mean(frequencies)
        std_freq = np.std(frequencies)
        
        # consistencia: menor variación = mejor
        cv = std_freq / mean_freq if mean_freq > 0 else 1
        consistency = max(0, 1 - cv * 5)
        
        # error promedio
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
        """convierto frecuencia a nota"""
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
        """verifico si es una cuerda válida"""
        freq, confidence, harmonics = self.detect_pitch(signal, sample_rate)
        
        # rango de guitarra y confianza
        is_valid = (
            70 <= detected_freq <= 1200 and
            confidence > 0.5 and
            len(harmonics) >= 1
        )
        
        msg = "Válida" if is_valid else "Dudosa"
        
        return is_valid, msg, confidence

    # plantillas de acordes
    CHORD_TEMPLATES = {
        'Mayor': [0, 4, 7],
        'Menor': [0, 3, 7],
        'Séptima': [0, 4, 7, 10],
        'Menor7': [0, 3, 7, 10],
        'Quinta': [0, 7],
    }

    def detect_picos(self, signal, sample_rate, min_freq=60, max_freq=1200, threshold=0.1):
        """detecto picos de frecuencia para acordes"""
        freqs, magnitude = self.fft.compute_fft(signal, sample_rate)

        if np.max(magnitude) > 0:
            magnitude = magnitude / np.max(magnitude)

        mask = (freqs >= min_freq) & (freqs <= max_freq) & (magnitude > threshold)
        freqs_filtered = freqs[mask]
        mags_filtered = magnitude[mask]

        if len(freqs_filtered) == 0:
            return []

        # busco picos locales
        picos = []
        for i in range(1, len(mags_filtered) - 1):
            if mags_filtered[i] > mags_filtered[i-1] and mags_filtered[i] > mags_filtered[i+1]:
                if mags_filtered[i] > threshold:
                    picos.append({
                        'freq': float(freqs_filtered[i]),
                        'magnitude': float(mags_filtered[i]),
                        'note': self.frequency_to_note(freqs_filtered[i])
                    })

        return sorted(picos, key=lambda x: x['magnitude'], reverse=True)[:6]

    def identify_chord(self, signal, sample_rate):
        """identifico el acorde"""
        picos = self.detect_picos(signal, sample_rate)

        if len(picos) < 2:
            return None

        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        
        # extraigo notas únicas
        notas_unicas = []
        for pico in picos:
            nota = pico['note']
            if nota and nota != "N/A" and nota != "Fuera de rango":
                nota_base = nota[:-1] if nota[-1].isdigit() else nota
                if nota_base not in notas_unicas:
                    notas_unicas.append(nota_base)

        if len(notas_unicas) < 2:
            return None

        nota_indices = []
        for n in notas_unicas:
            try:
                nota_indices.append(note_names.index(n))
            except ValueError:
                continue

        if len(nota_indices) < 2:
            return None

        # comparo con plantillas de acordes
        for raiz in nota_indices:
            for tipo, intervalos in self.CHORD_TEMPLATES.items():
                notas_acorde = sorted([(raiz + i) % 12 for i in intervalos])
                notas_encontradas = sorted(nota_indices)

                if all(n in notas_encontradas for n in notas_acorde):
                    sufijo = '' if tipo == 'Mayor' else 'm' if tipo == 'Menor' else '7' if tipo == 'Séptima' else 'm7' if tipo == 'Menor7' else '5'
                    return {
                        'nombre': f"{note_names[raiz]}{sufijo}",
                        'tipo': tipo,
                        'raiz': note_names[raiz],
                        'notas': notas_unicas,
                        'picos': picos
                    }

        return {'nombre': '-'.join(notas_unicas), 'tipo': 'Desconocido', 'raiz': notas_unicas[0], 'notas': notas_unicas, 'picos': picos}

    def identify_chord_from_notes(self, notas: list) -> dict:
        """
        Identifica un acorde desde una lista de notas
        
        Este método permite identificar un acorde pasando
        directamente las notas musicales, sin necesidad
        de procesar un archivo de audio.
        
        Args:
            notas: Lista de notas (ej: ["A", "C#", "E"])
            
        Returns:
            Diccionario con información del acorde
        """
        if not notas or len(notas) < 2:
            return None
            
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        
        # Convierto notas a índices
        nota_indices = []
        for n in notas:
            try:
                # Quitooctava si la tiene
                nota_limpia = n[:-1] if n[-1].isdigit() else n
                nota_limpia = nota_limpia.replace("#", "S").replace("S", "#")
                if "#" in nota_limpia:
                    nota_limpia = nota_limpia.replace("#", "S")
                    nota_limpia = nota_limpia.replace("S", "#")
                nota_indices.append(note_names.index(nota_limpia))
            except ValueError:
                continue
                
        if len(nota_indices) < 2:
            return {'nombre': '-'.join(notas), 'tipo': 'Desconocido', 'raiz': notas[0], 'notas': notas}
        
        # Comparo con plantillas de acordes
        for raiz in nota_indices:
            for tipo, intervalos in self.CHORD_TEMPLATES.items():
                notas_acorde = sorted([(raiz + i) % 12 for i in intervalos])
                notas_encontradas = sorted(nota_indices)
                
                if all(n in notas_encontradas for n in notas_acorde):
                    sufijo = '' if tipo == 'Mayor' else 'm' if tipo == 'Menor' else '7' if tipo == 'Séptima' else 'm7' if tipo == 'Menor7' else '5'
                    return {
                        'nombre': f"{note_names[raiz]}{sufijo}",
                        'tipo': tipo,
                        'raiz': note_names[raiz],
                        'notas': notas
                    }
                    
        return {'nombre': '-'.join(notas), 'tipo': 'Desconocido', 'raiz': notas[0], 'notas': notas}