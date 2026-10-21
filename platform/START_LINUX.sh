#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
printf '%s\n' 'Linguist-X AES67 shared gateway - Linux lab'
if ! command -v gst-launch-1.0 >/dev/null 2>&1; then
  echo 'Install GStreamer tools and plugins: sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good'
fi
if [ ! -x ".venv-shared/bin/python" ]; then python3 -m venv .venv-shared; fi
.venv-shared/bin/python -m pip install -r gateway_stage2/requirements.txt
exec .venv-shared/bin/python -m gateway_stage2.launch_shared
