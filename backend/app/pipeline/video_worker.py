from __future__ import annotations

import asyncio
from collections.abc import Coroutine
import time
import cv2

from app.algorithms.video_dummy import DummyVideoAlgorithm
from app.algorithms.video_motion import MotionVideoAlgorithm
from app.pipeline.ffmpeg_publisher import FFmpegPublisher

VIDEO_ALGORITHMS = {"dummy": DummyVideoAlgorithm, "motion": MotionVideoAlgorithm}


class VideoWorker:
    def __init__(self, settings, event_bus, publisher: FFmpegPublisher) -> None:
        self.settings = settings
        self.event_bus = event_bus
        self.publisher = publisher
        self.running = False
        self.error: str | None = None
        self.actual_fps = 0.0
        self._task: asyncio.Task | None = None
        self._stop = False
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        if self.running:
            return
        if self._task and not self._task.done():
            return
        self._loop = asyncio.get_running_loop()
        self._stop = False
        self.error = None
        self._task = asyncio.create_task(asyncio.to_thread(self._run))

    async def stop(self) -> None:
        self._stop = True
        if self._task and not self._task.done():
            done, _ = await asyncio.wait([self._task], timeout=5)
            if done:
                self._task = None
        elif self._task:
            self._task = None
        if not self._task:
            self.running = False

    def _submit_to_loop(self, coro: Coroutine) -> None:
        if not self._loop or self._loop.is_closed():
            coro.close()
            return
        try:
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            future.add_done_callback(lambda item: item.exception())
        except RuntimeError:
            coro.close()

    def _threadsafe_publish(self, message: dict) -> None:
        if self._loop and not self._loop.is_closed():
            self._submit_to_loop(self.event_bus.publish(message))

    def _threadsafe_log(self, level: str, message: str) -> None:
        if self._loop and not self._loop.is_closed():
            self._submit_to_loop(self.event_bus.log(level, message))

    @staticmethod
    def _normalize_fourcc(value: str | None) -> str:
        code = (value or "").strip().upper()
        if code in {"MJPEG", "JPEG"}:
            return "MJPG"
        if code in {"H.264", "X264", "AVC1"}:
            return "H264"
        return code[:4]

    @staticmethod
    def _decode_fourcc(value: float) -> str:
        try:
            code = int(value)
        except (TypeError, ValueError):
            return ""
        chars = [chr((code >> 8 * i) & 0xFF) for i in range(4)]
        return "".join(ch for ch in chars if ch.isprintable()).strip()

    def _run(self) -> None:
        cap = cv2.VideoCapture(self.settings.video_device, cv2.CAP_V4L2)
        if not cap.isOpened():
            self.error = f"无法打开视频设备: {self.settings.video_device}"
            self._threadsafe_log("error", self.error)
            return
        requested_fourcc = self._normalize_fourcc(self.settings.video_fourcc)
        if requested_fourcc:
            fourcc = cv2.VideoWriter_fourcc(*requested_fourcc)
            cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.video_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.video_height)
        cap.set(cv2.CAP_PROP_FPS, self.settings.video_fps)
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        actual_fourcc = self._decode_fourcc(cap.get(cv2.CAP_PROP_FOURCC))
        requested_format = requested_fourcc or "默认"
        self._threadsafe_log(
            "info",
            f"摄像头请求参数: {requested_format} {self.settings.video_width}x{self.settings.video_height}@{self.settings.video_fps}; "
            f"实际协商: {actual_fourcc or '未知'} {actual_width}x{actual_height}@{actual_fps:.2f}",
        )
        algo_cls = VIDEO_ALGORITHMS.get(self.settings.video_algorithm, DummyVideoAlgorithm)
        algorithm = algo_cls()
        output_width = self.settings.video_width
        output_height = self.settings.video_height
        publisher = self.publisher
        publisher.on_log = lambda line: self._threadsafe_log("info", f"FFmpeg: {line}")
        try:
            publisher.start()
            self.running = True
            self._threadsafe_log("info", "视频管线已启动")
            frame_index = 0
            last = time.monotonic()
            logged_resize = False
            while not self._stop:
                ok, frame = cap.read()
                if not ok:
                    self.error = "读取视频帧失败"
                    self._threadsafe_log("error", self.error)
                    time.sleep(0.2)
                    continue
                frame_height, frame_width = frame.shape[:2]
                if frame_width != output_width or frame_height != output_height:
                    if not logged_resize:
                        self._threadsafe_log("warning", f"摄像头实际输出 {frame_width}x{frame_height}，已缩放为 {output_width}x{output_height} 后推流")
                        logged_resize = True
                    frame = cv2.resize(frame, (output_width, output_height), interpolation=cv2.INTER_AREA)
                start = time.monotonic()
                result = algorithm.process(frame)
                algorithm_ms = (time.monotonic() - start) * 1000
                if result.frame.shape[:2] != (output_height, output_width):
                    actual_height, actual_width = result.frame.shape[:2]
                    self._threadsafe_log("warning", f"算法输出尺寸 {actual_width}x{actual_height} 与推流尺寸不一致，已缩放为 {output_width}x{output_height}")
                    result.frame = cv2.resize(result.frame, (output_width, output_height), interpolation=cv2.INTER_AREA)
                publisher.write_frame(result.frame)
                frame_index += 1
                now = time.monotonic()
                dt = now - last
                last = now
                if dt > 0:
                    fps = 1.0 / dt
                    self.actual_fps = 0.9 * self.actual_fps + 0.1 * fps if self.actual_fps else fps
                self._threadsafe_publish({"type": "video.metrics", "fps": self.actual_fps, "frame_index": frame_index, "algorithm_ms": algorithm_ms, "width": output_width, "height": output_height})
                self._threadsafe_publish({"type": "detection.boxes", "frame_index": frame_index, "boxes": [box.to_dict() for box in result.boxes]})
        except Exception as exc:
            self.error = str(exc)
            self._threadsafe_log("error", f"视频管线异常: {exc}")
        finally:
            publisher.stop()
            cap.release()
            self.running = False
            self._threadsafe_log("info", "视频管线已停止")
