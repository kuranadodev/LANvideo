from __future__ import annotations


def list_audio_devices() -> list[dict]:
    try:
        import sounddevice as sd
        devices = []
        for index, info in enumerate(sd.query_devices()):
            if info.get("max_input_channels", 0) > 0:
                devices.append({
                    "id": index,
                    "name": info.get("name", f"audio-{index}"),
                    "hostapi": str(info.get("hostapi")),
                    "channels": int(info.get("max_input_channels", 0)),
                    "default_sample_rate": int(info.get("default_samplerate", 48000)),
                    "available": True,
                })
        return devices or [{"id": None, "name": "未找到音频输入设备", "available": False}]
    except Exception as exc:
        return [{"id": None, "name": f"音频设备枚举失败: {exc}", "available": False}]
