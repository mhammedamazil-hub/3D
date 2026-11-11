> **Superseded:** the WebGL screenshot-capture route below was rejected by the user. Use `docs/FIVE_WORLDS_BLENDER_V2.md` and the Blender/Cycles renders instead.

# Five Worlds v1 — five different 10-second scenes

This delivery is **not** the prior Kerala/coconut/paddy/house sunrise scene. It is a new set of five assistant-invented worlds. References were generated first, then loaded as actual scene inputs.

## Route decision: fastest available method

| Route | Decision |
|---|---|
| GitHub Actions workflow | Rejected. The previous 15-shard CPU render took roughly 78 minutes; a CI queue also adds latency. |
| Blender/Cycles in this sandbox | Rejected. The Blender Python environment was absent after the workspace refresh; rebuilding and CPU-only path tracing would be slower. |
| **Three.js/WebGL + browser screenshot capture + local ffmpeg** | **Selected.** Two local headless-Chromium workers captured 1,500 deterministic 1280×720 WebGL frames, then local `libx264` encoded them. Measured wall clock: **162.96 s capture**, **180.97 s total**. |

The browser route was available immediately through npm. `@sparticuz/chromium` supplied the headless binary and its AL2023/SwiftShader libraries; `puppeteer-core` took deterministic JPEG screenshots; `@ffmpeg-installer/ffmpeg` encoded H.264. No GPU was required.

## Generated references and how they are used

Five photorealistic plates were generated first at 1376×768, then cropped/resized to 1280×720 16:9 derivatives in `assets/references/v6/`:

1. `01_alpine_lake.jpg` — mirror alpine lake at golden hour.
2. `02_neon_rain_alley.jpg` — wet neon alley after rain.
3. `03_sahara_dunes.jpg` — sunrise dunes with a distant caravan.
4. `04_iceland_aurora.jpg` — black-sand beach, aurora and basalt cliff.
5. `05_rainforest_temple.jpg` — mossy temple, waterfall and sunlit jungle.

`assets/references/v6/00_reference_contact.jpg` is the generated-reference contact sheet. `assets/references/v6/00_five_worlds_video_contact.jpg` is a later contact sheet extracted from the finished MP4s.

In `web/scene.js`, each 16:9 derivative is loaded as:

- the **actual backplate texture** on a large Three.js plane, with a subtle scene-specific UV shimmer;
- a second **rippled reflection-plane texture** used for water, wet pavement, heat haze, beach sheen or forest-floor haze;
- the art direction for each scene's lighting palette, camera move, particles and foreground depth.

This is reference-driven 2.5D photorealism, not a claim of a full reconstructible 3D world. The generated photographic plates provide the realism; WebGL adds deterministic motion, weather, reflections, particles, aurora animation, focus-like camera moves, grain and vignette.

## Five scenes

| # | Scene | MP4 | Motion |
|---|---|---|---|
| 01 | Alpine Lake | `output/FiveWorlds_01_AlpineLake_720p30_10s.mp4` | drifting mist, rippled reflection, warm sun bloom, slow dolly |
| 02 | Neon Rain Alley | `output/FiveWorlds_02_NeonRainAlley_720p30_10s.mp4` | falling rain, wet neon reflections, steam, flickering signs, tracking move |
| 03 | Sahara Dunes | `output/FiveWorlds_03_SaharaDunes_720p30_10s.mp4` | heat shimmer, wind-blown sand, warm dune ripples, lateral drift |
| 04 | Iceland Aurora | `output/FiveWorlds_04_IcelandAurora_720p30_10s.mp4` | animated aurora curtain, stars, surf foam, soft basalt-cliff foreground shade, tilt up |
| 05 | Rainforest Temple | `output/FiveWorlds_05_RainforestTemple_720p30_10s.mp4` | floating dust, canopy shade, warm haze, slow dolly into temple |

`output/FiveWorlds_AllScenes_720p30_50s.mp4` concatenates all five without re-encoding.

## Technical specification

- 1280×720, H.264 High profile, `yuv420p`, 30 fps.
- Exactly 300 frames and 10.000 s per scene; 1,500 frames and 50.000 s in the montage.
- Deterministic time: `window.setTime(t)` renders the frame and calls `renderer.getContext().finish()` before Puppeteer captures it.
- `libx264`, preset `veryfast`, CRF 19, `-movflags +faststart`.
- Two capture workers: scenes 1–3 and 4–5.
- `web/node_modules/` and `web/frames/` are ignored; final MP4s, references, code, docs and receipts are tracked.

## Verification

`docs/FIVE_WORLDS_RECEIPT.json` records the route, toolchain, reference SHA-256s, per-video byte sizes and SHA-256s, and the measured timing. `scripts/verify_five_worlds.py` independently checks:

- all five generated references are referenced by `web/scene.js` and their SHA-256s match;
- each MP4's receipt bytes/SHA-256, H.264/yuv420p, 1280×720, 30 fps and 10.000 s duration;
- a full low-resolution decode of all 300 frames per scene: return code 0, no decoder errors, exactly 300 frames, 300 distinct frames, no black/white frames, and frame-to-frame motion;
- the 50-second montage: full decode of 1,500 frames, exact duration, resolution and codec;
- the final video contact sheet exists.

`docs/FIVE_WORLDS_VALIDATION.json` contains the passing result. All five scenes passed 22/22 checks and the combined montage passed 11/11 checks.

## Reproduce

```bash
cd web
npm ci
npm run render          # capture 1,500 frames + encode five MP4s + montage + receipt
npm run verify          # run ../scripts/verify_five_worlds.py
npm run preview         # optional five-frame look-dev contact sheet
```

If `web/frames/` is already present and only encoding needs to be repeated, use `node render.cjs --encode-only`.

## Honest limits

The output is 720p rather than 1080p to keep the selected route fastest on 2 vCPU / ~3.8 GiB RAM with no GPU. The scenes are photographic 2.5D compositions with procedural motion, not path-traced 3D geometry. No audio was requested and none is included.
