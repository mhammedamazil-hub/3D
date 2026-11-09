# Kerala v5.1 bug fix — “three suns” and floating black grid

User report: the v5.0 animation appeared to show three suns / searchlight cones, lacked convincing god rays, and had a black grid artifact overhead.

## Root causes found
1. **Three actual spotlights + emissive cone volumes.** `scripts/kerala_v5.py` v5.0 created `LGT_V5_GodRay_Shaft_0..2` and `SM_V5_Light_Shaft_*` cones with volume emission. These read as separate suns/searchlights, not natural crepuscular rays.
2. **Floating roof-vent parts.** `SM_Vent_Cap_StandingSeam_*` and `SM_Vent_Metal_Rib_*` were unparented at the origin instead of under `SM_Tharavad_House_Root`. In the opening camera frame they appeared as a black grid overhead.

## Fix
- Removed all shaft spotlights and emissive beam cones.
- Exactly one directional sun (`LGT_V51_SingleSun`) illuminates a non-emissive, height-faded mist volume.
- A shadow-only cloud aperture and scene geometry occlude that same sun; volume bounces = 0 for crisp single scattering.
- Parented stray roof-vent ribs/caps to the house root.
- Relocated near coconut crowns / adjusted camera headroom; hid old hard mist banks that caused horizon fog walls.
- Added structural audits: one sun, zero spots, zero fake shaft objects, zero emissive volumes, zero unparented vent parts.

## Verification
- Local proof frames: opening frame no longer contains the floating vent grid; midpoint shows diagonal single-sun shafts; A/B with mist removed removes the shafts.
- CI workflow re-renders all 150 native frames at 1920×1080/30 fps and writes `docs/KERALA_ANIMATION_V51_RECEIPT.json` + validation.
- Corrected deliverable: `output/Kerala_Coconut_Realism_GodRays_FIXED_1080p30_5s.mp4`.

The rejected v5.0 file is retained for comparison but is not the corrected deliverable.
