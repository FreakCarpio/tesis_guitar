import numpy as np
import sounddevice as sd
from audio.metricas_extractor import MetricsExtractor

def frequency_to_note(freq):
    """Convierte frecuencia a nota musical."""
    if freq <= 0:
        return "N/A"
    
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    midi_number = round(69 + 12 * np.log2(freq / 440.0))
    
    # Validar rango MIDI válido
    if midi_number < 0 or midi_number > 127:
        return "Fuera de rango"
    
    note = note_names[midi_number % 12]
    octave = (midi_number // 12) - 1
    
    return f"{note}{octave}"

def analyze_segment(signal, sample_rate, extractor, segment_duration=0.5):
    """
    Analiza la señal por segmentos para ver estabilidad temporal.
    Útil para detectar si la cuerda se desafina durante la grabación.
    """
    samples_per_segment = int(segment_duration * sample_rate)
    n_segments = len(signal) // samples_per_segment
    
    results = []
    for i in range(n_segments):
        start = i * samples_per_segment
        end = start + samples_per_segment
        segment = signal[start:end]
        
        # Verificar que el segmento tenga señal
        if np.max(np.abs(segment)) < 0.01:
            continue
            
        freq = extractor.detect_pitch(segment, sample_rate)
        if freq > 0:
            results.append({
                'time': i * segment_duration,
                'freq': freq,
                'note': frequency_to_note(freq)
            })
    
    return results

def main():
    # Configuración optimizada
    duration = 4  # segundos (más tiempo para cuerdas graves)
    sample_rate = 44100
    
    print("=" * 60)
    print(" DETECTOR DE CUERDAS SUELTAS - MODO REAL")
    print("=" * 60)
    print("\n Consejos para mejor detección:")
    print("   1. Usa auriculares o un micrófono externo de calidad")
    print("   2. Coloca el micrófono cerca del hueco de la guitarra (5-10 cm)")
    print("   3. Toca la cuerda con fuerza media-alta")
    print("   4. Mantén la cuerda vibrando durante toda la grabación")
    print("   5. Evita ruido de fondo (ventiladores, TV, conversaciones)")
    print("-" * 60)
    print("\nFrecuencias esperadas:")
    print("   6ª (Mi grave): ~82 Hz    |    5ª (La): ~110 Hz")
    print("   4ª (Re): ~147 Hz         |    3ª (Sol): ~196 Hz")
    print("   2ª (Si): ~247 Hz         |    1ª (Mi agudo): ~330 Hz")
    print("=" * 60)
    
    input("\n Presiona ENTER para iniciar grabación...")
    
    print("\n GRABANDO... Toca una cuerda suelta AHORA y manténla!")
    print(f"   (Duración: {duration} segundos)")
    
    try:
        # Configurar dispositivo de audio
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='float64',
            blocking=True
        )
        print("✅ Grabación completada")
        
    except Exception as e:
        print(f"\n Error de grabación: {e}")
        print(" Verifica que el micrófono esté conectado y configurado")
        return
    
    # Procesar
    signal = audio.flatten()
    
    # Análisis de nivel
    max_amp = np.max(np.abs(signal))
    rms = np.sqrt(np.mean(signal**2))
    
    print(f"\n ANÁLISIS DE SEÑAL:")
    print(f"   Pico máximo: {max_amp:.4f} (ideal: 0.3 - 0.9)")
    print(f"   RMS (promedio): {rms:.4f} (ideal: >0.05)")
    
    if max_amp < 0.05:
        print("\n SEÑAL MUY DÉBIL")
        print("   Posibles causas:")
        print("   • Micrófono muy lejos de la guitarra")
        print("   • Cuerda tocada muy suave")
        print("   • Micrófono con baja sensibilidad o filtro de corte")
        print("   • Problema de permisos del micrófono en Windows")
        return
    
    if max_amp > 0.99:
        print("\nSEÑAL DISTORSIONADA (clipping)")
        print("   Toca más suave o baja la ganancia del micrófono")
    
    # Análisis principal
    extractor = MetricsExtractor()
    detected_freq = extractor.detect_pitch(signal, sample_rate)
    
    print(f"\n RESULTADO PRINCIPAL:")
    print(f"   Frecuencia detectada: {detected_freq:.2f} Hz")
    
    if detected_freq == 0:
        print("\n No se pudo detectar frecuencia dominante")
        print("Intenta:")
        print("   • Tocar más fuerte cerca del micrófono")
        print("   • Verificar que el micrófono capture graves (prueba con 3ª-1ª cuerda)")
        print("   • Revisar configuración de privacidad de micrófono en Windows")
        return
    
    note = frequency_to_note(detected_freq)
    print(f"   Nota detectada: {note}")
    
    # Análisis por segmentos (ver estabilidad)
    print(f"\nANÁLISIS TEMPORAL (estabilidad):")
    segment_results = analyze_segment(signal, sample_rate, extractor)
    
    if len(segment_results) > 1:
        freqs = [r['freq'] for r in segment_results]
        std_freq = np.std(freqs)
        mean_freq = np.mean(freqs)
        
        print(f"   Frecuencia promedio: {mean_freq:.2f} Hz")
        print(f"   Desviación estándar: {std_freq:.2f} Hz")
        
        if std_freq < 2:
            print("Cuerda estable (buena técnica de ejecución)")
        elif std_freq < 5:
            print("Cuerda algo inestable (normal en cuerdas nuevas o desafinadas)")
        else:
            print("Cuerda muy inestable (¿cuerda desafinada o técnica irregular?)")
        
        # Mostrar evolución
        print(f"\n   Evolución en el tiempo:")
        for r in segment_results[:6]:  # Mostrar primeros 6 segmentos
            print(f"      t={r['time']:.1f}s: {r['freq']:.1f} Hz ({r['note']})")
    
    # Identificar cuerda
    cuerdas_ref = {
        82.41: ("6ª cuerda (Mi grave)", "E2"),
        110.00: ("5ª cuerda (La)", "A2"),
        146.83: ("4ª cuerda (Re)", "D3"),
        196.00: ("3ª cuerda (Sol)", "G3"),
        246.94: ("2ª cuerda (Si)", "B3"),
        329.63: ("1ª cuerda (Mi agudo)", "E4")
    }
    
    print(f"\nIDENTIFICACIÓN DE CUERDA:")
    
    # Encontrar cuerda más cercana
    cuerda_cercana = min(cuerdas_ref.keys(), key=lambda x: abs(x - detected_freq))
    diff = abs(detected_freq - cuerda_cercana)
    nombre_cuerda, nota_ref = cuerdas_ref[cuerda_cercana]
    
    print(f"   Cuerda más cercana: {nombre_cuerda}")
    print(f"   Frecuencia esperada: {cuerda_cercana:.2f} Hz ({nota_ref})")
    print(f"   Diferencia: {diff:.2f} Hz")
    
    if diff < 1:
        print("¡AFINACIÓN PERFECTA!")
    elif diff < 3:
        print("Afinación aceptable")
    elif diff < 10:
        print(f"Desafinada (~{diff/2:.1f} semitonos)")
    else:
        print(f"Muy desafinada o no es cuerda suelta")
        print(f"¿Quizás tocaste una nota presionada?")
    
    # Validación de armónicos
    print(f"\n🔍 VALIDACIÓN DE ARMÓNICOS:")
    is_valid, msg = extractor.validate_guitar_string(signal, sample_rate, detected_freq)
    print(f"   {msg}")

if __name__ == "__main__":
    main()