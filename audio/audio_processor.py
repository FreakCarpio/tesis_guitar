import numpy as np
import sounddevice as sd
from audio.FFT_analizador import FFTAnalyzer
from audio.metricas_extractor import MetricsExtractor
from scipy.io.wavfile import write
import datetime

def save_sesiones(signal, sample_rate):
    filename = f"sesiones/sesion_{datetime.datetime.now().timestamp()}.wav"
    write(filename, sample_rate, signal.astype("int16"))
    print(f"Sesión guardada en: {filename}")
    return filename

class AudioProcessor:
    """
    Procesador de audio completo con umbral adaptativo de silencio.
    """
    def __init__(self, sample_rate=44100, calibration_duration=1.0):
        self.sample_rate = sample_rate
        self.fft = FFTAnalyzer()
        self.extractor = MetricsExtractor()
        
        # Umbral adaptativo
        self.noise_floor = 0.0
        self.threshold_multiplier = 3.0  # Umbral = ruido * 3
        
        # Calibrar umbral al inicializar
        self._calibrate_silence(calibration_duration)
    
    def _calibrate_silence(self, duration=1.0):
        """
        Calibra el umbral de silencio midiendo el ruido ambiente.
        """
        print(f"Calibrando silencio ({duration}s)... No toques nada.")
        
        audio = sd.rec(
                       int(duration * self.sample_rate),
                       samplerate=self.sample_rate,
                       channels=1,
                       dtype='float64',
                       device=1
        )
        sd.wait()
        
        signal = audio.flatten()
        save_sesiones(signal, self.sample_rate) # Guardar sesión
        # continuar análisis
        
        # Estimar piso de ruido (percentil 50 para ser robusto a picos)
        self.noise_floor = np.percentile(np.abs(signal), 50)
        
        print(f"Ruido ambiente: {self.noise_floor:.6f}")
        print(f"Umbral activación: {self.get_threshold():.6f}")
    
    def get_threshold(self):
        """Retorna el umbral actual de activación."""
        return self.noise_floor * self.threshold_multiplier
    
    def has_signal(self, signal, threshold=None):
        """
        Detecta si hay señal válida (no solo silencio).
        """
        if threshold is None:
            threshold = self.get_threshold()
        
        # Usar percentil 90 para ser robusto a picos breves
        signal_level = np.percentile(np.abs(signal), 90)
        
        return signal_level > threshold
    
    def record_and_analyze(self, duration, target_freq=None, auto_stop=True):
        """
        Graba y analiza audio con detección inteligente.
        
        Args:
            duration: Duración máxima de grabación
            target_freq: Frecuencia objetivo (opcional)
            auto_stop: Detener si hay silencio prolongado
        
        Returns:
            dict: Resultados del análisis
        """
        print(f"Grabando (max {duration}s)...")
        
        # Grabar en chunks para procesamiento en tiempo real
        chunk_duration = 0.5  # segundos
        chunk_samples = int(chunk_duration * self.sample_rate)
        max_chunks = int(duration / chunk_duration)
        
        all_frames = []
        silence_chunks = 0
        max_silence_chunks = 3  # Detener después de 1.5s de silencio
        
        for i in range(max_chunks):
            # Grabar chunk
            chunk = sd.rec(chunk_samples, 
                          samplerate=self.sample_rate,
                          channels=1,
                          dtype='float64',
                          device=1,
                          blocking=True)
            signal_chunk = chunk.flatten()
            all_frames.append(signal_chunk)
            
            # Verificar si hay señal
            if self.has_signal(signal_chunk):
                silence_chunks = 0

                freq, conf, harmonics = self.fft.dominant_frequency(signal_chunk, self.sample_rate)
                if freq > 0:
                    all_frames.append({'frequency': freq, 'confidence': conf, 'harmonics': len(harmonics)})
                    note = self.extractor.frequency_to_note(freq)
                    print(f"  Detectado: {freq:.1f} Hz ({note})", end='\r')
            else:
                silence_chunks += 1
                print(f"  [Silencio {silence_chunks}/{max_silence_chunks}]", end='\r')

                if auto_stop and silence_chunks >= max_silence_chunks:
                    print("\nDeteniendo por silencio...")
                    break
        
        print() 
        
        # Concatenar todo el audio grabado para análisis final
        # (En implementación real, guardaríamos los chunks)
        if all_frames:
         full_audio = np.concatenate(all_frames)
        else:
         full_audio = np.zeros(1000)
         
         # Guardar la sesión real grabada
        save_sesiones(full_audio, self.sample_rate)
        
        # Análisis final
        if target_freq:
            return self.extractor.evaluate_sequence(full_audio, self.sample_rate, target_freq)
        else:
            # Solo detectar nota dominante
            freq, conf, harmonics = self.extractor.detect_pitch(full_audio, self.sample_rate)
            return {
                "detected_freq": freq,
                "confianza": conf,
                "nota": self.extractor.frequency_to_note(freq),
                "armonicos": len(harmonics),
                "es_guitarra": self.extractor.validate_guitar_string(full_audio, self.sample_rate, freq)[0]
            }
    
    def analyze_file(self, file_path, target_freq=None):
        """
        Analiza un archivo de audio (para pruebas con grabaciones).
        """
        # Requiere scipy.io.wavfile o librosa
        try:
            from scipy.io import wavfile
            sample_rate, data = wavfile.read(file_path)
            
            # Convertir a mono y float
            if len(data.shape) > 1:
                data = data.mean(axis=1)
            data = data.astype(np.float64) / np.max(np.abs(data))
            
            if target_freq:
                return self.extractor.evaluate_sequence(data, sample_rate, target_freq)
            else:
                freq, conf, harmonics = self.extractor.detect_pitch(data, sample_rate)
                return {
                    "detected_freq": freq,
                    "confianza": conf,
                    "nota": self.extractor.frequency_to_note(freq)
                }
                
        except ImportError:
            print("Instala scipy para leer archivos WAV")
            return None

# Función de conveniencia para pruebas rápidas
def quick_test():
    """Prueba rápida del procesador de audio."""
    processor = AudioProcessor()
    
    # Detectar nota libre (sin objetivo)
    result = processor.record_and_analyze(duration=3.0, target_freq=None)
    
    print("\n=== RESULTADO ===")
    for key, value in result.items():
        if key != 'evolucion_temporal':
            print(f"{key}: {value}")
    
    return result

if __name__ == "__main__":
    quick_test()