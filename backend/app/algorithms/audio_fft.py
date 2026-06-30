from __future__ import annotations

import numpy as np

from .audio_base import AudioAlgorithm


class FftAudioAlgorithm(AudioAlgorithm):
    name = "fft"

    def __init__(self) -> None:
        self._window_size: int | None = None
        self._window: np.ndarray | None = None

    def _get_window(self, size: int) -> np.ndarray:
        if self._window is None or self._window_size != size:
            self._window = np.hanning(size).astype(np.float32)
            self._window_size = size
        return self._window

    def analyze(self, samples: np.ndarray, sample_rate: int) -> dict:
        mono = samples.reshape(-1).astype(np.float32)
        rms = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
        peak = float(np.max(np.abs(mono))) if mono.size else 0.0
        windowed = mono * self._get_window(len(mono)) if mono.size else mono
        spectrum = np.fft.rfft(windowed) if mono.size else np.array([])
        magnitudes = np.abs(spectrum)
        if magnitudes.size and magnitudes.max() > 0:
            magnitudes = magnitudes / magnitudes.max()
        freqs = np.fft.rfftfreq(len(mono), d=1.0 / sample_rate) if mono.size else np.array([])
        return {"rms": rms, "peak": peak, "freqs": freqs[:256].tolist(), "magnitudes": magnitudes[:256].tolist()}
