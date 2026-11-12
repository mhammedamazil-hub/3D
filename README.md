# Monsoon Light — Kerala / Five Worlds Blender v3

## Current delivery — Five Worlds Blender v3: fully modeled pure-3D worlds

The user rejected the earlier WebGL screenshot-capture route **and** the v2 Blender/Cycles backplate route. Every one of the five worlds is now rebuilt from scratch with `bpy` as an editable, fully modeled 3D scene. The generated JPGs are **visual references only**: no image datablock, image texture, environment texture, photo backplate, HDRI or generated image mask exists inside any final `.blend`.

- `output/FiveWorlds_BlenderV3_01_AlpineLake.blend` … `output/FiveWorlds_BlenderV3_05_RainforestTemple.blend` — five frozen Blender 4.2.23 pure-procedural 3D scenes.
- `output/FiveWorlds_BlenderV3_01_AlpineLake_1080p30_10s.mp4` … `output/FiveWorlds_BlenderV3_05_RainforestTemple_1080p30_10s.mp4` — five 1920×1080, 30 fps, exactly 10 s silent H.264 videos.
- `output/FiveWorlds_BlenderV3_AllScenes_1080p30_50s.mp4` — all five back-to-back, exactly 50 s.
- `assets/references/v6/00_five_worlds_blender_v3_contact.jpg` — contact sheet extracted from the final Blender MP4s by CI.
- `docs/FIVE_WORLDS_BLENDER_V3.md`, `docs/FIVE_WORLDS_BLENDER_V3_BRIEF.md`, `docs/FIVE_WORLDS_BLENDER_V3_REFERENCE_ANALYSIS.md` — review, locked brief and reference-only analysis.
- `docs/FIVE_WORLDS_BLENDER_V3_MANIFEST.json`, `docs/FIVE_WORLDS_BLENDER_V3_BLEND_AUDIT.json`, `docs/FIVE_WORLDS_BLENDER_V3_RECEIPT.json`, `docs/FIVE_WORLDS_BLENDER_V3_VALIDATION.json`, `docs/FIVE_WORLDS_BLENDER_V3_LOCAL_VALIDATION.json` — frozen scenes, independent zero-image audit, render receipt, CI validation and independent delivery validation.
- `docs/five_worlds_blender_v3_skill_94_review.json` / `docs/FIVE_WORLDS_BLENDER_V3_SKILL_94_REVIEW.md` — all **94** pinned `.claude/skills` documents rechecked as production guidance, compatibility checks, N/A disciplines and QA/exclusion lenses. This is not a claim that 94 styles were mixed into one image.
- `scripts/build_five_worlds_blender_v3.py`, `scripts/render_five_worlds_blender_v3.py`, `scripts/audit_five_worlds_blender_v3.py`, `scripts/finalize_five_worlds_blender_v3.py`, `scripts/verify_five_worlds_blender_v3.py` — pure-3D builder, zero-image shard renderer, standalone auditor, assembler and independent verifier.
- `.github/workflows/render-five-worlds-blender-v3.yml` — independent frozen-scene audit, 15 Cycles CPU shards × 100 frames, assembly and commit-back.

Render spec: Cycles CPU, 4 samples, adaptive sampling, OpenImageDenoise `RGB_ALBEDO_NORMAL`, AgX Medium High Contrast, 1920×1080, 30 fps, 300 frames per scene, H.264/yuv420p `libx264` CRF 18. The final MP4s, contact sheet, receipt and validation are written by the CI workflow's commit-back step. CI run `43064656588` succeeded with 15/15 no-image shard receipts; the receipt, CI validation, CI blend audit and independent local validation all report `pass:true` with no errors.

Rebuild/verify locally:

```bash
sh scripts/blender-py scripts/build_five_worlds_blender_v3.py --out output --manifest docs/FIVE_WORLDS_BLENDER_V3_MANIFEST.json --width 1920 --height 1080 --samples 4 --fps 30 --frames 300
sh scripts/blender-py scripts/audit_five_worlds_blender_v3.py --manifest docs/FIVE_WORLDS_BLENDER_V3_MANIFEST.json --out docs/FIVE_WORLDS_BLENDER_V3_BLEND_AUDIT.json
python3 scripts/verify_five_worlds_blender_v3.py
```

## Superseded / rejected routes

- **v1 WebGL:** `web/`, `output/FiveWorlds_*_720p30_10s.mp4`, `docs/FIVE_WORLDS_V1.md` and the v1 receipt/validation are historical comparison artifacts only; the user rejected the browser route.
- **v2 Blender 2.5D:** `output/FiveWorlds_Blender_*.blend`, `output/FiveWorlds_Blender_*_1080p30_10s.mp4`, `docs/FIVE_WORLDS_BLENDER_V2.md` and the v2 receipt/validation are rejected because photographic plates were packed into the scenes and used as backplates/ground/reflection textures.
- **Kerala v5.2:** `output/Kerala_Coconut_Sunrise_GodRays_1080p30_5s.mp4` remains a completed, presented historical deliverable; it is unrelated to the Five Worlds v3 request.

## Historical Kerala v5.2 sunrise god-rays animation

- `output/Kerala_Coconut_Sunrise_GodRays_1080p30_5s.mp4` — 5 s, 1920×1080, 30 fps, 150 native frames; one sun rises from behind the Ghats with physically shadow-shaped crepuscular rays.
- `docs/KERALA_ANIMATION_V52_RECEIPT.json` / `docs/KERALA_ANIMATION_V52_VALIDATION.json` — encode, ffprobe, SHA-256 and lighting-audit proof.
- `docs/KERALA_V52_SUNRISE_GODRAYS.md` — look-dev brief and A/B causality results.
- `scripts/proof_kerala_v52.py` — `normal` / `no_mist` / `no_sun` / `no_clouds` visual proofs.
- `scripts/verify_kerala_animation_v52.py` — independent delivery checks.

