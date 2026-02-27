import numpy as np
import sounddevice as sd
from audio.metricas_extractor import MetricsExtractor

def frequency_to_note(freq):
    """Convierte frecuencia a nota musical."""
    if freq <= 0:
        return "N/A"
    
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    midi_number = round(69 + 12 * np.log2(freq / 440.0))
    note = note_names[midi_number % 12]
    octave = (midi_number // 12) - 1
    return f"{note}{octave}"

def main():
    # Configuración
    duration = 3  # segundos
    sample_rate = 44100
    
    print("=" * 50)
    print("DETECTOR DE CUERDAS DE GUITARRA")
    print("=" * 50)
    print("\nFrecuencias esperadas de cuerdas sueltas:")
    print("6ª (Mi grave): 82.41 Hz  |  5ª (La): 110.00 Hz")
    print("4ª (Re): 146.83 Hz       |  3ª (Sol): 196.00 Hz")
    print("2ª (Si): 246.94 Hz       |  1ª (Mi agudo): 329.63 Hz")
    print("-" * 50)
    
    input("\nPresiona ENTER cuando estés listo para grabar...")
    
    print("\n Grabando... Toca una cuerda suelta ahora!")
    print("   (Mantén la cuerda pulsada durante la grabación)")
    
    try:
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='float64'
        )
        sd.wait()
        print("Grabación completa.")
        
    except Exception as e:
        print(f" Error de grabación: {e}")
        return
    
    # Procesar señal
    signal = audio.flatten()
    
    # Verificar nivel de entrada
    max_amp = np.max(np.abs(signal))
    print(f"\nNivel de entrada: {max_amp:.4f} (ideal: >0.1)")
    
    if max_amp < 0.01:
        print("Señal muy débil. Verifica que el micrófono esté conectado y cerca de la guitarra.")
        return
    
    # Analizar
    extractor = MetricsExtractor()
    detected_freq = extractor.detect_pitch(signal, sample_rate)
    
    print(f"\n Frecuencia detectada: {detected_freq:.2f} Hz")
    
    if detected_freq > 0:
        note = frequency_to_note(detected_freq)
        print(f"🎵 Nota detectada: {note}")
        
        # Validar armónicos
        is_valid, msg = extractor.validate_guitar_string(signal, sample_rate, detected_freq)
        print(f" Validación: {'Válida' if is_valid else '' + msg}")
        
        # Identificar cuerda probable
        cuerdas = {
            82.41: "6ª cuerda (Mi grave)",
            110.00: "5ª cuerda (La)",
            146.83: "4ª cuerda (Re)",
            196.00: "3ª cuerda (Sol)",
            246.94: "2ª cuerda (Si)",
            329.63: "1ª cuerda (Mi agudo)"
        }
        
        cuerda_cercana = min(cuerdas.keys(), key=lambda x: abs(x - detected_freq))
        error_cuerda = abs(detected_freq - cuerda_cercana)
        
        if error_cuerda < 5:  # Si está dentro de 5Hz
            print(f"🎸 Probablemente es la: {cuerdas[cuerda_cercana]}")
            if error_cuerda > 2:
                print(f"Desafinada por {error_cuerda:.2f} Hz")
            else:
                print(f" Afinación correcta")
        else:
            print(f"No coincide con cuerdas sueltas estándar")
            
    else:
        print(" No se detectó frecuencia dominante. Intenta de nuevo tocando más fuerte.")

if __name__ == "__main__":
    main()