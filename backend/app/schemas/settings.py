from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    video_device: str = "/dev/video0"
    video_width: int = Field(1280, ge=1)
    video_height: int = Field(720, ge=1)
    video_fps: int = Field(20, ge=1, le=120)
    video_fourcc: str | None = None
    audio_device: int | str | None = None
    audio_sample_rate: int = Field(48000, ge=8000)
    audio_channels: int = Field(1, ge=1, le=8)
    audio_block_size: int = Field(1024, ge=128)
    mediamtx_webrtc_url: str
    video_algorithm: str = "dummy"
    audio_algorithm: str = "fft"