Rebuild/verify locally:

```bash
sh scripts/blender-py scripts/proof_kerala_v52.py --mode normal --frame 75 --width 800 --height 450 --samples 40 --out review/v5_fix/sunrise_f075.png
sh scripts/blender-py scripts/render_kerala_animation.py --start 1 --end 1 --out frames --samples 40 --width 1920 --height 1080
python scripts/verify_kerala_animation_v52.py
```

The full 150-frame render is produced by `.github/workflows/render-kerala-animation.yml`. Prior v5 and v5.1 MP4s are preserved.

An actual editable Blender landscape inspired by two user-supplied paddy-field references: flooded rice rows, a curved earthen bund, coconut palms and tropical tree belt, layered Western-Ghat-inspired mountains, and an old Kerala tharavad-inspired house at the path end.

## Historical Kerala quality-first deliverables

- `output/Kerala_Quality.blend` — editable packed Blender 4.2 quality scene (metric, named collections, live GN/collection instances, packed PBR).
- `output/Kerala_Quality_900p.png` — 1600×900 Cycles CPU hero still from the frozen v3 scene.
- `output/Kerala_Quality_House_Detail_540p.png` — Cycles house detail from the same frozen v3 scene.
- `*.receipt.json` — scene/image SHA-256, engine, settings and measured render time.
- `docs/KERALA_VALIDATION_V3.json`, `docs/KERALA_QA_V3.md`, `docs/ADDON_LIBRARY_REPORT_V3.md`, `docs/QUALITY_ASSET_PROVENANCE_V3.json`, `docs/SKILL_94_REVIEW.md` — verification, QA, generator/library tests, provenance and all-94-skill review.

Rebuild/render v3:

```bash
PYTHONPATH=vendor/sources/infinigen/infinigen-main/src sh scripts/blender-py scripts/build_botanical_library.py
sh scripts/blender-py scripts/build_kerala_quality.py
sh scripts/blender-py scripts/render_kerala_quality.py --camera CAM_Q_Hero_LeadingBund --width 1600 --height 900 --samples 64 --out output/Kerala_Quality_900p.png
sh scripts/blender-py scripts/render_kerala_quality.py --camera CAM_Q_House_Detail --width 960 --height 540 --samples 32 --out output/Kerala_Quality_House_Detail_540p.png
sh scripts/blender-py scripts/verify_kerala_v3.py
```

v2 deliverables remain frozen below for comparison.

## Primary deliverables

- `output/Kerala_Monsoon_Light.blend` — editable packed Blender 4.2 scene, metric units, named collections, procedural node materials, non-realized vegetation instances.
- `output/Kerala_Monsoon_Light_1080p.png` — 1920×1080 Cycles CPU hero still rendered from the frozen scene.
- `output/Kerala_Monsoon_Light_1080p.receipt.json` — scene/image SHA-256, engine, settings and measured render time.
- `output/Kerala_House_Detail_540p.png` — Cycles house detail from the same frozen scene.
- `output/Kerala_Fast_Eevee_LOD_540p.png` — fast Eevee preview with reduced instance density, no mist volume and no ray tracing; explicitly not the hero.
- `output/Kerala_House_Compat.glb` / `Kerala_House_CollisionProxy.glb` — generic export/collision compatibility proof; no game-engine import claimed.
- `docs/KERALA_VALIDATION.json` — independent delivery checks.
- `docs/KERALA_QA.md` — ship-with-notes verdict and visual limitations.
- `docs/RENDER_SPEED_REPORT.md` — measured render routes, failures and unavailable backends.
- `docs/SKILL_94_REVIEW.md` — how all 94 specialist documents were reviewed/applied/checked.

## Rebuild and render

```bash
sh scripts/setup_sandbox.sh                     # rebuild venv + vendored OS libs if sandbox reset
sh scripts/blender-py scripts/build_kerala_scene.py
sh scripts/blender-py scripts/render_kerala.py cycles_final --samples 64 \
  --out output/Kerala_Monsoon_Light_1080p.png
sh scripts/blender-py scripts/verify_kerala.py
```

Fast checks:

```bash
sh scripts/blender-py scripts/render_kerala.py cycles_preview --out review/preview.png
sh scripts/blender-py scripts/render_kerala.py clay --size 800 450 --out review/clay.png
```

There is no `blender` CLI in this sandbox; Blender is the PyPI `bpy` module. Use `scripts/blender-py`.

## Honest limits

2 vCPU, 3.85 GiB RAM, no GPU. Cycles CPU is the reliable hero path. Full-density Eevee on software OpenGL was OOM-killed; Workbench is practical only as a simplified clay proxy. The visible sky is a procedural shader on a distant dome, not volumetric cloud geometry. References were analyzed only; no reference photo is used as a backplate.


## Kerala photoreal v2 deliverables

`output/Kerala_Photoreal.blend`, `output/Kerala_Photoreal_1080p.png` + receipt, `output/Kerala_Photoreal_House_Detail_540p.png` + receipt. Rebuild: `sh scripts/blender-py scripts/build_kerala_photoreal.py`; verify: `sh scripts/blender-py scripts/verify_kerala_v2.py`. Add-on/library/texture tests: `docs/ADDON_LIBRARY_REPORT.md`; 94-skill recheck: `docs/SKILL_94_REVIEW.md`.
