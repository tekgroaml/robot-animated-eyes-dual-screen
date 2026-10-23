#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
[[ $(uname -s) == Linux ]] || { echo "This installer requires Raspberry Pi OS or Debian Linux." >&2; exit 1; }
[[ $(id -u) != 0 ]] || { echo "Run as the desktop user; sudo is used only for APT." >&2; exit 1; }
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip python3-pygame
# Debian's SDL build supports the system's graphics stack and avoids Pi wheel builds.
python3 -m venv --system-site-packages .venv
if ! .venv/bin/python -c 'import pygame; assert pygame.version.vernum >= (2, 0, 0)' >/dev/null 2>&1; then
  sudo apt-get install -y build-essential python3-dev pkg-config libsdl2-dev libsdl2-image-dev \
    libsdl2-mixer-dev libsdl2-ttf-dev libportmidi-dev libfreetype6-dev libjpeg-dev libpng-dev
  .venv/bin/python -m pip install -r requirements.txt
fi
if [[ ${1:-} == --install-only ]]; then exit 0; fi
exec ./run.sh "$@"
