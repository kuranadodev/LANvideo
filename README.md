# LANvideo USB 摄像头图像/音频算法实验台

一个运行在 Debian 13 小主机上的局域网网页端实验平台，用于快速调试 USB 摄像头图像算法和麦克风音频算法。后端使用 FastAPI、OpenCV、sounddevice 和 FFmpeg，视频通过 MediaMTX 转 WebRTC，前端使用 React + Vite + TypeScript。

## 硬件环境

- Dell 小主机，Intel i5-8500，16GB RAM，256GB SSD
- Debian 13
- 普通 USB 摄像头，带麦克风
- 可选 NVIDIA RTX A400；第一版默认不依赖 GPU

## 安装系统依赖

```bash
bash scripts/install_debian.sh
```

MediaMTX 第一版建议手动下载二进制并放到 `/usr/local/bin/mediamtx`。

## 检查摄像头和麦克风

```bash
bash scripts/check_devices.sh
```

如果 `/dev/video0` 权限不足，将当前用户加入设备组后重新登录：

```bash
sudo usermod -aG video,audio $USER
```

## 启动 MediaMTX

```bash
bash scripts/run_mediamtx.sh
```

RTSP 输入地址：`rtsp://127.0.0.1:8554/processed`。
浏览器 WebRTC 地址：`http://<server-ip>:8889/processed`。

## 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
MEDIAMTX_WEBRTC_URL=http://<server-ip>:8889/processed uvicorn app.main:app --host 0.0.0.0 --port 8000
```

也可以使用：

```bash
bash scripts/run_backend.sh
```

局域网内其它机器访问时，浏览器 WebRTC 地址必须使用服务器 IP。`MEDIAMTX_WEBRTC_URL` 未显式设置时，后端会尽量根据请求主机名把默认的 `127.0.0.1` 播放地址转换为浏览器可访问的服务器地址；也可以通过环境变量固定为 `http://<server-ip>:8889/processed`。

## 启动前端

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

也可以使用：

```bash
bash scripts/run_frontend.sh
```

## 浏览器访问

打开：`http://<server-ip>:5173`。

默认不做认证，适合可信局域网使用。需要开放端口：8000、5173、8889；8554 通常只需要本机访问。

## 常见问题

### `/dev/video0` 权限不足

将用户加入 video 组并重新登录：

```bash
sudo usermod -aG video $USER
```

### 麦克风无权限

将用户加入 audio 组，或检查 PipeWire/PulseAudio/ALSA 配置：

```bash
sudo usermod -aG audio $USER
```

### FFmpeg 推流失败

确认 MediaMTX 已启动，且 `rtsp://127.0.0.1:8554/processed` 可写入。后端日志面板会显示 FFmpeg stderr。

### MediaMTX 无画面

确认已经点击“启动管线”，摄像头可用，FFmpeg 没有异常退出，并访问 `http://<server-ip>:8889/processed`。如果视频区域显示 `127.0.0.1` 拒绝连接，说明浏览器正在访问客户端本机，请设置 `MEDIAMTX_WEBRTC_URL=http://<server-ip>:8889/processed` 后重启后端。

### 浏览器打不开 WebRTC 页面

检查防火墙、MediaMTX 是否监听 8889，以及浏览器是否能访问服务器 IP。

### 延迟过高

第一版使用 CPU x264 ultrafast + zerolatency。可降低分辨率或帧率，例如 640x480@15fps。

### CPU 占用过高

降低分辨率、帧率，减少运动检测复杂度。第一版不默认启用 NVENC。
