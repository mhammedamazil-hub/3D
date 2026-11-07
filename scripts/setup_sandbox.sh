#!/bin/sh
# Reproduce the Blender production sandbox (see docs/ENVIRONMENT.md).
# Network note: this sandbox reaches only github.com / pypi.org, so Blender
# comes from the PyPI `bpy` wheel and the X/GL OS libraries come from the
# "Fetch Blender OS libraries" GitHub Actions workflow (official Debian
# bookworm packages), extracted locally by scripts/install_vendor_libs.sh.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/.." && pwd)
cd "$ROOT"

echo "== 1/4 Python venv + pinned packages =="
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv || {
    python3 -m pip install --user --break-system-packages -q virtualenv
    python3 -m virtualenv .venv
  }
fi
.venv/bin/pip install --no-input --progress-bar off -r requirements.txt

echo "== 2/4 Vendored OS libraries =="
if [ -d vendor/debs ]; then
  sh scripts/install_vendor_libs.sh
else
  echo "NOTE: vendor/debs missing. If vendor/runtime is also missing, push a change"
  echo "to scripts/os-libs-request.txt to trigger the fetch workflow, git pull,"
  echo "then re-run this script."
fi

echo "== 3/4 Import check =="
sh scripts/blender-py -c "import bpy; print('bpy', bpy.app.version_string, 'background=', bpy.app.background)"

echo "== 4/4 Full doctor (renders + encode/decode proof) =="
sh scripts/blender-py scripts/env_doctor.py
echo "Setup complete. Report: review/env_report.json"
