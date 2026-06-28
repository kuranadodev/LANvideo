from __future__ import annotations

import asyncio
import time
import numpy as np

from app.algorithms.audio_fft import FftAudioAlgorithm


class AudioWorker:
    def __init__(self, settings, event_bus) -> None:
        self.settings = settings
        self.event_bus = event_bus
        self.running = False
        self.error: str | None = None
        self._task: asyncio.Task | None = None
        self._stop = False
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        if self.running:
            return
        self._loop = asyncio.get_running_loop()
        self._stop = False
        self.error = None
        self._task = asyncio.create_task(asyncio.to_thread(self._run))

    async def stop(self) -> None:
        self._stop = True
        if self._task:
            await asyncio.wait([self._task], timeout=5)
        self.running = False

    def _publish(self, message: dict) -> None:
        if self._loop:
            asyncio.run_coroutine_threadsafe(self.event_bus.publish(message), self._loop)

    def _log(self, level: str, message: str) -> None:
        if self._loop:
            asyncio.run_coroutine_threadsafe(self.event_bus.log(level, message), self._loop)

    def _run(self) -> None:
        try:
            import sounddevice as sd
            algorithm = FftAudioAlgorithm()
            device = self.settings.audio_device
            if isinstance(device, str) and device.isdigit():
                device = int(device)
            self.running = True
            self._log("info", "音频管线已启动")
            last_push = 0.0
            with sd.InputStream(device=device, samplerate=self.settings.audio_sample_rate, channels=self.settings.audio_channels, blocksize=self.settings.audio_block_size, dtype="float32") as stream:
                while not self._stop:
                    data, _ = stream.read(self.settings.audio_block_size)
                    now = time.monotonic()
                    if now - last_push < 0.07:
                        continue
                    last_push = now
                    mono = np.mean(data, axis=1) if data.ndim > 1 else data.reshape(-1)
                    step = max(1, len(mono) // 256)
                    waveform = mono[::step][:256].astype(float).tolist()
                    analysis = algorithm.analyze(mono, self.settings.audio_sample_rate)
                    self._publish({"type": "audio.waveform", "sample_rate": self.settings.audio_sample_rate, "values": waveform})
                    self._publish({"type": "audio.spectrum", "sample_rate": self.settings.audio_sample_rate, "freqs": analysis["freqs"], "magnitudes": analysis["magnitudes"]})
                    self._publish({"type": "audio.metrics", "rms": analysis["rms"], "peak": analysis["peak"]})
        except Exception as exc:
            self.error = str(exc)
            self._log("error", f"音频管线异常: {exc}")
        finally:
            self.running = False
            self._log("info", "音频管线已停止")
