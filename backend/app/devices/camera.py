from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess


_FORMAT_RE = re.compile(r"\[\d+\]:\s+'([^']+)'\s*\(([^)]*)\)")
_FFMPEG_FORMAT_RE = re.compile(r"Raw\s*\:\s*([^:]+)\s*:\s*'([^']+)'")
_COMPRESSED_FORMAT_RE = re.compile(r"Compressed\s*:\s*([^:]+)\s*:\s*'([^']+)'")


def _normalize_fourcc(value: str | None) -> str:
    code = (value or "").strip().upper()
    if code in {"MJPEG", "JPEG"}:
        return "MJPG"
    if code in {"H.264", "X264", "AVC1"}:
        return "H264"
    return code[:4]


def _format_label(fourcc: str, description: str | None = None) -> str:
    names = {"MJPG": "MJPEG", "H264": "H.264", "YUYV": "YUYV"}
    name = names.get(fourcc, fourcc)
    if description and description.upper() != name.upper():
        return f"{name} ({description})"
    return name


def _dedupe_formats(formats: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique = []
    for item in formats:
        fourcc = _normalize_fourcc(item.get("fourcc"))
        if not fourcc or fourcc in seen:
            continue
        seen.add(fourcc)
        unique.append({"fourcc": fourcc, "label": _format_label(fourcc, item.get("label"))})
    return unique


def _probe_with_v4l2_ctl(device: str) -> tuple[list[dict], str | None]:
    if not shutil.which("v4l2-ctl"):
        return [], "未安装 v4l2-ctl"
    try:
        proc = subprocess.run(
            ["v4l2-ctl", "--list-formats-ext", "-d", device],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return [], "v4l2-ctl 探测超时"
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    formats = [
        {"fourcc": match.group(1), "label": match.group(2).strip()}
        for match in _FORMAT_RE.finditer(output)
    ]
    error = None if proc.returncode == 0 else output.strip() or f"v4l2-ctl 退出码 {proc.returncode}"
    return _dedupe_formats(formats), error


def _probe_with_ffmpeg(device: str) -> tuple[list[dict], str | None]:
    if not shutil.which("ffmpeg"):
        return [], "未安装 ffmpeg"
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-f", "v4l2", "-list_formats", "all", "-i", device],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return [], "ffmpeg 探测超时"
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    formats: list[dict] = []
    for regex in (_FFMPEG_FORMAT_RE, _COMPRESSED_FORMAT_RE):
        formats.extend({"fourcc": m.group(2), "label": m.group(1).strip()} for m in regex.finditer(output))
    return _dedupe_formats(formats), output.strip() or None


def probe_video_formats(device: str) -> tuple[list[dict], str | None]:
    formats, error = _probe_with_v4l2_ctl(device)
    if formats:
        return formats, None
    fallback_formats, fallback_error = _probe_with_ffmpeg(device)
    if fallback_formats:
        return fallback_formats, None
    return [], error or fallback_error


def list_video_devices() -> list[dict]:
    devices = []
    for path in sorted(Path("/dev").glob("video*")):
        formats, format_error = probe_video_formats(str(path))
        devices.append({"id": str(path), "name": path.name, "available": path.exists(), "formats": formats, "format_error": format_error})
    by_id = Path("/dev/v4l/by-id")
    if by_id.exists():
        for path in sorted(by_id.iterdir()):
            formats, format_error = probe_video_formats(str(path))
            devices.append({"id": str(path), "name": path.name, "available": path.exists(), "stable": True, "formats": formats, "format_error": format_error})
    if devices:
        return devices
    return [{"id": "/dev/video0", "name": "未找到视频设备", "available": False, "formats": [], "format_error": "未找到视频设备"}]


def is_video_format_supported(device: str, fourcc: str | None) -> tuple[bool, str | None]:
    requested = _normalize_fourcc(fourcc)
    if not requested:
        return True, None
    formats, error = probe_video_formats(device)
    if not formats:
        return False, error or "无法探测摄像头支持的编码格式"
    supported = {item["fourcc"] for item in formats}
    if requested not in supported:
        return False, f"摄像头 {device} 不支持编码格式 {requested}，支持: {', '.join(sorted(supported))}"
    return True, None
