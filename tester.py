import numpy as np
from audio.metricas_extractor import MetricsExtractor

def test_cuerda(frecuencia, nombre_cuerda, sample_rate=44100):
    """Prueba una cuerda específica con señal simulada."""
    t = np.linspace(0, 1, sample_rate)
    
    # Simular cuerda con armónicos realistas (fundamental + 2do + 3er armónico)
    fundamental = np.sin(2 * np.pi * frecuencia * t)
    segundo_armonico = 0.5 * np.sin(2 * np.pi * frecuencia * 2 * t)
    tercer_armonico = 0.25 * np.sin(2 * np.pi * frecuencia * 3 * t)
    
    # Agregar un poco de ruido realista
    ruido = 0.02 * np.random.randn(len(t))
    
    signal = fundamental + segundo_armonico + tercer_armonico + ruido
    
    # Analizar
    extractor = MetricsExtractor()
    metrics = extractor.evaluate(signal, sample_rate, frecuencia)
    
    print(f"\n{'='*40}")
    print(f"{nombre_cuerda} ({frecuencia} Hz)")
    print(f"{'='*40}")
    print(f"Frecuencia detectada: {metrics['detected_freq']:.2f} Hz")
    print(f"Nota detectada: {metrics['nota_detectada']}")
    print(f"Precisión: {metrics['precision']:.3f}")
    print(f"Consistencia: {metrics['consistencia']:.3f}")
    print(f"Error: {metrics['error']:.2f} Hz")
    
    return metrics

# Probar todas las cuerdas
if __name__ == "__main__":
    print(" PRUEBA DE DETECCIÓN DE CUERDAS SUELTAS")
    
    cuerdas = [
        (82.41, "6ª cuerda - Mi grave"),
        (110.00, "5ª cuerda - La"),
        (146.83, "4ª cuerda - Re"),
        (196.00, "3ª cuerda - Sol"),
        (246.94, "2ª cuerda - Si"),
        (329.63, "1ª cuerda - Mi agudo")
    ]
    
    resultados = []
    for freq, nombre in cuerdas:
        metrics = test_cuerda(freq, nombre)
        resultados.append({
            'cuerda': nombre,
            'precision': metrics['precision'],
            'detectada': metrics['detected_freq']
        })
    
    # Resumen
    print(f"\n{'='*50}")
    print("RESUMEN DE PRUEBAS")
    print(f"{'='*50}")
    for r in resultados:
        status = "" if r['precision'] > 0.95 else ""
        print(f"{status} {r['cuerda']}: {r['detectada']:.2f} Hz")