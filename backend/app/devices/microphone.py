from __future__ import annotations


def list_audio_devices(requested_sample_rate: int | None = None, channels: int = 1) -> list[dict]:
    try:
        import sounddevice as sd
        devices = []
        for index, info in enumerate(sd.query_devices()):
            if info.get("max_input_channels", 0) > 0:
                device = {
                    "id": index,
                    "name": info.get("name", f"audio-{index}"),
                    "hostapi": str(info.get("hostapi")),
                    "channels": int(info.get("max_input_channels", 0)),
                    "default_sample_rate": int(info.get("default_samplerate", 48000)),
                    "available": True,
                }
                if requested_sample_rate is not None:
                    try:
                        sd.check_input_settings(
                            device=index,
                            samplerate=requested_sample_rate,
                            channels=min(channels, device["channels"]),
                        )
                        device["supports_configured_sample_rate"] = True
                        device["sample_rate_error"] = None
                    except Exception as exc:
                        device["supports_configured_sample_rate"] = False
                        device["sample_rate_error"] = str(exc)
                devices.append(device)
        return devices or [{"id": None, "name": "未找到音频输入设备", "available": False}]
    except Exception as exc:
        return [{"id": None, "name": f"音频设备枚举失败: {exc}", "available": False}]
