from __future__ import annotations

import time
from datetime import datetime
import cv2
import numpy as np

from .video_base import DetectionBox, VideoAlgorithm, VideoAlgorithmResult


class DummyVideoAlgorithm(VideoAlgorithm):
    name = "dummy"

    def __init__(self) -> None:
        self._last_time = time.monotonic()
        self._fps = 0.0

    def process(self, frame: np.ndarray) -> VideoAlgorithmResult:
        now = time.monotonic()
        dt = now - self._last_time
        self._last_time = now
        if dt > 0:
            self._fps = 0.9 * self._fps + 0.1 * (1.0 / dt) if self._fps else 1.0 / dt
        output = frame.copy()
        h, w = output.shape[:2]
        box = DetectionBox(x=w // 4, y=h // 4, w=w // 3, h=h // 3, label="demo", score=0.98)
        cv2.rectangle(output, (box.x, box.y), (box.x + box.w, box.y + box.h), (0, 255, 0), 2)
        cv2.putText(output, f"FPS: {self._fps:.1f}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(output, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        return VideoAlgorithmResult(frame=output, boxes=[box])
