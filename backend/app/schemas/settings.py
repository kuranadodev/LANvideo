from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    video_device: str = "/dev/video0"
    video_width: int = Field(1280, ge=1)
    video_height: int = Field(720, ge=1)
    video_fps: int = Field(20, ge=1, le=120)
    video_fourcc: str | None = None
    video_encoder: str = "libx264"
    video_encoder_preset: str | None = None
    video_bitrate: str | None = None
    audio_device: int | str | None = None
    audio_sample_rate: int = Field(48000, ge=8000)
    audio_channels: int = Field(1, ge=1, le=8)
    audio_block_size: int = Field(1024, ge=128)
    audio_playback_gain: float = Field(3.0, ge=0.1, le=20.0)
    audio_metrics_interval_ms: int = Field(70, ge=20, le=1000)
    mediamtx_webrtc_url: str
    video_algorithm: str = "dummy"
    audio_algorithm: str = "fft"
