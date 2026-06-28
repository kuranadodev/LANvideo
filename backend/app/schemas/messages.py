from typing import Literal
from pydantic import BaseModel


class AlgorithmSelectRequest(BaseModel):
    name: str


class DetectionBoxMessage(BaseModel):
    x: int
    y: int
    w: int
    h: int
    label: str
    score: float


class LogMessage(BaseModel):
    type: Literal["log"] = "log"
    timestamp: int
    level: str
    message: str
