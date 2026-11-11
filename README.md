# Monsoon Light — Kerala

## Current Five Worlds Blender v2 — user-corrected Blender/Cycles renders

The user rejected the earlier WebGL screenshot-capture route. All five scenes are now **actual Blender `.blend` scenes**, rendered as videos with **Blender Cycles CPU** in a 15-shard GitHub Actions workflow like the Kerala animation.

- `output/FiveWorlds_Blender_01_AlpineLake.blend` … `output/FiveWorlds_Blender_05_RainforestTemple.blend` — five editable, packed Blender scenes using the generated references as real backplates and animated ground textures.
- `output/FiveWorlds_Blender_01_AlpineLake_1080p30_10s.mp4` … `output/FiveWorlds_Blender_05_RainforestTemple_1080p30_10s.mp4` — five Blender-rendered 1920×1080, 30 fps, exactly 10 s videos.
- `output/FiveWorlds_Blender_AllScenes_1080p30_50s.mp4` — all five back-to-back.
- `assets/references/v6/00_five_worlds_blender_contact.jpg` — contact sheet extracted from the Blender MP4s.
- `docs/FIVE_WORLDS_BLENDER_MANIFEST.json`, `docs/FIVE_WORLDS_BLENDER_RECEIPT.json`, `docs/FIVE_WORLDS_BLENDER_VALIDATION.json`, `docs/FIVE_WORLDS_BLENDER_V2.md` — packed-scene manifest, route/render proof, validation and method notes.
- `scripts/build_five_worlds_blender.py`, `scripts/render_five_worlds_blender.py`, `scripts/finalize_five_worlds_blender.py`, `scripts/verify_five_worlds_blender.py` — Blender builder, shard renderer, assembler and independent verifier.
- `.github/workflows/render-five-worlds-blender.yml` — 15-shard Cycles CPU render and commit-back.

Reproduce/verify locally:

```bash
sh scripts/setup_sandbox.sh
sh scripts/blender-py scripts/build_five_worlds_blender.py --out output --manifest docs/FIVE_WORLDS_BLENDER_MANIFEST.json
python scripts/verify_five_worlds_blender.py
```

## Earlier Five Worlds v1 WebGL prototype — superseded

Five assistant-invented, reference-driven worlds replace the Kerala/coconut/paddy/house scene. Each is a photorealistic 1280×720, 30 fps, 300-frame H.264 render lasting exactly 10 seconds; the 50-second montage joins all five.

- `output/FiveWorlds_01_AlpineLake_720p30_10s.mp4` — mirror alpine lake, drifting mist, rippled reflection, golden-hour dolly.
- `output/FiveWorlds_02_NeonRainAlley_720p30_10s.mp4` — wet neon alley, falling rain, steam, flickering signs, tracking move.
- `output/FiveWorlds_03_SaharaDunes_720p30_10s.mp4` — sunrise dunes, heat shimmer, wind-blown sand, lateral drift.
- `output/FiveWorlds_04_IcelandAurora_720p30_10s.mp4` — black-sand beach, animated aurora, stars, surf, tilt up.
- `output/FiveWorlds_05_RainforestTemple_720p30_10s.mp4` — mossy temple, floating dust, canopy shade, slow dolly.
- `output/FiveWorlds_AllScenes_720p30_50s.mp4` — all five scenes back-to-back.
- `assets/references/v6/` — five generated reference plates, 16:9 derivatives, reference contact sheet, and final video contact sheet.
- `docs/FIVE_WORLDS_RECEIPT.json` / `docs/FIVE_WORLDS_VALIDATION.json` — route decision, SHA-256, codec/duration/frame and full-decode proof.
- `docs/FIVE_WORLDS_V1.md` — method, scene list and reproduction steps.

Fastest route selected: in-sandbox Three.js/WebGL, Puppeteer screenshot capture, and local ffmpeg. The generated references are loaded as actual backplate and rippled-reflection textures, not kept as documentation only. Reproduce with:

```bash
cd web
npm ci
npm run render
npm run verify
```

## Current v5.2 sunrise god-rays animation

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

## Quality-first v3 deliverables

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
