# Kerala v5.2 — sunrise from the Ghats with physical god rays

The v5.1 FIXED animation was rejected: the sun did not read as rising from the
mountains and the shafts were not convincing. v5.2 is a fresh look-dev pass,
not a compositor overlay.

## What is actually in the scene

- **One animated SUN lamp**, `LGT_V52_RisingSun`, at azimuth 20°. Its apparent
  elevation is keyframed 5.0° → 7.0° → 9.5° at frames 1 / 75 / 150, so the
  disc starts behind the ridge, clears it mid-shot, and is above it at the end.
  Energy and colour warm up over the same keys. No spotlights, no emissive
  beam cones, no second sun.
- A procedural **dawn-gradient world** with a small additive sun disc. The disc
  direction is keyframed with the lamp, fixing the earlier stuck-disc bug.
  Camera background and lighting background are separated with `Is Camera Ray`.
- **One non-emissive mist volume**, `SM_V52_Sunrise_MistDomain`, with a
  height-faded density and forward-scattering anisotropy. Its density ramps
  from zero at pre-dawn to 0.0022 by frame 60 to avoid low-sample fireflies in
  the dark sky.
- A **world-space, shadow-only cloud deck**, `SM_V52_CloudDeck`. Geometry
  Position drives low-frequency warped sine lanes; the deck is invisible to
  camera/diffuse/glossy/transmission rays and blocks only shadow rays. Object
  coordinates on a plane scaled hundreds of metres were nearly constant — the
  earlier v5.1 aperture used that dead end and produced no readable shafts.
- The uploaded coconut GLB, Kerala paddy/path/house, and the 150-frame dolly
  are retained. The floating roof-vent grid and the snow-like specular horizon
  patches remain fixed.

## Causality, not painted beams

`scripts/proof_kerala_v52.py` rendered A/B proofs at frame 75:

| Mode | Result |
| --- | --- |
| `normal` | bright sun glow, diagonal cloud shadows and distinct shafts |
| `no_mist` | crisp sun disc and dark scene; no volumetric shafts |
| `no_sun` | near-black scene; the world disc remains but nothing is lit |
| `no_clouds` | bright uniform haze; no distinct shadow-shaped shafts |

Local 800×450 / 40-sample proofs are in `review/v5_fix/sr_final4_*` (review
images are gitignored). All proof runs passed the lighting audit.

## Render and QA

- 1920×1080, 30 fps, 150 native frames, 5.000 s.
- CPU Cycles, 40 samples max, OpenImageDenoise. Frames 1–60 use
  `RGB_ALBEDO_NORMAL` denoising for clean pre-dawn skies; frames 61–150 use
  `RGB_ALBEDO` so the volumetric shaft detail is not smoothed away.
- `.github/workflows/render-kerala-animation.yml` renders 15 shards of 10
  frames, verifies every shard's single-sun audit, encodes with libx264 CRF 17,
  ffprobes the result, runs `scripts/verify_kerala_animation_v52.py`, and pushes
  the MP4 + receipt + validation back to the branch.
- Deliverable: `output/Kerala_Coconut_Sunrise_GodRays_1080p30_5s.mp4`.
  Receipt: `docs/KERALA_ANIMATION_V52_RECEIPT.json`.
  Validation: `docs/KERALA_ANIMATION_V52_VALIDATION.json`.
- Prior v5 and v5.1 MP4s and receipts remain in place for comparison.
