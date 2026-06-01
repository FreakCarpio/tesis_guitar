"""
Validador del pipeline DSP completo para afinación de guitarra acústica.

Proporciona:
1. Análisis de coherencia armónica (¿es una cuerda de guitarra?)
2. Diagnóstico de calidad de señal (SNR, clipping, ruido)
3. Reporte detallado de cada etapa del pipeline para tesis
4. Comparación antes/después del preprocesamiento

Para tesis:
Esta herramienta permite cuantificar objetivamente la mejora que
aporta cada etapa del pipeline, generando métricas comparables
que demuestran la efectividad del sistema.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from audio.audio_filters import AudioPreprocessor
from audio.noise_reduction import SpectralNoiseReducer, WienerFilterNoiseReducer
from audio.tuner_engine import PitchDetector, GuitarStringValidator


GUITAR_STRINGS_HZ = {
    "E2": 82.41, "A2": 110.00, "D3": 146.83,
    "G3": 196.00, "B3": 246.94, "E4": 329.63
}


class PipelineValidator:
    """
    Valida y diagnostica el pipeline completo de procesamiento.

    Analiza la señal antes y después de cada etapa para cuantificar
    la mejora en métricas clave: SNR, claridad espectral, estabilidad.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.validator = GuitarStringValidator()
        self.pitch_detector = PitchDetector(sample_rate=sample_rate)

    def analyze_signal_quality(self, signal: np.ndarray) -> Dict:
        """
        Analiza la calidad de la señal de audio.

        Returns:
            Dict con métricas de calidad
        """
        if len(signal) == 0:
            return {"error": "Señal vacía"}

        signal = signal.astype(np.float64)
        max_amp = np.max(np.abs(signal))
        rms = np.sqrt(np.mean(signal ** 2))
        crest_factor = max_amp / (rms + 1e-10)

        has_clipping = max_amp > 0.98
        is_too_quiet = max_amp < 0.01

        noise_estimate = np.percentile(np.abs(signal), 10)
        snr_estimate = 20 * np.log10((rms + 1e-10) / (noise_estimate + 1e-10))

        signal_energy = np.sum(signal ** 2)
        zero_crossings = np.sum(np.abs(np.diff(np.signbit(signal)))) / len(signal)

        return {
            "max_amplitude": float(max_amp),
            "rms": float(rms),
            "crest_factor": float(crest_factor),
            "has_clipping": has_clipping,
            "is_too_quiet": is_too_quiet,
            "snr_estimate_db": float(snr_estimate),
            "signal_energy": float(signal_energy),
            "zero_crossing_rate": float(zero_crossings),
            "calidad": self._quality_label(max_amp, snr_estimate, has_clipping)
        }

    def _quality_label(self, max_amp: float, snr_db: float,
                       clipping: bool) -> str:
        if clipping:
            return "Distorsionada (clipping)"
        if max_amp < 0.01:
            return "Demasiado débil"
        if snr_db > 20:
            return "Excelente"
        if snr_db > 10:
            return "Buena"
        if snr_db > 5:
            return "Aceptable"
        return "Ruido excesivo"

    def compare_pipeline_stages(self, original: np.ndarray) -> Dict:
        """
        Compara señal antes y después del pipeline completo.

        Para tesis: Genera métricas comparativas que demuestran
        cuantitativamente la mejora del preprocesamiento.

        Args:
            original: Señal cruda original

        Returns:
            Dict con comparación antes/después
        """
        preprocessor = AudioPreprocessor(sample_rate=self.sample_rate)
        processed = preprocessor.process(original.copy())

        original_quality = self.analyze_signal_quality(original)
        processed_quality = self.analyze_signal_quality(processed)

        orig_freq, orig_conf, _ = self.pitch_detector.detect(original)
        proc_freq, proc_conf, _ = self.pitch_detector.detect(processed)

        return {
            "original": {
                "quality": original_quality,
                "frecuencia_detectada": float(orig_freq) if orig_freq > 0 else 0,
                "confianza": float(orig_conf)
            },
            "procesado": {
                "quality": processed_quality,
                "frecuencia_detectada": float(proc_freq) if proc_freq > 0 else 0,
                "confianza": float(proc_conf)
            },
            "mejora_snr_db": float(
                processed_quality.get("snr_estimate_db", 0) -
                original_quality.get("snr_estimate_db", 0)
            ),
            "mejora_confianza": float(proc_conf - orig_conf)
        }

    def validate_guitar_note(self, signal: np.ndarray,
                             sample_rate: int) -> Dict:
        """
        Valida si la señal corresponde a una nota de guitarra.

        Analiza:
        - Coherencia armónica
        - Proximidad a frecuencias de cuerdas
        - Estabilidad temporal

        Returns:
            Dict con resultado de validación y confianza
        """
        freq, confidence, rms = self.pitch_detector.detect(signal)

        if freq <= 0:
            return {
                "es_nota_guitarra": False,
                "confianza": 0.0,
                "razon": "No se detectó frecuencia"
            }

        validation = self.validator.validate(signal, sample_rate, freq)

        string_distances = {}
        for name, s_freq in GUITAR_STRINGS_HZ.items():
            cents_diff = 1200 * np.log2(freq / s_freq)
            string_distances[name] = {
                "distancia_cents": float(cents_diff),
                "frecuencia_cuerda": s_freq,
                "cuerda_cercana": abs(cents_diff) < 50
            }

        closest_string = min(string_distances.keys(),
                             key=lambda k: abs(string_distances[k]["distancia_cents"]))

        note_info = {
            "nota": frequency_to_note_info(freq)["nota_completa"],
            "frecuencia": float(freq),
            "confianza_deteccion": float(confidence)
        }

        es_guitarra = (
            validation["es_guitarra"] and
            string_distances[closest_string]["cuerda_cercana"] and
            confidence > 0.3
        )

        return {
            "es_nota_guitarra": es_guitarra,
            "confianza_total": float(min(1.0, confidence * 0.4 + validation["confianza"] * 0.6)),
            "note_info": note_info,
            "validacion_armonica": validation,
            "cuerda_mas_cercana": closest_string,
            "distancias_cuerdas": string_distances,
            "razon": "Nota de guitarra válida" if es_guitarra else "No supera validación armónica"
        }


def frequency_to_note_info(freq: float) -> Dict:
    """Convierte frecuencia a nota musical."""
    if freq <= 0:
        return {"nota_completa": "N/A", "nota": "N/A", "octava": 0,
                "freq_teorica": 0, "cents": 0}

    NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    midi = round(69 + 12 * np.log2(freq / 440.0))

    if midi < 0 or midi > 127:
        return {"nota_completa": "Fuera de rango", "nota": "N/A",
                "octava": 0, "freq_teorica": 0, "cents": 0}

    nota = NOTE_NAMES[midi % 12]
    octava = (midi // 12) - 1
    freq_teorica = 440.0 * (2.0 ** ((midi - 69) / 12))
    cents = 1200.0 * np.log2(freq / freq_teorica)

    return {
        "nota_completa": f"{nota}{octava}",
        "nota": nota,
        "octava": octava,
        "freq_teorica": freq_teorica,
        "cents": cents
    }
