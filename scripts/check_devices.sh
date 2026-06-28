#!/usr/bin/env bash
set -euo pipefail

missing=0
for cmd in v4l2-ctl ffmpeg arecord; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "缺少命令: $cmd"
    missing=1
  fi
done
if [ "$missing" -eq 1 ]; then
  echo "请安装依赖: sudo apt install -y ffmpeg v4l-utils alsa-utils"
fi

ls /dev/video* 2>/dev/null || true
v4l2-ctl --list-devices || true
ffmpeg -f v4l2 -list_formats all -i /dev/video0 || true
arecord -l || true
arecord -L || true
