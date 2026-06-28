from __future__ import annotations

from app.config import settings
from app.pipeline.audio_worker import AudioWorker
from app.pipeline.event_bus import EventBus
from app.pipeline.video_worker import VideoWorker


class PipelineManager:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.video_worker = VideoWorker(settings, event_bus)
        self.audio_worker = AudioWorker(settings, event_bus)

    async def start(self) -> dict:
        await self.event_bus.log("info", "正在启动管线")
        if not (self.video_worker.running or self.audio_worker.running):
            self.rebuild_workers()
        await self.video_worker.start()
        await self.audio_worker.start()
        return self.status()

    async def stop(self) -> dict:
        await self.event_bus.log("info", "正在停止管线")
        await self.video_worker.stop()
        await self.audio_worker.stop()
        return self.status()

    async def restart(self) -> dict:
        await self.stop()
        self.rebuild_workers()
        return await self.start()

    def rebuild_workers(self) -> None:
        self.video_worker = VideoWorker(settings, self.event_bus)
        self.audio_worker = AudioWorker(settings, self.event_bus)

    def status(self) -> dict:
        running = self.video_worker.running or self.audio_worker.running
        state = "running" if self.video_worker.running and self.audio_worker.running else "partial" if running else "stopped"
        if not running and (self.video_worker.error or self.audio_worker.error):
            state = "error"
        return {
            "running": running,
            "state": state,
            "video": {"running": self.video_worker.running, "device": settings.video_device, "width": settings.video_width, "height": settings.video_height, "fps": settings.video_fps, "actual_fps": self.video_worker.actual_fps, "error": self.video_worker.error},
            "audio": {"running": self.audio_worker.running, "device": settings.audio_device, "sample_rate": settings.audio_sample_rate, "channels": settings.audio_channels, "block_size": settings.audio_block_size, "error": self.audio_worker.error},
            "mediamtx": {"rtsp_url": settings.mediamtx_rtsp_url, "webrtc_url": settings.mediamtx_webrtc_url},
        }
