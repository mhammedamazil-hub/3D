# Kerala v5 — god-rays animation brief

Requested: use the uploaded coconut scene, improve god rays / shadows / lighting / textures, and deliver a 5-second 30 fps 1080p render through a GitHub workflow.

## Scene upgrade (`scripts/kerala_v5.py`)
- Applied on top of frozen v4 `output/Kerala_Coconut_Realism.blend`; uploaded coconut instances retained.
- Lighting: post-rain sun break. Warm low sun (energy 6, ~0.8° angle) from behind/side for longer defined shadows; reduced world/fill so shafts read against darker humid air.
- God rays: true 3D volume work — forward-scattering humid medium, shadow-only cloud gobo, and three art-directed scattering/emission shaft volumes with radial falloff. No 2D ray overlay.
- Textures: AO-driven crevice grime on roof/tile/plaster/wood/mud, added micro-bump, wet-mud roughness variation, sharper paddy-water ripple normals.
- Camera: 150-frame eased dolly along the bund toward the house, 30 fps, 1920×1080.

## GitHub workflow
`.github/workflows/render-kerala-animation.yml` renders 15 shards × 10 frames on `ubuntu-latest` with `bpy==4.2.23` Cycles CPU (16 max samples, adaptive .05, OIDN), uploads frame artifacts, verifies all 150 frames, encodes H.264 MP4 with ffmpeg, validates 1920×1080/30 fps/150 frames/5 s via ffprobe, and pushes:
- `output/Kerala_Coconut_Realism_GodRays_1080p30_5s.mp4`
- `docs/KERALA_ANIMATION_V5_RECEIPT.json`

The derived v5 blend is rebuilt on each runner from the tracked v4 blend to avoid committing another ~80 MB scene. Local preview stills are in `review/v5/` (ignored).

## Completed render
GitHub Actions run `42556110997` completed successfully on branch `arena/cd56b6ae-3d` (commit `4cac87c`). All 15 frame shards rendered, assembled, and ffprobe-verified: 1920×1080, 30/1 fps, 150 frames, 5.000000 s. Local validation: `docs/KERALA_ANIMATION_V5_VALIDATION.json` PASS.
