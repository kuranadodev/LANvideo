from __future__ import annotations

import cv2
import numpy as np

from .video_base import DetectionBox, VideoAlgorithm, VideoAlgorithmResult


class MotionVideoAlgorithm(VideoAlgorithm):
    name = "motion"

    def __init__(self) -> None:
        self._prev_gray: np.ndarray | None = None

    def process(self, frame: np.ndarray) -> VideoAlgorithmResult:
        output = frame.copy()
        gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (21, 21), 0)
        boxes: list[DetectionBox] = []
        if self._prev_gray is not None:
            delta = cv2.absdiff(self._prev_gray, gray)
            thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                if cv2.contourArea(contour) < 800:
                    continue
                x, y, w, h = cv2.boundingRect(contour)
                box = DetectionBox(x=x, y=y, w=w, h=h, label="motion", score=1.0)
                boxes.append(box)
                cv2.rectangle(output, (x, y), (x + w, y + h), (0, 128, 255), 2)
                cv2.putText(output, "motion", (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 128, 255), 2)
        self._prev_gray = gray
        return VideoAlgorithmResult(frame=output, boxes=boxes)
