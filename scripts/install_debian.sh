#!/usr/bin/env bash
set -e
sudo apt update
sudo apt install -y \
  python3 \
  python3-venv \
  python3-pip \
  ffmpeg \
  v4l-utils \
  alsa-utils \
  nodejs \
  npm \
  curl \
  git \
  build-essential
