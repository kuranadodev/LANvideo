from __future__ import annotations

from dataclasses import asdict
from fastapi import APIRouter, Request

from app.algorithms.video_dummy import DummyVideoAlgorithm
from app.algorithms.video_motion import MotionVideoAlgorithm
from app.config import settings
from app.devices.camera import list_video_devices
from app.devices.microphone import list_audio_devices
from app.schemas.messages import AlgorithmSelectRequest
from app.schemas.settings import AppSettings
from app.utils.system_info import get_system_info

router = APIRouter(prefix="/api")
VIDEO_NAMES = [DummyVideoAlgorithm.name, MotionVideoAlgorithm.name]
AUDIO_NAMES = ["fft"]


def current_settings() -> AppSettings:
    return AppSettings(
        video_device=settings.video_device,
        video_width=settings.video_width,
        video_height=settings.video_height,
        video_fps=settings.video_fps,
        video_fourcc=settings.video_fourcc,
        audio_device=settings.audio_device,
        audio_sample_rate=settings.audio_sample_rate,
        audio_channels=settings.audio_channels,
        audio_block_size=settings.audio_block_size,
        mediamtx_webrtc_url=settings.mediamtx_webrtc_url,
        video_algorithm=settings.video_algorithm,
        audio_algorithm=settings.audio_algorithm,
    )


@router.get("/status")
def status(request: Request) -> dict:
    data = request.app.state.pipeline.status()
    data["system"] = get_system_info()
    return data


@router.get("/settings")
def get_settings() -> AppSettings:
    return current_settings()


@router.post("/settings")
async def update_settings(new_settings: AppSettings, request: Request) -> dict:
    for key, value in new_settings.model_dump().items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    await request.app.state.event_bus.log("info", "设置已保存，重启管线后生效")
    return {"settings": current_settings(), "requires_restart": True}


@router.get("/devices/video")
def video_devices() -> dict:
    return {"devices": list_video_devices()}


@router.get("/devices/audio")
def audio_devices() -> dict:
    return {"devices": list_audio_devices()}


@router.post("/pipeline/start")
async def start_pipeline(request: Request) -> dict:
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
