#!/bin/sh
# Source this file (`. scripts/env.sh`) or use it via scripts/blender-py.
# Points the dynamic loader at the vendored Debian bookworm X/GL libraries
# (extracted by scripts/install_vendor_libs.sh) and caps math-library threads
# for this 2-vCPU sandbox.
REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# When sourced from another script, $0 may not be this file; allow override.
if [ -n "${BLENDER_REPO_ROOT:-}" ]; then REPO_ROOT="$BLENDER_REPO_ROOT"; fi

VENDOR_LIB="$REPO_ROOT/vendor/runtime/usr/lib/x86_64-linux-gnu"
export LD_LIBRARY_PATH="$VENDOR_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LIBGL_DRIVERS_PATH="$VENDOR_LIB/dri"
export __EGL_VENDOR_LIBRARY_DIRS="$REPO_ROOT/vendor/runtime/usr/share/glvnd/egl_vendor.d"
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=2
export BLENDER_REPO_ROOT="$REPO_ROOT"
