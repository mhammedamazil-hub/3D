#!/usr/bin/env bash
# Fetches the Horizon reference implementation (MIT) into ../horizon (never into the
# voxelcore repo tree — the C++ engine is an original implementation, Horizon is a
# functional reference only).
set -euo pipefail
DEST="${1:-$(cd "$(dirname "$0")/.." && pwd)/../horizon}"
if [ -d "$DEST/.git" ]; then echo "Horizon already present at $DEST ($(git -C "$DEST" rev-parse --short HEAD))"; exit 0; fi
git clone --depth 1 https://github.com/horizon-rust/horizon.git "$DEST"
echo "Horizon reference clone: $DEST @ $(git -C "$DEST" rev-parse HEAD)"
