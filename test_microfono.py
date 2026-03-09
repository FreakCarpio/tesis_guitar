import numpy as np
import sounddevice as sd
from audio.metricas_extractor import MetricsExtractor

def main():
    duration = 3
    sample_rate = 44100

    print("=" * 60)
    print("DETECTOR DE CUERDAS DE GUITARRA - VERSION ESTABLE")
    print("=" * 60)

    input("\nPresiona ENTER para iniciar grabacion...")

    print("\nOpciones:")
    print("1. Deteccion libre")
    print("2. Evaluar contra nota especifica")
    opcion = input("Selecciona (1/2) [1]: ").strip() or "1"

    target_freq = None
    nota_obj = None

    if opcion == "2":
        notas = {
            '1': ('E2', 82.41),
            '2': ('A2', 110.00),
            '3': ('D3', 146.83),
            '4': ('G3', 196.00),
            '5': ('B3', 246.94),
            '6': ('E4', 329.63)
        }

        print("\nNotas disponibles:")
        for k, (nombre, freq) in notas.items():
            print(f"{k}. {nombre} ({freq} Hz)")

        seleccion = input("\nSelecciona cuerda (1-6) [1]: ").strip() or "1"
        nota_obj, target_freq = notas.get(seleccion, ('E2', 82.41))

        print(f"\nObjetivo: {nota_obj} ({target_freq} Hz)")

    print(f"\nGrabando {duration} segundos... Toca ahora.")

    try:
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='float32',
            blocking=True
        )


        print("Grabacion completada")

        if audio is None:
            print("Error: audio es None")
            return

        # Convertir a 1D correctamente
        signal = np.squeeze(audio)

        # Analizar solo el primer segundo (evita decay y ruido)
        analysis_window = sample_rate
        signal = signal[:analysis_window]

        max_amp = np.max(np.abs(signal))
        rms = np.sqrt(np.mean(signal**2))

        print("\nNivel de señal:")
        print(f"Pico maximo: {max_amp:.4f}")
        print(f"RMS: {rms:.4f}")

        if max_amp < 0.01:
            print("Señal demasiado debil.")
            return

        extractor = MetricsExtractor()

        # =========================
        # MODO EVALUACION
        # =========================
        if target_freq:

            metrics = extractor.evaluate_sequence(
                signal,
                sample_rate,
                target_freq
            )

            print("\nRESULTADOS")
            print("-" * 40)
            print(f"Frecuencia promedio: {metrics['detected_freq']:.2f} Hz")
            print(f"Nota detectada: {metrics['nota_detectada']}")
            print(f"Precision: {metrics['precision']:.2%}")
            print(f"Consistencia: {metrics['consistencia']:.2%}")
            print(f"Error: {metrics['error']:.2f} Hz")
            print(f"Confianza: {metrics['confianza']:.2%}")

        # =========================
        # MODO LIBRE
        # =========================
        else:

            freq, conf, harmonics = extractor.detect_pitch(
                signal,
                sample_rate
            )

            note = extractor.frequency_to_note(freq)

            print("\nDETECCION LIBRE")
            print("-" * 40)
            print(f"Frecuencia detectada: {freq:.2f} Hz")
            print(f"Nota musical: {note}")
            print(f"Confianza: {conf:.2%}")
            print(f"Armónicos detectados: {len(harmonics)}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()