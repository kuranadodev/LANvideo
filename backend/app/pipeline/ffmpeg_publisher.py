from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable

import numpy as np


class FFmpegPublisher:
    def __init__(self, ffmpeg_path: str, rtsp_url: str, width: int, height: int, fps: int, pix_fmt: str, on_log: Callable[[str], None] | None = None) -> None:
        self.ffmpeg_path = ffmpeg_path
        self.rtsp_url = rtsp_url
        self.width = width
        self.height = height
        self.fps = fps
        self.pix_fmt = pix_fmt
        self.on_log = on_log
        self.process: subprocess.Popen | None = None

    def start(self) -> None:
        self.stop()
        cmd = [self.ffmpeg_path, "-f", "rawvideo", "-pix_fmt", self.pix_fmt, "-s", f"{self.width}x{self.height}", "-r", str(self.fps), "-i", "-", "-an", "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-pix_fmt", "yuv420p", "-profile:v", "baseline", "-g", str(self.fps), "-bf", "0", "-f", "rtsp", self.rtsp_url]
        self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
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
        self.process.stdin.write(frame.tobytes())

    def stop(self) -> None:
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
