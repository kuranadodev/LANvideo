from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, HTTPException, Request

from app.algorithms.video_dummy import DummyVideoAlgorithm
from app.algorithms.video_motion import MotionVideoAlgorithm
from app.config import settings
from app.devices.camera import is_video_format_supported, list_video_devices
from app.devices.microphone import list_audio_devices
from app.schemas.messages import AlgorithmSelectRequest
from app.schemas.settings import AppSettings
from app.utils.system_info import get_system_info

router = APIRouter(prefix="/api")
VIDEO_NAMES = [DummyVideoAlgorithm.name, MotionVideoAlgorithm.name]
AUDIO_NAMES = ["fft"]


def browser_webrtc_url(request: Request | None = None) -> str:
    url = settings.mediamtx_webrtc_url
    if request is None:
        return url

    parsed = urlsplit(url)
    request_host = request.url.hostname
    if parsed.hostname in {"127.0.0.1", "localhost", "0.0.0.0"} and request_host not in {
        None,
        "127.0.0.1",
        "localhost",
        "0.0.0.0",
    }:
        port = parsed.port or 8889
        netloc = f"{request_host}:{port}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    return url


def current_settings(request: Request | None = None) -> AppSettings:
    return AppSettings(
        video_device=settings.video_device,
        video_width=settings.video_width,
        video_height=settings.video_height,
        video_fps=settings.video_fps,
        video_fourcc=settings.video_fourcc,
        video_encoder=settings.video_encoder,
        video_encoder_preset=settings.video_encoder_preset,
        video_bitrate=settings.video_bitrate,
        audio_device=settings.audio_device,
        audio_sample_rate=settings.audio_sample_rate,
        audio_channels=settings.audio_channels,
        audio_block_size=settings.audio_block_size,
        audio_playback_gain=settings.audio_playback_gain,
        audio_metrics_interval_ms=settings.audio_metrics_interval_ms,
        mediamtx_webrtc_url=browser_webrtc_url(request),
        video_algorithm=settings.video_algorithm,
        audio_algorithm=settings.audio_algorithm,
    )


@router.get("/status")
def status(request: Request) -> dict:
    data = request.app.state.pipeline.status()
    data["system"] = get_system_info()
    return data


@router.get("/settings")
def get_settings(request: Request) -> AppSettings:
    return current_settings(request)


def apply_settings(new_settings: AppSettings) -> None:
    ok, error = is_video_format_supported(new_settings.video_device, new_settings.video_fourcc)
    if not ok:
        raise HTTPException(status_code=400, detail=error)
    for key, value in new_settings.model_dump().items():
        if hasattr(settings, key):
            setattr(settings, key, value)


@router.post("/settings")
async def update_settings(new_settings: AppSettings, request: Request) -> dict:
    apply_settings(new_settings)
    await request.app.state.event_bus.log("info", "设置已保存，重启管线后生效")
    return {"settings": current_settings(request), "requires_restart": True}


@router.get("/devices/video")
def video_devices() -> dict:
    return {"devices": list_video_devices()}


@router.get("/devices/audio")
def audio_devices() -> dict:
    return {"devices": list_audio_devices(settings.audio_sample_rate, settings.audio_channels)}


@router.post("/pipeline/start")
async def start_pipeline(request: Request) -> dict:
    return await request.app.state.pipeline.start()


@router.post("/pipeline/apply-start")
async def apply_start_pipeline(new_settings: AppSettings, request: Request) -> dict:
    apply_settings(new_settings)
    await request.app.state.event_bus.log("info", "已应用当前设置，正在启动管线")
    return await request.app.state.pipeline.start()


@router.post("/pipeline/stop")
async def stop_pipeline(request: Request) -> dict:
    return await request.app.state.pipeline.stop()


@router.post("/pipeline/restart")
async def restart_pipeline(request: Request) -> dict:
    return await request.app.state.pipeline.restart()


@router.get("/algorithms/video")
def video_algorithms() -> dict:
    return {"algorithms": VIDEO_NAMES, "selected": settings.video_algorithm}


@router.post("/algorithms/video/select")
async def select_video_algorithm(body: AlgorithmSelectRequest, request: Request) -> dict:
    if body.name not in VIDEO_NAMES:
        return {"ok": False, "error": "未知视频算法"}
    settings.video_algorithm = body.name
    await request.app.state.event_bus.log("info", f"已选择视频算法: {body.name}")
    return {"ok": True, "selected": settings.video_algorithm, "requires_restart": True}


@router.get("/algorithms/audio")
def audio_algorithms() -> dict:
    return {"algorithms": AUDIO_NAMES, "selected": settings.audio_algorithm}


@router.post("/algorithms/audio/select")
async def select_audio_algorithm(body: AlgorithmSelectRequest, request: Request) -> dict:
    if body.name not in AUDIO_NAMES:
        return {"ok": False, "error": "未知音频算法"}
    settings.audio_algorithm = body.name
    await request.app.state.event_bus.log("info", f"已选择音频算法: {body.name}")
    return {"ok": True, "selected": settings.audio_algorithm, "requires_restart": True}
