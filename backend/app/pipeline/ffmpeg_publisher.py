from __future__ import annotations

import os
import subprocess
import threading
import time
from collections.abc import Callable

import numpy as np


class FFmpegPublisher:
    def __init__(
        self,
        ffmpeg_path: str,
        rtsp_url: str,
        width: int,
        height: int,
        fps: int,
        pix_fmt: str,
        audio_sample_rate: int,
        audio_channels: int,
        audio_gain: float,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self.ffmpeg_path = ffmpeg_path
        self.rtsp_url = rtsp_url
        self.width = width
        self.height = height
        self.fps = fps
        self.pix_fmt = pix_fmt
        self.audio_sample_rate = audio_sample_rate
        self.audio_channels = audio_channels
        self.audio_gain = audio_gain
        self.on_log = on_log
        self.process: subprocess.Popen | None = None
        self._audio_pipe = None
        self._video_lock = threading.Lock()
        self._audio_lock = threading.Lock()
        self._last_audio_write = 0.0
        self._silence_thread: threading.Thread | None = None

    def start(self) -> None:
        self.stop()
        audio_read_fd, audio_write_fd = os.pipe()
        cmd = [
            self.ffmpeg_path,
            "-thread_queue_size",
            "512",
            "-f",
            "rawvideo",
            "-pix_fmt",
            self.pix_fmt,
            "-s",
            f"{self.width}x{self.height}",
            "-r",
            str(self.fps),
            "-i",
            "-",
            "-thread_queue_size",
            "512",
            "-f",
            "f32le",
            "-ar",
            str(self.audio_sample_rate),
            "-ac",
            str(self.audio_channels),
            "-i",
            f"pipe:{audio_read_fd}",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "zerolatency",
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "baseline",
            "-g",
            str(self.fps),
            "-bf",
            "0",
            "-c:a",
            "libopus",
            "-b:a",
            "96k",
            "-af",
            f"volume={self.audio_gain}",
            "-f",
            "rtsp",
            self.rtsp_url,
        ]
        try:
            self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, pass_fds=(audio_read_fd,))
            self._audio_pipe = os.fdopen(audio_write_fd, "wb", buffering=0)
        finally:
            os.close(audio_read_fd)
        self._last_audio_write = time.monotonic()
        self._silence_thread = threading.Thread(target=self._write_silence_when_idle, daemon=True)
        self._silence_thread.start()
        threading.Thread(target=self._drain_stderr, daemon=True).start()

    def _drain_stderr(self) -> None:
        if not self.process or not self.process.stderr:
            return
        for raw in self.process.stderr:
            line = raw.decode(errors="replace").strip()
            if line and self.on_log:
                self.on_log(line)

    def write_frame(self, frame: np.ndarray) -> None:
        if not self.process or not self.process.stdin or self.process.poll() is not None:
            raise BrokenPipeError("FFmpeg 未运行")
        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(f"FFmpeg 需要 3 通道 BGR 帧，实际 shape={frame.shape}")
        frame_height, frame_width = frame.shape[:2]
        if frame_width != self.width or frame_height != self.height:
            raise ValueError(f"FFmpeg 帧尺寸不匹配: 期望 {self.width}x{self.height}, 实际 {frame_width}x{frame_height}")
        if self.pix_fmt != "bgr24":
            raise ValueError(f"当前仅支持 bgr24 输入像素格式，实际 pix_fmt={self.pix_fmt}")
        frame = np.ascontiguousarray(frame)
        with self._video_lock:
            self.process.stdin.write(frame.tobytes())

    def write_audio(self, samples: np.ndarray) -> None:
        if not self.process or self.process.poll() is not None or not self._audio_pipe:
            return
        audio = np.asarray(samples, dtype=np.float32)
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        if audio.ndim != 2:
            raise ValueError(f"FFmpeg 音频需要二维数组，实际 shape={audio.shape}")
        if audio.shape[1] != self.audio_channels:
            if audio.shape[1] > self.audio_channels:
                audio = audio[:, : self.audio_channels]
            else:
                audio = np.repeat(audio, self.audio_channels, axis=1)
        audio = np.ascontiguousarray(np.clip(audio, -1.0, 1.0), dtype=np.float32)
        self._write_audio_bytes(audio.tobytes(), mark_active=True)

    def _write_audio_bytes(self, payload: bytes, *, mark_active: bool) -> None:
        with self._audio_lock:
            if not self.process or self.process.poll() is not None or not self._audio_pipe:
                return
            try:
                self._audio_pipe.write(payload)
                if mark_active:
                    self._last_audio_write = time.monotonic()
            except (BrokenPipeError, ValueError):
                return

    def _write_silence_when_idle(self) -> None:
        chunk_samples = max(1, self.audio_sample_rate // 20)
        silence = np.zeros((chunk_samples, self.audio_channels), dtype=np.float32).tobytes()
        while self.process and self.process.poll() is None:
            if time.monotonic() - self._last_audio_write > 0.15:
                self._write_audio_bytes(silence, mark_active=False)
            time.sleep(0.05)

    def stop(self) -> None:
        if self._audio_pipe:
            try:
                self._audio_pipe.close()
            except Exception:
                pass
            self._audio_pipe = None
        if not self.process:
            return
        if self.process.stdin:
            try:
                self.process.stdin.close()
            except Exception:
                pass
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
