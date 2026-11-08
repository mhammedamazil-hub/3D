# Monsoon Light — Kerala

An actual editable Blender landscape inspired by two user-supplied paddy-field references: flooded rice rows, a curved earthen bund, coconut palms and tropical tree belt, layered Western-Ghat-inspired mountains, and an old Kerala tharavad-inspired house at the path end.

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
