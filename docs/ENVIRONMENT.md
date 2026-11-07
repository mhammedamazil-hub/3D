# Sandbox environment audit — 2026-11-07

Measured, not assumed. Per `skills/realistic-blender-production/SKILL.md` §1.

## Machine

| Item | Value |
|---|---|
| OS | Debian GNU/Linux 12 (bookworm), 12.15 |
| Kernel / arch | Linux 6.1.158+, x86_64 |
| glibc | 2.36 (2.36-9+deb12u14) |
| CPU | 2 vCPU, Intel Xeon @ 2.60 GHz |
| RAM | 3.85 GiB total, no swap |
| Disk | 21 GB total, ~17.4 GB free after setup |
| GPU | **None.** No `/dev/dri`, no `nvidia-smi`. CPU Cycles only. |
| User / sudo | `user` (uid 1001), passwordless sudo available |

## Installed toolchain

| Tool | Version | Source |
|---|---|---|
| Python | 3.11.2 | system `/usr/bin/python3.11` |
| Blender (`bpy`) | **4.2.23 LTS** | PyPI wheel, in `.venv/` |
| NumPy | 2.4.6 | PyPI |
| Pillow | 13.0.0 | PyPI |
| FFmpeg | n9.0.2 (via `imageio-ffmpeg` 0.8.1) | bundled static binary |
| Git / gh | preinstalled; `gh` authenticated as `mhammedamazil-hub` | system |

`bpy` 4.2 LTS was chosen deliberately: it matches the skill's documented workflow, and
its `cp311` wheel matches this sandbox's Python 3.11. Newer `bpy` 5.1/5.2 wheels require
Python 3.13 and would not install here. Exact pins are in `requirements.txt`.

Blender runs as a Python module, so there is **no `blender` CLI binary**. Use
`scripts/blender-py <script.py>` instead of `blender -b --python <script.py>`.

## Network restrictions (important)

Reachable: `github.com`, `api.github.com`, `codeload.github.com`, `pypi.org`,
`files.pythonhosted.org`, `registry.npmjs.org`.

**Blocked:** Debian/Ubuntu apt mirrors, `download.blender.org`,
`raw.githubusercontent.com`, `objects.githubusercontent.com`, and GitHub Actions
artifact/log download hosts. So:

- Official Blender binaries cannot be downloaded here → PyPI `bpy` wheel is used.
- `apt-get install` cannot work in the sandbox → OS libraries are fetched by CI.
- `gh run view --log` / `gh run download` fail on redirect → read job status and
  annotations through `gh api`, and have CI push any needed text back to the branch.

## OS libraries

`bpy` initially failed with `ImportError: libXrender.so.1`. Eight X/GL libraries were
missing. They were **not** stubbed. The `Fetch Blender OS libraries` workflow ran in a
`debian:bookworm` container (matching this sandbox's OS and glibc), downloaded 52
official Debian packages with `apt-get --download-only`, recorded SHA-256 checksums and
provenance, and pushed them to this branch as a transport. They were then verified and
extracted into `vendor/runtime/` (gitignored, ~150 MB) and removed from Git tracking.

`scripts/env.sh` sets `LD_LIBRARY_PATH`, `LIBGL_DRIVERS_PATH`, and
`__EGL_VENDOR_LIBRARY_DIRS` to that tree, plus `OMP_NUM_THREADS=2` /
`OPENBLAS_NUM_THREADS=1` for this 2-vCPU box. `ldd` on `bpy/__init__.so` now reports
zero unresolved libraries.

Mesa llvmpipe is included, so headless Eevee works via software OpenGL — useful for fast
previews, not a GPU substitute.

## Verification (actual runs, not claims)

`scripts/env_doctor.py` — full results in `docs/environment-audit.json`:

- `import bpy` → `4.2.23 LTS`, `background=True`
- Cycles CPU still, 320×180, 24 samples + OIDN: **1.77 s**, PNG validated with Pillow
- 24 native rendered animation frames, 160×90, 8 samples: **6.68 s** total (~0.28 s/frame)
- H.264 encode (`libx264`, `yuv420p`, High profile) then full decode: **24/24 frames**, no errors
- Headless Eevee Next via llvmpipe, 320×180, 16 samples: **21.79 s**, PNG validated
- **TECHNICAL: PASS**

Both smoke stills were visually inspected: correct sphere/cube silhouettes, sun direction
and cast shadows agree, bevel highlight visible on the cube, AgX tonemapping active. These
are pipeline smoke tests, **not** realism samples or approved artwork.

## Capacity implications for production

The ~0.28 s/frame figure is for a trivial 160×90 8-sample scene and is **not** a
production estimate. Per the skill, benchmark representative full-resolution frames
before choosing chunk sizes. With 2 vCPU, 3.85 GiB RAM, and no GPU, expect 1080p Cycles
frames with volumetrics to be slow; heavy scenes may exceed RAM. Distributed rendering
via GitHub Actions is available and was proven working here.

Workspace/snapshot cap is ~128 MB / 10,000 files. `.venv/` (~2 GB) and `vendor/` are
excluded or gitignored; keep raw frame sequences out of Git.

## Rebuild

```bash
sh scripts/setup_sandbox.sh
```

If `vendor/runtime` is missing, update the timestamp in `scripts/os-libs-request.txt`,
commit and push to this branch; CI will push fresh `.debs`, then `git pull` and re-run
setup.
