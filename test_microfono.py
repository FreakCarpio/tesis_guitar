import numpy as np
import sounddevice as sd
from audio.audio_processor import AudioProcessor
from audio.metricas_extractor import MetricsExtractor

def frequency_to_note(freq):
    """Convierte frecuencia a nota musical."""
    if freq <= 0:
        return "N/A"
    
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    midi_number = round(69 + 12 * np.log2(freq / 440.0))
    
    if midi_number < 0 or midi_number > 127:
        return "Fuera de rango"
    
    note = note_names[midi_number % 12]
    octave = (midi_number // 12) - 1
    
    return f"{note}{octave}"

def main():
    # Configuración
    duration = 4  # segundos
    sample_rate = 44100
    
    print("=" * 60)
    print("DETECTOR DE CUERDAS DE GUITARRA - VERSIÓN ROBUSTA")
    print("=" * 60)
    print("\nFrecuencias esperadas de cuerdas sueltas:")
    print("6ª (Mi grave): 82.41 Hz  |  5ª (La): 110.00 Hz")
    print("4ª (Re): 146.83 Hz       |  3ª (Sol): 196.00 Hz")
    print("2ª (Si): 246.94 Hz       |  1ª (Mi agudo): 329.63 Hz")
    print("-" * 60)
    
    # Inicializar procesador con calibración de silencio
    print("\n Inicializando sistema...")
    try:
        processor = AudioProcessor(sample_rate=sample_rate, calibration_duration=1.0)
    except Exception as e:
        print(f"Error de inicialización: {e}")
        print("Continuando sin calibración automática...")
        processor = None
    
    input("\nPresiona ENTER para iniciar grabación...")
    
    # Opciones de prueba
    print("\nOpciones:")
    print("1. Detección libre (sin nota objetivo)")
    print("2. Evaluar contra nota específica")
    opcion = input("Selecciona (1/2) [1]: ").strip() or "1"
    
    if opcion == "2":
        print("\nNotas disponibles:")
        notas = {
            '1': ('E2', 82.41), '2': ('A2', 110.00), '3': ('D3', 146.83),
            '4': ('G3', 196.00), '5': ('B3', 246.94), '6': ('E4', 329.63)
        }
        for k, (nombre, freq) in notas.items():
            print(f"  {k}. {nombre} ({freq} Hz)")
        
        seleccion = input("\nSelecciona cuerda (1-6) [1]: ").strip() or "1"
        nota_obj, freq_obj = notas.get(seleccion, ('E2', 82.41))
        print(f"\nObjetivo: {nota_obj} ({freq_obj} Hz)")
    else:
        nota_obj, freq_obj = None, None
    
    # Grabar y analizar
    print(f"\nGRABANDO... Toca una cuerda ahora!")
    print(f"   (Duración máxima: {duration}s, se detiene en silencio)")
    
    try:
        if processor and opcion == "1":
            # Usar procesador con calibración
            result = processor.record_and_analyze(
                duration=duration,
                target_freq=None,
                auto_stop=True
            )
            
            print(f"\n{'='*50}")
            print("RESULTADO DEL ANÁLISIS")
            print(f"{'='*50}")
            
            if result.get('es_guitarra', False):
                print(f"Señal válida detectada")
            else:
                print(f"{result.get('message', 'Señal no identificada como guitarra')}")
            
            print(f"Frecuencia detectada: {result['detected_freq']:.2f} Hz")
            print(f"Nota musical: {result['nota']}")
            print(f"Confianza: {result['confianza']:.2%}")
            print(f"Armónicos detectados: {result['armonicos']}")
            
            # Identificar cuerda más cercana
            if result['detected_freq'] > 0:
                cuerdas_ref = {
                    82.41: "6ª cuerda (Mi grave)",
                    110.00: "5ª cuerda (La)",
                    146.83: "4ª cuerda (Re)",
                    196.00: "3ª cuerda (Sol)",
                    246.94: "2ª cuerda (Si)",
                    329.63: "1ª cuerda (Mi agudo)"
                }
                cuerda_cercana = min(cuerdas_ref.keys(), 
                                    key=lambda x: abs(x - result['detected_freq']))
                diff = abs(result['detected_freq'] - cuerda_cercana)
                
                if diff < 10:
                    print(f"\nProbablemente es: {cuerdas_ref[cuerda_cercana]}")
                    if diff < 2:
                        print("¡Afinación correcta!")
                    else:
                        print(f"Desafinada por {diff:.2f} Hz")
                        
        else:
            # Grabación tradicional para análisis detallado
            audio = sd.rec(int(duration * sample_rate),
                          samplerate=sample_rate,
                          channels=1,
                          dtype='float64')
            sd.wait()
            print("Grabación completada")
            
            signal = audio.flatten()
            
            # Análisis con métricas extractor
            extractor = MetricsExtractor()
            
            if freq_obj:
                # Evaluación contra objetivo
                metrics = extractor.evaluate_sequence(signal, sample_rate, freq_obj)
                
                print(f"\n{'='*50}")
                print(f"EVALUACIÓN: {nota_obj} ({freq_obj} Hz)")
                print(f"{'='*50}")
                print(f"Frecuencia promedio: {metrics['detected_freq']:.2f} Hz")
                print(f"Nota detectada: {metrics['nota_detectada']}")
                print(f"Precisión: {metrics['precision']:.2%}")
                print(f"Consistencia: {metrics['consistencia']:.2%}")
                print(f"Error: {metrics['error']:.2f} Hz ({metrics['error_cents']:.1f} cents)")
                print(f"Confianza: {metrics['confianza']:.2%}")
                print(f"Frames analizados: {metrics['frames_analizados']}")
                
                # Validación de guitarra
                is_guitar, msg, conf = extractor.validate_guitar_string(signal, sample_rate, metrics['detected_freq'])
                print(f"\n🔍 Validación: {msg} (confianza: {conf:.2%})")
                
                # Feedback
                if metrics['precision'] > 0.9:
                    print("\n¡Excelente ejecución!")
                elif metrics['precision'] > 0.7:
                    print("\n Buena ejecución, pequeños ajustes necesarios")
                else:
                    print("\nPractica más lentamente, enfócate en la afinación")
                    
            else:
                # Detección libre
                freq, conf, harmonics = extractor.detect_pitch(signal, sample_rate)
                note = extractor.frequency_to_note(freq)
                
                print(f"\n{'='*50}")
                print("DETECCIÓN LIBRE")
                print(f"{'='*50}")
                print(f"Frecuencia: {freq:.2f} Hz")
                print(f"Nota: {note}")
                print(f"Confianza: {conf:.2%}")
                print(f"Armónicos: {len(harmonics)}")
                
                is_guitar, msg, _ = extractor.validate_guitar_string(signal, sample_rate, freq)
                print(f"Validación: {msg}")
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()