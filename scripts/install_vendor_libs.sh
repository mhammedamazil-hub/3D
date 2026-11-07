#!/bin/sh
# Extract the CI-transported Debian bookworm .debs into vendor/runtime/.
# Verifies SHA-256 checksums recorded by the workflow before extracting.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/.." && pwd)
DEBS="$ROOT/vendor/debs"
RUNTIME="$ROOT/vendor/runtime"

if [ ! -d "$DEBS" ]; then
  echo "ERROR: $DEBS not found." >&2
  echo "Run the 'Fetch Blender OS libraries' workflow (touch scripts/os-libs-request.txt," >&2
  echo "commit, push), then git pull and re-run this script." >&2
  exit 1
fi

cd "$DEBS"
sha256sum -c SHA256SUMS
mkdir -p "$RUNTIME"
for deb in ./*.deb; do
  dpkg-deb -x "$deb" "$RUNTIME"
done
echo "Extracted $(ls ./*.deb | wc -l) packages into $RUNTIME"
