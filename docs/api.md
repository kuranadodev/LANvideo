# API

## REST

- `GET /api/status`
- `GET /api/settings`
- `POST /api/settings`
- `GET /api/devices/video`
- `GET /api/devices/audio`
- `POST /api/pipeline/start`
- `POST /api/pipeline/apply-start`
- `POST /api/pipeline/stop`
- `POST /api/pipeline/restart`
- `GET /api/algorithms/video`
- `POST /api/algorithms/video/select`
- `GET /api/algorithms/audio`
- `POST /api/algorithms/audio/select`

## WebSocket

- `WS /ws/events`

消息类型：`video.metrics`、`detection.boxes`、`audio.waveform`、`audio.spectrum`、`audio.metrics`、`log`。
