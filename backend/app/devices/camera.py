from __future__ import annotations

from pathlib import Path
import subprocess


def list_video_devices() -> list[dict]:
    devices = []
    for path in sorted(Path("/dev").glob("video*")):
        devices.append({"id": str(path), "name": path.name, "available": path.exists()})
    by_id = Path("/dev/v4l/by-id")
    if by_id.exists():
        for path in sorted(by_id.iterdir()):
            devices.append({"id": str(path), "name": path.name, "available": path.exists(), "stable": True})
    if devices:
        return devices
    return [{"id": "/dev/video0", "name": "未找到视频设备", "available": False}]
