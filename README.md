# 3D — realistic Blender production sandbox

Prepared 2026-11-07 per `skills/realistic-blender-production/SKILL.md`.
Measured audit and verified capabilities: **`docs/ENVIRONMENT.md`**.

## Quick start

```bash
# Run Python with Blender (bpy 4.2.23 LTS) in the prepared environment:
scripts/blender-py -c "import bpy; print(bpy.app.version_string)"

# Re-verify the whole pipeline (renders + encode/decode proof):
scripts/blender-py scripts/env_doctor.py

# Rebuild everything from scratch (venv + OS libs + verification):
sh scripts/setup_sandbox.sh
```

There is no `blender` CLI here — Blender is the PyPI `bpy` module (CPU Cycles;
headless Eevee works via software OpenGL). 2 vCPU / 3.85 GiB RAM / no GPU:
benchmark before committing to big renders.

## Layout

```text
skills/    production skill + vendored blender-skills library (94 specialists, MIT)
scripts/   setup, environment wrapper, doctor; future build/render/verify scripts
docs/      environment audit, OS-library provenance (SHA-256 + versions)
assets/    licensed source assets and credits (empty yet)
output/    requested deliverables (gitignored)
review/    temporary tests and smoke renders (gitignored)
vendor/    Debian X/GL libraries for bpy (gitignored; CI-transported)
.venv/     pinned Python environment (not snapshotted; setup script rebuilds it)
```

## Network-restricted sandbox

Only GitHub / PyPI / npm hosts are reachable. OS libraries arrive via the
`Fetch Blender OS libraries` GitHub Actions workflow (official Debian bookworm
packages, checksummed); re-trigger it by pushing a change to
`scripts/os-libs-request.txt`, then `git pull` and re-run setup.
