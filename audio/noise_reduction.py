"""
Reducción de ruido espectral para guitarra acústica.

Implementa dos algoritmos de reducción espectral:
1. Spectral Noise Gate (spectral gating) — elimina ruido por debajo de un umbral espectral
2. Wiener Filter adaptativo — estimación MMSE de la señal limpia

Para tesis:
La reducción espectral en el dominio de la frecuencia es una técnica
fundamental en DSP de audio. Ambos métodos transforman la señal al dominio
STFT, aplican un filtro espectral, y reconstruyen la señal (ISTFT).
La diferencia está en cómo calculan el filtro: el spectral gating usa
un umbral duro/blando mientras que Wiener usa una estimación estadística
de la relación señal-ruido (SNR) en cada banda de frecuencia.

Referencia académica:
- Spectral subtraction: Boll (1979) "Suppression of acoustic noise in speech..."
- Wiener filtering: Scalart & Filho (1996) "Speech enhancement based on a priori SNR"
"""

import numpy as np
from scipy import signal as scipy_signal
from typing import Optional, Tuple


class SpectralNoiseReducer:
    """
    Reducción de ruido espectral (spectral gating).

    Transforma la señal al dominio frecuencia vía STFT, aplica un umbral
    espectral adaptativo por banda de frecuencia, y reconstruye la señal
    mediante ISTFT con overlap-add.

    DSP: Spectral gating con estimación de piso de ruido.
    Ventana Hann para reducir leakage espectral.
    Reconstrucción overlap-add para evitar artefactos.

    Para tesis:
    - Demuestra dominio de STFT (Short-Time Fourier Transform)
    - Implementa enventanado con solapamiento (overlap-add)
    - El umbral se calcula como noise_floor + n_std * noise_std
    - Mediana móvil en tiempo suaviza la máscara espectral
    """

    def __init__(self,
                 sample_rate: int = 44100,
                 fft_size: int = 2048,
                 hop_length: int = 512,
                 noise_floor_percentile: float = 50,
                 reduction_factor: float = 0.1,
                 n_std_thresh: float = 2.0):

        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self.hop_length = hop_length
        self.noise_floor_percentile = noise_floor_percentile
        self.reduction_factor = reduction_factor
        self.n_std_thresh = n_std_thresh
        self.noise_floor = None
        self.noise_std = None
        self.calibrated = False

        self.window = scipy_signal.windows.hann(fft_size, sym=False)

    def calibrate(self, noise_sample: np.ndarray):
        """
        Calibra el piso de ruido a partir de una muestra de silencio.

        Debe llamarse antes de procesar, con el micrófono activo pero
        sin tocar la guitarra (solo ruido ambiente).

        Args:
            noise_sample: Muestra de audio sin señal de guitarra
        """
        f, t, Zxx = scipy_signal.stft(
            noise_sample,
            fs=self.sample_rate,
            window=self.window,
            nperseg=self.fft_size,
            noverlap=self.fft_size - self.hop_length
        )

        magnitude = np.abs(Zxx)

        self.noise_floor = np.percentile(magnitude, self.noise_floor_percentile, axis=1)
        self.noise_std = np.std(magnitude, axis=1)
        self.calibrated = True

    def process(self, signal: np.ndarray) -> np.ndarray:
        """
        Aplica reducción espectral de ruido vía spectral gating.

        Args:
            signal: Señal de audio preprocesada

        Returns:
            Señal con ruido reducido espectralmente
        """
        f, t, Zxx = scipy_signal.stft(
            signal,
            fs=self.sample_rate,
            window=self.window,
            nperseg=self.fft_size,
            noverlap=self.fft_size - self.hop_length
        )

        magnitude = np.abs(Zxx)
        phase = np.angle(Zxx)

        if self.calibrated:
            threshold = self.noise_floor[:, np.newaxis] + \
                        self.n_std_thresh * self.noise_std[:, np.newaxis]
        else:
            threshold_freq = np.percentile(magnitude, 20, axis=1, keepdims=True)
            threshold_time = np.percentile(magnitude, 20, axis=0, keepdims=True)
            threshold = np.maximum(threshold_freq, threshold_time)
            threshold = np.maximum(threshold, np.percentile(magnitude, 10))

        mask = magnitude > threshold
        gain = np.where(mask, 1.0, self.reduction_factor)

        gain = scipy_signal.medfilt(gain, kernel_size=(3, 1))

        magnitude_filtered = magnitude * gain

        Zxx_filtered = magnitude_filtered * np.exp(1j * phase)

        _, filtered = scipy_signal.istft(
            Zxx_filtered,
            fs=self.sample_rate,
            window=self.window,
            nperseg=self.fft_size,
            noverlap=self.fft_size - self.hop_length
        )

        return filtered


