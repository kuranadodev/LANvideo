from __future__ import annotations

import numpy as np

from .audio_base import AudioAlgorithm


class FftAudioAlgorithm(AudioAlgorithm):
    name = "fft"

    def analyze(self, samples: np.ndarray, sample_rate: int) -> dict:
        mono = samples.reshape(-1).astype(np.float32)
        rms = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
        peak = float(np.max(np.abs(mono))) if mono.size else 0.0
        windowed = mono * np.hanning(len(mono)) if mono.size else mono
        spectrum = np.fft.rfft(windowed) if mono.size else np.array([])
        magnitudes = np.abs(spectrum)
        if magnitudes.size and magnitudes.max() > 0:
            magnitudes = magnitudes / magnitudes.max()
        freqs = np.fft.rfftfreq(len(mono), d=1.0 / sample_rate) if mono.size else np.array([])
        return {"rms": rms, "peak": peak, "freqs": freqs[:256].tolist(), "magnitudes": magnitudes[:256].tolist()}
