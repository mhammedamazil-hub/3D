# Monsoon Light — Kerala

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
