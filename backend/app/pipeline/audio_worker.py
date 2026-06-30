from __future__ import annotations

import asyncio
from collections.abc import Coroutine
import time
import numpy as np

from app.algorithms.audio_fft import FftAudioAlgorithm

AUDIO_ALGORITHMS = {"fft": FftAudioAlgorithm}


class AudioWorker:
    def __init__(self, settings, event_bus, publisher=None) -> None:
        self.settings = settings
        self.event_bus = event_bus
        self.publisher = publisher
        self.running = False
        self.error: str | None = None
        self._task: asyncio.Task | None = None
        self._stop = False
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        if self.running:
            return
        if self._task and not self._task.done():
            return
        self._loop = asyncio.get_running_loop()
        self._stop = False
        self.error = None
        self._task = asyncio.create_task(asyncio.to_thread(self._run))

    async def stop(self) -> None:
        self._stop = True
        if self._task and not self._task.done():
            done, _ = await asyncio.wait([self._task], timeout=5)
            if done:
                self._task = None
        elif self._task:
            self._task = None
        if not self._task:
            self.running = False

    def _submit_to_loop(self, coro: Coroutine) -> None:
        if not self._loop or self._loop.is_closed():
            coro.close()
            return
        try:
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            future.add_done_callback(lambda item: item.exception())
        except RuntimeError:
            coro.close()

    def _publish(self, message: dict) -> None:
        if self._loop and not self._loop.is_closed():
            self._submit_to_loop(self.event_bus.publish(message))

    def _log(self, level: str, message: str) -> None:
        if self._loop and not self._loop.is_closed():
            self._submit_to_loop(self.event_bus.log(level, message))

    @staticmethod
    def _is_invalid_sample_rate_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "invalid sample rate" in message or "-9997" in message

    def _open_stream(self, sd, device, sample_rate: int):
        return sd.InputStream(
            device=device,
            samplerate=sample_rate,
            channels=self.settings.audio_channels,
            blocksize=self.settings.audio_block_size,
            dtype="float32",
        )

    def _run(self) -> None:
        try:
            import sounddevice as sd
            algo_cls = AUDIO_ALGORITHMS.get(self.settings.audio_algorithm, FftAudioAlgorithm)
            if algo_cls is FftAudioAlgorithm and self.settings.audio_algorithm not in AUDIO_ALGORITHMS:
                self._log("warning", f"未知音频算法 {self.settings.audio_algorithm}，已回退到 fft")
            algorithm = algo_cls()
            device = self.settings.audio_device
            if isinstance(device, str) and device.isdigit():
                device = int(device)

            requested_sample_rate = int(self.settings.audio_sample_rate)
            actual_sample_rate = requested_sample_rate
            stream = self._open_stream(sd, device, requested_sample_rate)
            try:
                stream.__enter__()
            except Exception as exc:
                stream.close(ignore_errors=True)
                if not self._is_invalid_sample_rate_error(exc):
                    raise

                device_info = sd.query_devices(device, "input")
                default_sample_rate = int(device_info.get("default_samplerate", requested_sample_rate))
                if default_sample_rate == requested_sample_rate:
                    raise

                self._log(
                    "warning",
                    f"音频采样率 {requested_sample_rate} Hz 不被当前输入设备支持，改用设备默认采样率 {default_sample_rate} Hz",
                )
                actual_sample_rate = default_sample_rate
                stream = self._open_stream(sd, device, actual_sample_rate)
                stream.__enter__()

            self.running = True
            self._log("info", f"音频管线已启动，采样率 {actual_sample_rate} Hz")
            last_push = 0.0
            try:
                while not self._stop:
                    data, _ = stream.read(self.settings.audio_block_size)
                    if self.publisher:
                        self.publisher.write_audio(data)
                    now = time.monotonic()
                    if now - last_push < self.settings.audio_metrics_interval_ms / 1000.0:
                        continue
                    last_push = now
                    mono = np.mean(data, axis=1) if data.ndim > 1 else data.reshape(-1)
                    step = max(1, len(mono) // 256)
                    waveform = mono[::step][:256].astype(float).tolist()
                    analysis = algorithm.analyze(mono, actual_sample_rate)
                    self._publish({"type": "audio.waveform", "sample_rate": actual_sample_rate, "values": waveform})
                    self._publish({"type": "audio.spectrum", "sample_rate": actual_sample_rate, "freqs": analysis["freqs"], "magnitudes": analysis["magnitudes"]})
                    self._publish({"type": "audio.metrics", "rms": analysis["rms"], "peak": analysis["peak"]})
            finally:
                stream.__exit__(None, None, None)
        except Exception as exc:
            self.error = str(exc)
            self._log("error", f"音频管线异常: {exc}")
        finally:
            self.running = False
            self._log("info", "音频管线已停止")
