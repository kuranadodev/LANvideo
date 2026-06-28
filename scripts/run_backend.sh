#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
if [ -z "${MEDIAMTX_WEBRTC_URL:-}" ]; then
  lan_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  if [ -n "$lan_ip" ]; then
    export MEDIAMTX_WEBRTC_URL="http://${lan_ip}:8889/processed"
  fi
fi
echo "MediaMTX WebRTC URL: ${MEDIAMTX_WEBRTC_URL:-http://127.0.0.1:8889/processed}"
uvicorn app.main:app --host 0.0.0.0 --port 8000