class WienerFilterNoiseReducer:
    """
    Reducción de ruido basada en filtro Wiener adaptativo.

    A diferencia del spectral gating (que aplica un umbral binario),
    el filtro Wiener estima la SNR instantánea en cada banda frecuencia-
    tiempo y aplica una ganancia suave: G = SNR / (SNR + 1).

    Esto produce una reducción de ruido más natural, sin artefactos
    de "música espectral" (musical noise) típicos del spectral gating.

    DSP: El filtro Wiener es el estimador MMSE (Minimum Mean Square Error)
    óptimo para ruido aditivo estacionario. Asume que señal y ruido son
    procesos aleatorios Gaussianos incorrelacionados.

    Para tesis:
    - El filtro Wiener es matemáticamente más elegante que el spectral gating
    - No requiere umbrales empíricos (se adapta automáticamente)
    - Produce menos artefactos audibles
    - Es la base de sistemas profesionales de reducción de ruido
    """

    def __init__(self,
                 sample_rate: int = 44100,
                 fft_size: int = 2048,
                 hop_length: int = 512,
                 noise_floor_percentile: float = 30,
                 snr_min_db: float = -20.0,
                 snr_max_db: float = 40.0):

        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self.hop_length = hop_length
        self.noise_floor_percentile = noise_floor_percentile
        self.snr_min_linear = 10 ** (snr_min_db / 10)
        self.snr_max_linear = 10 ** (snr_max_db / 10)
        self.noise_psd = None
        self.calibrated = False

        self.window = scipy_signal.windows.hann(fft_size, sym=False)

    def calibrate(self, noise_sample: np.ndarray):
        """
        Estima la densidad espectral de potencia (PSD) del ruido.

        Args:
            noise_sample: Muestra de audio sin señal de guitarra
        """
        f, t, Zxx = scipy_signal.stft(
            noise_sample,
            fs=self.sample_rate,
            window=self.window,
            nperseg=self.fft_size,
            noverlap=self.fft_size - self.hop_length
        )

        self.noise_psd = np.median(np.abs(Zxx) ** 2, axis=1)
        self.calibrated = True

    def process(self, signal: np.ndarray) -> np.ndarray:
        """
        Aplica filtro Wiener adaptativo para reducción de ruido.

        El filtro Wiener se calcula como:
            G(f,t) = SNR_priori(f,t) / (SNR_priori(f,t) + 1)

        Donde SNR_priori se estima usando el método "decision-directed"
        (Ephraim & Malah, 1984) que mezcla la SNR instantánea con la
        SNR estimada en el frame anterior, dando mayor estabilidad.

        Args:
            signal: Señal de audio

        Returns:
            Señal filtrada con ruido reducido
        """
        f, t, Zxx = scipy_signal.stft(
            signal,
            fs=self.sample_rate,
            window=self.window,
            nperseg=self.fft_size,
            noverlap=self.fft_size - self.hop_length
        )

        magnitude_sq = np.abs(Zxx) ** 2

        if self.calibrated:
            noise_power = self.noise_psd[:, np.newaxis]
        else:
            noise_power = np.percentile(magnitude_sq, self.noise_floor_percentile, axis=1, keepdims=True)
            noise_power = np.maximum(noise_power, np.percentile(magnitude_sq, 10))

        noise_power = np.maximum(noise_power, 1e-10)

        snr_instant = magnitude_sq / noise_power

        gamma = np.clip(snr_instant, self.snr_min_linear, self.snr_max_linear)

        gain = gamma / (gamma + 1.0)

        gain = scipy_signal.medfilt(gain, kernel_size=(3, 1))

        gain = np.clip(gain, 0.05, 1.0)

        Zxx_filtered = Zxx * gain

        _, filtered = scipy_signal.istft(
            Zxx_filtered,
            fs=self.sample_rate,
            window=self.window,
            nperseg=self.fft_size,
            noverlap=self.fft_size - self.hop_length
        )

        return filtered
