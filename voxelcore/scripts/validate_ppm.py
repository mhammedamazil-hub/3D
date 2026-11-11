#!/usr/bin/env python3
# PROJECT VOXELCORE — validate an RGB8 PPM dump from the Vulkan headless renderer.
# Usage: validate_ppm.py <file.ppm>
# Checks: binary P6 magic, dimensions, exact body length, and that the frame contains a
# meaningful number of non-sky pixels (the clear color is (89,140,217), 0.85*255 -> 217).
import sys

def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "vulkan_render.ppm"
    data = open(path, "rb").read()
    magic, _, rest = data.partition(b"\n")
    assert magic == b"P6", f"bad magic {magic!r}"
    header, _, body = rest.partition(b"255\n")
    parts = header.split()
    w, h = int(parts[0]), int(parts[1])
    assert len(body) == w * h * 3, f"PPM body {len(body)} != {w*h*3}"
    sky = (89, 140, 217)
    def is_sky(px):
        return all(abs(int(c) - s) <= 2 for c, s in zip(px, sky))
    non_sky = sum(1 for i in range(0, len(body), 3) if not is_sky(body[i:i + 3]))
    print(f"PPM OK: {w}x{h}, bytes={len(body)}, non-sky-pixel-count={non_sky}")
    assert non_sky > 1000, "frame appears empty (all sky)"
    return 0

if __name__ == "__main__":
    sys.exit(main())
