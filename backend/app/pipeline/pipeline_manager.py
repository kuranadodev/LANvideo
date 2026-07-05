from __future__ import annotations

from app.config import settings
from app.pipeline.audio_worker import AudioWorker
from app.pipeline.event_bus import EventBus
from app.pipeline.ffmpeg_publisher import FFmpegPublisher
from app.pipeline.video_worker import VideoWorker
from app.utils.system_info import get_capability_info


class PipelineManager:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.publisher = self._build_publisher()
        self.video_worker = VideoWorker(settings, event_bus, self.publisher)
        self.audio_worker = AudioWorker(settings, event_bus, self.publisher)

    async def start(self) -> dict:
        running = self.video_worker.running or self.audio_worker.running
        if running:
            await self.event_bus.log("info", "管线运行中，正在停止后重新启动")
            await self.stop()
        await self.event_bus.log("info", "正在启动管线")
        await self._log_capability_summary()
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


    async def _log_capability_summary(self) -> None:
        capabilities = get_capability_info()
        ffmpeg = capabilities.get("ffmpeg", {})
        opencv = capabilities.get("opencv", {})
        nvidia = capabilities.get("nvidia_smi", {})
        gpu_names = ", ".join(gpu.get("name", "unknown") for gpu in nvidia.get("gpus", [])) or "未检测到"
        await self.event_bus.log(
            "info",
            f"系统能力: encoder={settings.video_encoder}, ffmpeg_nvenc={ffmpeg.get('has_h264_nvenc')}, "
            f"opencv_cuda_devices={opencv.get('cuda_device_count', 0)}, nvidia_gpus={gpu_names}",
        )
        if settings.video_encoder == "h264_nvenc" and not ffmpeg.get("has_h264_nvenc"):
            await self.event_bus.log("warning", "已选择 h264_nvenc，但当前 FFmpeg 未检测到 h264_nvenc 编码器")

    def _build_publisher(self) -> FFmpegPublisher:
        return FFmpegPublisher(
            settings.ffmpeg_path,
            settings.mediamtx_rtsp_url,
            settings.video_width,
            settings.video_height,
            settings.video_fps,
            settings.video_pix_fmt,
            settings.audio_sample_rate,
            settings.audio_channels,
            settings.audio_playback_gain,
            settings.video_encoder,
            settings.video_encoder_preset,
            settings.video_bitrate,
        )

    def rebuild_workers(self) -> None:
        self.publisher = self._build_publisher()
        self.video_worker = VideoWorker(settings, self.event_bus, self.publisher)
        self.audio_worker = AudioWorker(settings, self.event_bus, self.publisher)

    def status(self) -> dict:
        running = self.video_worker.running or self.audio_worker.running
        state = "running" if self.video_worker.running and self.audio_worker.running else "partial" if running else "stopped"
        if not running and (self.video_worker.error or self.audio_worker.error):
            state = "error"
        return {
            "running": running,
            "state": state,
            "video": {"running": self.video_worker.running, "device": settings.video_device, "width": settings.video_width, "height": settings.video_height, "fps": settings.video_fps, "analysis_fps": settings.video_analysis_fps, "actual_fps": self.video_worker.actual_fps, "pipeline_mode": settings.video_pipeline_mode, "encoder": settings.video_encoder, "encoder_preset": settings.video_encoder_preset, "bitrate": settings.video_bitrate, "error": self.video_worker.error},
            "audio": {"running": self.audio_worker.running, "device": settings.audio_device, "sample_rate": settings.audio_sample_rate, "channels": settings.audio_channels, "block_size": settings.audio_block_size, "playback_gain": settings.audio_playback_gain, "metrics_interval_ms": settings.audio_metrics_interval_ms, "error": self.audio_worker.error},
            "mediamtx": {"rtsp_url": settings.mediamtx_rtsp_url, "webrtc_url": settings.mediamtx_webrtc_url},
        }
