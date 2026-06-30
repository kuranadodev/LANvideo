from __future__ import annotations

import os
import shutil
import subprocess
import time
from typing import Any

import psutil

_CAPABILITY_CACHE: dict[str, Any] | None = None
_CAPABILITY_CACHE_TS = 0.0
_CAPABILITY_CACHE_TTL_SECONDS = 30.0


def _run_command(cmd: list[str], *, timeout: float = 2.0) -> tuple[bool, str, str]:
    try:
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
        output = f"{completed.stdout}\n{completed.stderr}".strip()
        return completed.returncode == 0, output, ""
    except Exception as exc:
        return False, "", str(exc)


def _ffmpeg_info() -> dict[str, Any]:
    ffmpeg_name = os.getenv("FFMPEG_PATH", "ffmpeg")
    path = shutil.which(ffmpeg_name) if os.path.basename(ffmpeg_name) == ffmpeg_name else ffmpeg_name
    available = bool(path) and (os.path.basename(ffmpeg_name) == ffmpeg_name or os.path.exists(path))
    info: dict[str, Any] = {"available": available, "path": path, "has_h264_nvenc": False}
    if not available:
        info["error"] = "ffmpeg not found in PATH"
        return info
    ok, output, error = _run_command([path, "-hide_banner", "-encoders"])
    if error:
        info["error"] = error
    if output:
        info["has_h264_nvenc"] = "h264_nvenc" in output
    info["encoder_probe_ok"] = ok
    return info


def _opencv_info() -> dict[str, Any]:
    try:
        import cv2

        has_cuda = hasattr(cv2, "cuda")
        device_count = 0
        cuda_error = None
        if has_cuda:
            try:
                device_count = int(cv2.cuda.getCudaEnabledDeviceCount())
            except Exception as exc:  # pragma: no cover - depends on host OpenCV build
                cuda_error = str(exc)
        info: dict[str, Any] = {
            "available": True,
            "version": getattr(cv2, "__version__", "unknown"),
            "cuda_available": has_cuda and device_count > 0,
            "cuda_device_count": device_count,
        }
        if cuda_error:
            info["cuda_error"] = cuda_error
        return info
    except Exception as exc:
        return {"available": False, "cuda_available": False, "cuda_device_count": 0, "error": str(exc)}


def _nvidia_smi_info() -> dict[str, Any]:
    path = shutil.which("nvidia-smi")
    info: dict[str, Any] = {"available": bool(path), "path": path, "gpus": []}
    if not path:
        info["error"] = "nvidia-smi not found in PATH"
        return info
    ok, output, error = _run_command(
        [path, "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
        timeout=2.0,
    )
    info["probe_ok"] = ok
    if error:
        info["error"] = error
    if output:
        gpus = []
        for line in output.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) >= 3:
                gpus.append({"name": parts[0], "driver_version": parts[1], "memory_total": parts[2]})
            elif line.strip():
                gpus.append({"name": line.strip()})
        info["gpus"] = gpus
    return info


def get_capability_info(*, force_refresh: bool = False) -> dict[str, Any]:
    global _CAPABILITY_CACHE, _CAPABILITY_CACHE_TS
    now = time.monotonic()
    if not force_refresh and _CAPABILITY_CACHE is not None and now - _CAPABILITY_CACHE_TS < _CAPABILITY_CACHE_TTL_SECONDS:
        return _CAPABILITY_CACHE
    _CAPABILITY_CACHE = {"ffmpeg": _ffmpeg_info(), "opencv": _opencv_info(), "nvidia_smi": _nvidia_smi_info()}
    _CAPABILITY_CACHE_TS = now
    return _CAPABILITY_CACHE


def get_system_info() -> dict:
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": psutil.virtual_memory().percent,
        "capabilities": get_capability_info(),
    }
