"""
Banco de calibración de métricas de audio (P1).

Sintetiza tonos de guitarra FÍSICAMENTE REALISTAS (fundamental + armónicos con
amplitudes de guitarra + envolvente de pulsación + inarmonicidad + micro-drift
de afinación) y los hace pasar por el MISMO pipeline que POST /practica
(SignalAnalyzer.load_audio -> MetricsExtractor.evaluate_sequence).

Objetivo: caracterizar qué valores de precisión/consistencia produce el
analizador para ejecuciones buenas / regulares / malas, y calibrar los
umbrales de aprobación (domain/ejercicios.py) con datos, no con suposiciones.

Nota: síntesis físicamente realista, no grabaciones reales. Da un punto de
partida defendible; la validación final necesita audio de guitarra real.
"""

import io
import wave

import numpy as np

from analizador_señales.señal import SignalAnalyzer
from audio.metricas_extractor import MetricsExtractor

SR = 22050
analyzer = SignalAnalyzer(sr=SR)
extractor = MetricsExtractor()

# Frecuencias de las 6 cuerdas al aire (afinación estándar).
CUERDAS = {
    "E2": 82.41, "A2": 110.0, "D3": 146.83,
    "G3": 196.0, "B3": 246.94, "E4": 329.63,
}

# Amplitudes armónicas típicas de una guitarra acústica (fundamental fuerte,
# armónicos decrecientes). Índice 0 = fundamental.
AMPLITUDES_ARMONICOS = [1.0, 0.6, 0.45, 0.3, 0.22, 0.15, 0.1, 0.07]
INARMONICIDAD = 0.0002  # B de cuerda de guitarra: f_n = n*f0*sqrt(1+B*n^2)


def sintetizar_nota(f0, dur_s=2.0, cents_offset=0.0, vibrato_cents=0.0,
                    drift_cents=0.0, semilla=0):
    """Sintetiza una nota de guitarra realista.

    - cents_offset: desafinación constante respecto al semitono (afinación).
    - vibrato_cents: amplitud de vibrato periódico (~5 Hz).
    - drift_cents: deriva aleatoria lenta de afinación (inestabilidad).
    """
    rng = np.random.default_rng(semilla)
    n = int(SR * dur_s)
    t = np.arange(n) / SR

    f_base = f0 * 2 ** (cents_offset / 1200.0)

    # Modulación de afinación: vibrato periódico + deriva aleatoria suave.
    mod_cents = vibrato_cents * np.sin(2 * np.pi * 5.0 * t)
    if drift_cents > 0:
        ruido = rng.standard_normal(n)
        # filtro paso-bajo simple (media móvil) para una deriva lenta
        k = int(SR * 0.05)
        ruido = np.convolve(ruido, np.ones(k) / k, mode="same")
        ruido = ruido / (np.max(np.abs(ruido)) + 1e-9)
        mod_cents = mod_cents + drift_cents * ruido
    f_inst = f_base * 2 ** (mod_cents / 1200.0)

    # Fase instantánea integrando la frecuencia.
    fase = 2 * np.pi * np.cumsum(f_inst) / SR

    señal = np.zeros(n)
    for i, amp in enumerate(AMPLITUDES_ARMONICOS):
        h = i + 1
        f_arm = h * np.sqrt(1 + INARMONICIDAD * h * h)
        señal += amp * np.sin(fase * f_arm)

    # Envolvente de pulsación: ataque rápido + decaimiento exponencial.
    ataque = int(SR * 0.005)
    env = np.exp(-t / (dur_s * 0.6))
    env[:ataque] *= np.linspace(0, 1, ataque)
    señal *= env

    # Ruido de fondo leve (realismo).
    señal += 0.002 * rng.standard_normal(n)
    señal = señal / (np.max(np.abs(señal)) + 1e-9) * 0.9
    return señal


def sintetizar_pasaje(frecs, dur_nota=0.5, **kwargs):
    """Concatena varias notas (escala / pasaje musical)."""
    return np.concatenate([sintetizar_nota(f, dur_s=dur_nota, **kwargs) for f in frecs])


def evaluar(señal):
    """Pasa la señal por el pipeline real de /practica y devuelve métricas."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        pcm = np.int16(np.clip(señal, -1, 1) * 32767)
        w.writeframes(pcm.tobytes())
    buf.seek(0)
    y = analyzer.load_audio(buf)
    freq, _c, _h = extractor.detect_pitch(y, SR)
    if freq is None or freq <= 0:
        return None
    import math
    target = 440.0 * 2 ** (round(12 * math.log2(freq / 440.0)) / 12)
    return extractor.evaluate_sequence(y, SR, target)


def resumen(nombre, muestras):
    precs = [m["precision"] for m in muestras if m]
    cons = [m["consistencia"] for m in muestras if m]
    print(f"{nombre:38s} | precision {np.mean(precs):.2f}±{np.std(precs):.2f} "
          f"[{min(precs):.2f}-{max(precs):.2f}] | consistencia {np.mean(cons):.2f}±{np.std(cons):.2f}")
    return np.mean(precs), np.mean(cons)


def escenario(nombre, **kwargs):
    muestras = []
    for i, (n, f) in enumerate(CUERDAS.items()):
        muestras.append(evaluar(sintetizar_nota(f, semilla=i, **kwargs)))
    return resumen(nombre, muestras)


if __name__ == "__main__":
    print("=== NOTAS SOSTENIDAS (caso afinación) ===")
    escenario("Afinada perfecta (0 cents)", cents_offset=0.0)
    escenario("Afinada + vibrato natural (8c)", vibrato_cents=8.0)
    escenario("Casi afinada (10 cents)", cents_offset=10.0)
    escenario("Ligeramente desafinada (20c)", cents_offset=20.0)
    escenario("Desafinada (30 cents)", cents_offset=30.0)
    escenario("Muy desafinada (45 cents)", cents_offset=45.0)
    escenario("Inestable (drift 25c)", drift_cents=25.0)
    escenario("Mala: desafinada+inestable", cents_offset=25.0, drift_cents=30.0)

    print("\n=== PASAJES MULTINOTA (escalas/acordes) ===")
    escala_do = [261.63, 293.66, 329.63, 349.23, 392.0, 440.0, 493.88, 523.25]
    m = [evaluar(sintetizar_pasaje(escala_do, semilla=s)) for s in range(6)]
    resumen("Escala Do (8 notas, bien tocada)", m)
    m = [evaluar(sintetizar_pasaje(escala_do, drift_cents=20.0, semilla=s)) for s in range(6)]
    resumen("Escala Do (con inestabilidad)", m)
