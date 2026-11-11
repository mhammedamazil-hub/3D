# Five Worlds Blender v2 — user-corrected Blender/Cycles renders

The earlier **Three.js/WebGL screenshot-capture version was not what was requested**. This v2 re-creates all five scenes as actual `.blend` files in **Blender 4.2.23**, then renders them as videos with **Cycles CPU** using the same sharded GitHub Actions pattern as the Kerala animation.

## What changed

- Five editable, packed `.blend` scenes are now the source of truth: `output/FiveWorlds_Blender_01_AlpineLake.blend` … `output/FiveWorlds_Blender_05_RainforestTemple.blend`.
- The five generated photorealistic references are packed into the `.blend` files and used as real scene inputs: emissive matte-painting backplates plus animated, UV-distorted ground/reflection textures.
- Procedural 3D foreground geometry, one physical sun per scene, area lights, particles, camera animation, ripples, aurora, rain and waterfalls are rendered by Blender, not by browser screenshots.
- Render engine: **Cycles CPU**, 4 samples, adaptive sampling, OpenImageDenoise (`RGB_ALBEDO_NORMAL`), AgX Medium High Contrast.
- Output: **1920×1080, 30 fps, 300 frames, exactly 10.000 s per scene**; H.264/yuv420p, `libx264` CRF 18.
- Workflow: `.github/workflows/render-five-worlds-blender.yml` — 15 CI shards, three 100-frame shards per scene, then assembly and commit-back.

This is still reference-driven 2.5D photorealism: photographic backplates provide the distant detail, while Blender geometry and lighting add real foreground depth and motion. It is not a claim of a fully reconstructible real-world 3D environment.

## Scenes

| # | Scene | `.blend` | 10 s MP4 | Blender motion |
|---|---|---|---|---|
| 01 | Alpine Lake | `output/FiveWorlds_Blender_01_AlpineLake.blend` | `output/FiveWorlds_Blender_01_AlpineLake_1080p30_10s.mp4` | mist, rippled lake, pine/rock foreground, golden-hour dolly |
| 02 | Neon Rain Alley | `output/FiveWorlds_Blender_02_NeonRainAlley.blend` | `output/FiveWorlds_Blender_02_NeonRainAlley_1080p30_10s.mp4` | falling rain, flickering neon, wet pavement, tracking move |
| 03 | Sahara Dunes | `output/FiveWorlds_Blender_03_SaharaDunes.blend` | `output/FiveWorlds_Blender_03_SaharaDunes_1080p30_10s.mp4` | wind-blown sand, UV-dune ripples, heat shimmer, lateral drift |
| 04 | Iceland Aurora | `output/FiveWorlds_Blender_04_IcelandAurora.blend` | `output/FiveWorlds_Blender_04_IcelandAurora_1080p30_10s.mp4` | animated aurora, stars, surf foam, basalt columns, tilt up |
| 05 | Rainforest Temple | `output/FiveWorlds_Blender_05_RainforestTemple.blend` | `output/FiveWorlds_Blender_05_RainforestTemple_1080p30_10s.mp4` | waterfall, floating dust, temple stones, slow dolly |

`output/FiveWorlds_Blender_AllScenes_1080p30_50s.mp4` joins all five back-to-back. `assets/references/v6/00_five_worlds_blender_contact.jpg` is a contact sheet extracted from the finished Blender MP4s.

## Proof and verification

- `docs/FIVE_WORLDS_BLENDER_MANIFEST.json` — Blender version, packed `.blend` SHA-256s, reference SHA-256s and render settings.
- `docs/FIVE_WORLDS_BLENDER_RECEIPT.json` — route, CI run ID, per-MP4 bytes/SHA-256, codec/duration/frame probes, full-decode metrics and combined montage proof.
- `docs/FIVE_WORLDS_BLENDER_VALIDATION.json` — CI frame-shard, lighting-audit and full-decode checks.
- `scripts/verify_five_worlds_blender.py` — independent local re-verification after pulling the CI commit-back.

Each shard receipt records a lighting audit with **one SUN light, zero SPOT lights** and a full SHA-256 of every rendered frame. The final verifier fully decodes all 300 frames of each MP4 and all 1,500 frames of the montage.

## Reproduce

```bash
sh scripts/setup_sandbox.sh
sh scripts/blender-py scripts/build_five_worlds_blender.py \
  --out output --manifest docs/FIVE_WORLDS_BLENDER_MANIFEST.json \
  --width 1920 --height 1080 --samples 4 --fps 30 --frames 300
sh scripts/blender-py scripts/render_five_worlds_blender.py \
  --scene 1 --start 1 --end 300 --out frames --width 1920 --height 1080 --samples 4
python scripts/finalize_five_worlds_blender.py --skip-encode
python scripts/verify_five_worlds_blender.py
```

For the full five-scene delivery, push changes matching the workflow path filters; the 15-shard CI run renders and commits the MP4s, receipt, validation and contact sheet back to the branch.

## Honest limits

Cycles CPU is used because this sandbox and the CI runners have no GPU. Four samples with denoising is a speed/quality compromise for 1,500 frames at 1080p. No audio was requested and none is included. The earlier WebGL MP4s remain in `output/` for comparison but are **superseded** by these Blender renders.
