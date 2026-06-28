from dataclasses import asdict, dataclass
import numpy as np


@dataclass
class DetectionBox:
    x: int
    y: int
    w: int
    h: int
    label: str
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VideoAlgorithmResult:
    frame: np.ndarray
    boxes: list[DetectionBox]


class VideoAlgorithm:
    name: str = "base"

    def process(self, frame: np.ndarray) -> VideoAlgorithmResult:
        raise NotImplementedError
