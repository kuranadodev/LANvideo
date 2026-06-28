from __future__ import annotations

SAMPLE_RATE_CANDIDATES = [8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200, 96000, 176400, 192000]


def _check_input_settings(sd, *, device: int, sample_rate: int, channels: int) -> tuple[bool, str | None]:
    try:
        sd.check_input_settings(device=device, samplerate=sample_rate, channels=channels)
        return True, None
    except Exception as exc:
        return False, str(exc)


def list_audio_devices(requested_sample_rate: int | None = None, channels: int = 1) -> list[dict]:
    try:
        import sounddevice as sd

        devices = []
        for index, info in enumerate(sd.query_devices()):
            max_input_channels = int(info.get("max_input_channels", 0))
            if max_input_channels <= 0:
                continue

            probe_channels = max_input_channels
            configured_channels = min(channels, max_input_channels)
            supported_sample_rates: list[int] = []
            sample_rate_errors: dict[int, str] = {}
            for sample_rate in SAMPLE_RATE_CANDIDATES:
                ok, error = _check_input_settings(
                    sd,
                    device=index,
                    sample_rate=sample_rate,
                    channels=probe_channels,
                )
                if ok:
                    supported_sample_rates.append(sample_rate)
                elif error:
                    sample_rate_errors[sample_rate] = error

            max_sample_rate = max(supported_sample_rates) if supported_sample_rates else None
            device = {
                "id": index,
                "name": info.get("name", f"audio-{index}"),
                "hostapi": str(info.get("hostapi")),
                "channels": max_input_channels,
                "max_channels": max_input_channels,
                "default_sample_rate": int(info.get("default_samplerate", 48000)),
                "supported_sample_rates": supported_sample_rates,
                "max_sample_rate": max_sample_rate,
                "available": True,
            }
            if requested_sample_rate is not None:
                ok, error = _check_input_settings(
                    sd,
                    device=index,
                    sample_rate=requested_sample_rate,
                    channels=configured_channels,
                )
                device["supports_configured_sample_rate"] = ok
                device["sample_rate_error"] = error
            if sample_rate_errors:
                device["sample_rate_errors"] = sample_rate_errors
            devices.append(device)
        return devices or [{"id": None, "name": "未找到音频输入设备", "available": False}]
    except Exception as exc:
        return [{"id": None, "name": f"音频设备枚举失败: {exc}", "available": False}]
