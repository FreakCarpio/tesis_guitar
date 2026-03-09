import numpy as np

def harmonic_product_spectrum(signal, sr):

    spectrum = np.abs(np.fft.fft(signal))
    spectrum = spectrum[:len(spectrum)//2]

    hps = spectrum.copy()

    for h in range(2,5):
        decimated = spectrum[::h]
        hps[:len(decimated)] *= decimated

    peak = np.argmax(hps)

    freq = peak * sr / len(signal)

    return freq