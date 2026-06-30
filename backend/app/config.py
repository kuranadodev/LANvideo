from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _optional(name: str) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else None


@dataclass
class Settings:
    video_device: str = os.getenv("VIDEO_DEVICE", "/dev/video0")
    video_width: int = _int("VIDEO_WIDTH", 1280)
    video_height: int = _int("VIDEO_HEIGHT", 720)
    video_fps: int = _int("VIDEO_FPS", 20)
    video_pix_fmt: str = os.getenv("VIDEO_PIX_FMT", "bgr24")
    video_encoder: str = os.getenv("VIDEO_ENCODER", "libx264")
    video_encoder_preset: str | None = _optional("VIDEO_ENCODER_PRESET")
    video_bitrate: str | None = _optional("VIDEO_BITRATE")
    video_fourcc: str | None = _optional("VIDEO_FOURCC")
    audio_device: int | str | None = _optional("AUDIO_DEVICE")
    audio_sample_rate: int = _int("AUDIO_SAMPLE_RATE", 48000)
    audio_channels: int = _int("AUDIO_CHANNELS", 1)
    audio_block_size: int = _int("AUDIO_BLOCK_SIZE", 1024)
    audio_playback_gain: float = float(os.getenv("AUDIO_PLAYBACK_GAIN", "3.0"))
    audio_metrics_interval_ms: int = _int("AUDIO_METRICS_INTERVAL_MS", 70)
    mediamtx_rtsp_url: str = os.getenv("MEDIAMTX_RTSP_URL", "rtsp://127.0.0.1:8554/processed")
    mediamtx_webrtc_url: str = os.getenv("MEDIAMTX_WEBRTC_URL", "http://127.0.0.1:8889/processed")
    ffmpeg_path: str = os.getenv("FFMPEG_PATH", "ffmpeg")
    video_algorithm: str = os.getenv("VIDEO_ALGORITHM", "dummy")
    audio_algorithm: str = os.getenv("AUDIO_ALGORITHM", "fft")


settings = Settings()
