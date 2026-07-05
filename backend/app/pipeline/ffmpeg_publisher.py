from __future__ import annotations

import os
import subprocess
import threading
import time
from collections import deque
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
        video_encoder: str = "libx264",
        video_encoder_preset: str | None = None,
        video_bitrate: str | None = None,
        video_maxrate: str | None = None,
        video_bufsize: str | None = None,
        video_thread_queue_size: int = 16,
        audio_thread_queue_size: int = 64,
        video_rtsp_transport: str = "tcp",
        video_low_latency_mode: bool = True,
        video_analysis_width: int | None = None,
        video_analysis_height: int | None = None,
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
        self.video_encoder = video_encoder
        self.video_encoder_preset = video_encoder_preset
        self.video_bitrate = video_bitrate
        self.video_maxrate = video_maxrate
        self.video_bufsize = video_bufsize
        self.video_thread_queue_size = video_thread_queue_size
        self.audio_thread_queue_size = audio_thread_queue_size
        self.video_rtsp_transport = video_rtsp_transport
        self.video_low_latency_mode = video_low_latency_mode
        self.video_analysis_width = video_analysis_width or width
        self.video_analysis_height = video_analysis_height or height
        self.on_log = on_log
        self.process: subprocess.Popen | None = None
        self._audio_pipe = None
        self._video_lock = threading.Lock()
        self._audio_lock = threading.Lock()
        self._last_audio_write = 0.0
        self._silence_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._recent_stderr: deque[str] = deque(maxlen=40)

    def _video_encoder_args(self) -> list[str]:
        encoder = (self.video_encoder or "libx264").strip()
        if encoder == "libx264":
            args = ["-c:v", "libx264", "-preset", self.video_encoder_preset or "ultrafast", "-tune", "zerolatency", "-pix_fmt", "yuv420p", "-profile:v", "baseline", "-g", str(self.fps), "-bf", "0"]
        elif encoder == "h264_nvenc":
            args = ["-c:v", "h264_nvenc", "-preset", self.video_encoder_preset or "p1", "-tune", "ull", "-pix_fmt", "yuv420p", "-g", str(self.fps), "-bf", "0"]
        else:
            raise ValueError(f"不支持的视频编码器: {encoder}")
        if self.video_bitrate:
            args.extend(["-b:v", self.video_bitrate])
        if self.video_maxrate:
            args.extend(["-maxrate", self.video_maxrate])
        if self.video_bufsize:
            args.extend(["-bufsize", self.video_bufsize])
        return args

    def _recent_error_context(self) -> str:
        if not self._recent_stderr:
            return ""
        text = "\n".join(self._recent_stderr)
        hint = ""
        lower = text.lower()
        if "unknown encoder" in lower and "h264_nvenc" in lower:
            hint = "；当前 FFmpeg 可能未编译 h264_nvenc 编码器"
        elif "cannot load libcuda" in lower or "libcuda" in lower:
            hint = "；无法加载 CUDA 驱动库，请检查 NVIDIA 驱动"
        elif "no capable devices" in lower:
            hint = "；未发现可用的 NVIDIA 编码设备"
        elif "device or resource busy" in lower or "resource busy" in lower:
            hint = "；摄像头设备正被其他进程占用，请使用 sudo fuser -v /dev/video* 或 sudo lsof /dev/video* 排查"
        return f"；最近 FFmpeg 输出{hint}: {text}"

    def _audio_input_args(self, audio_read_fd: int) -> list[str]:
        return ["-thread_queue_size", str(self.audio_thread_queue_size), "-f", "f32le", "-ar", str(self.audio_sample_rate), "-ac", str(self.audio_channels), "-i", f"pipe:{audio_read_fd}"]

    def _audio_output_args(self) -> list[str]:
        return ["-c:a", "libopus", "-b:a", "96k", "-af", f"volume={self.audio_gain}"]


    def _low_latency_input_args(self) -> list[str]:
        if not self.video_low_latency_mode:
            return []
        return ["-fflags", "nobuffer", "-flags", "low_delay"]

    def _rtsp_output_args(self) -> list[str]:
        args: list[str] = []
        transport = (self.video_rtsp_transport or "tcp").strip().lower()
        if transport in {"tcp", "udp"}:
            args.extend(["-rtsp_transport", transport])
        if self.video_low_latency_mode:
            args.extend(["-muxdelay", "0", "-muxpreload", "0", "-flush_packets", "1"])
        args.extend(["-f", "rtsp", self.rtsp_url])
        return args

    @staticmethod
    def _v4l2_input_format(fourcc: str | None) -> str | None:
        code = (fourcc or "").strip().upper()
        if code in {"MJPG", "MJPEG", "JPEG"}:
            return "mjpeg"
        if code in {"YUYV", "YUY2"}:
            return "yuyv422"
        if code in {"H264", "H.264", "AVC1"}:
            return "h264"
        return fourcc.strip().lower() if fourcc else None

    def _spawn(self, cmd: list[str], audio_read_fd: int, audio_write_fd: int, *, stdin: bool = True, stdout: bool = False) -> None:
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE if stdin else subprocess.DEVNULL,
                stdout=subprocess.PIPE if stdout else subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                pass_fds=(audio_read_fd,),
            )
            self._audio_pipe = os.fdopen(audio_write_fd, "wb", buffering=0)
        finally:
            os.close(audio_read_fd)
        self._recent_stderr.clear()
        self._last_audio_write = time.monotonic()
        self._silence_thread = threading.Thread(target=self._write_silence_when_idle, daemon=True)
        self._silence_thread.start()
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()

    def start(self) -> None:
        self.stop()
        audio_read_fd, audio_write_fd = os.pipe()
        cmd = [self.ffmpeg_path, *self._low_latency_input_args(), "-thread_queue_size", str(self.video_thread_queue_size), "-f", "rawvideo", "-pix_fmt", self.pix_fmt, "-s", f"{self.width}x{self.height}", "-r", str(self.fps), "-i", "-", *self._audio_input_args(audio_read_fd), *self._video_encoder_args(), *self._audio_output_args(), *self._rtsp_output_args()]
        self._spawn(cmd, audio_read_fd, audio_write_fd)

    def start_v4l2(self, device: str, fourcc: str | None = None) -> None:
        self.stop()
        audio_read_fd, audio_write_fd = os.pipe()
        input_args = [*self._low_latency_input_args(), "-thread_queue_size", str(self.video_thread_queue_size), "-f", "v4l2", "-framerate", str(self.fps), "-video_size", f"{self.width}x{self.height}"]
        input_format = self._v4l2_input_format(fourcc)
        if input_format:
            input_args.extend(["-input_format", input_format])
        cmd = [self.ffmpeg_path, *input_args, "-i", device, *self._audio_input_args(audio_read_fd), *self._video_encoder_args(), *self._audio_output_args(), *self._rtsp_output_args()]
        self._spawn(cmd, audio_read_fd, audio_write_fd)

    def start_v4l2_with_analysis(self, device: str, fourcc: str | None = None, analysis_fps: int = 5) -> None:
        self.stop()
        audio_read_fd, audio_write_fd = os.pipe()
        input_args = [*self._low_latency_input_args(), "-thread_queue_size", str(self.video_thread_queue_size), "-f", "v4l2", "-framerate", str(self.fps), "-video_size", f"{self.width}x{self.height}"]
        input_format = self._v4l2_input_format(fourcc)
        if input_format:
            input_args.extend(["-input_format", input_format])
        filter_complex = (
            f"[0:v]split=2[vmain][vanalysis];"
            f"[vanalysis]fps={max(1, analysis_fps)},scale={self.video_analysis_width}:{self.video_analysis_height},format=bgr24[raw]"
        )
        cmd = [
            self.ffmpeg_path,
            *input_args,
            "-i",
            device,
            *self._audio_input_args(audio_read_fd),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vmain]",
            "-map",
            "1:a",
            *self._video_encoder_args(),
            *self._audio_output_args(),
            *self._rtsp_output_args(),
            "-map",
            "[raw]",
            "-f",
            "rawvideo",
            "pipe:1",
        ]
        self._spawn(cmd, audio_read_fd, audio_write_fd, stdin=False, stdout=True)

    def read_analysis_frame(self) -> np.ndarray:
        if not self.process or not self.process.stdout or self.process.poll() is not None:
            raise BrokenPipeError(f"FFmpeg 分析输出未运行{self._recent_error_context()}")
        frame_size = self.video_analysis_width * self.video_analysis_height * 3
        payload = self.process.stdout.read(frame_size)
        if len(payload) != frame_size:
            raise BrokenPipeError(f"FFmpeg 分析输出已中断{self._recent_error_context()}")
        return np.frombuffer(payload, dtype=np.uint8).reshape((self.video_analysis_height, self.video_analysis_width, 3)).copy()

    def _drain_stderr(self) -> None:
        if not self.process or not self.process.stderr:
            return
        for raw in self.process.stderr:
            line = raw.decode(errors="replace").strip()
            if line:
                self._recent_stderr.append(line)
                if self.on_log:
                    self.on_log(line)

    def write_frame(self, frame: np.ndarray) -> None:
        if not self.process or not self.process.stdin or self.process.poll() is not None:
            raise BrokenPipeError(f"FFmpeg 未运行{self._recent_error_context()}")
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
        self.on_log = None
        if self._audio_pipe:
            try:
                self._audio_pipe.close()
            except Exception:
                pass
            self._audio_pipe = None
        if self.process:
            if self.process.stdin:
                try:
                    self.process.stdin.close()
                except Exception:
                    pass
            if self.process.stdout:
                try:
                    self.process.stdout.close()
                except Exception:
                    pass
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
            self.process = None
        if self._silence_thread and self._silence_thread.is_alive():
            self._silence_thread.join(timeout=1)
        self._silence_thread = None
        if self._stderr_thread and self._stderr_thread.is_alive():
            self._stderr_thread.join(timeout=1)
        self._stderr_thread = None
