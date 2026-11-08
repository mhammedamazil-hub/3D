# QA verdict — Monsoon Light, Kerala

**Result: SHIP WITH NOTES**

- **TECHNICAL: PASS** — `docs/KERALA_VALIDATION.json`; frozen scene SHA-256 matches the hero receipt; 1920×1080 PNG decodes; water IOR 1.333; required collections present; no missing external images.
- **VISUAL: agent-reviewed, user approval pending** — hero, house crop/detail, foreground crop, clay proxy and Eevee LOD preview inspected.
- **DELIVERY: final verified** for the Cycles hero still and editable `.blend`.

## What was visually checked
- Path leads from foreground to the house; house is readable at the end.
- Roof tiles, veranda posts/brackets, door, windows, laterite plinth and steps read in the detail render.
- Flooded rows and reflective water are visible between rice clumps.
- Mountains sit behind the tree line; sky has blue breaks and procedural clouds.
- No reference photograph is used as a backplate.

## Known limitations / notes
- This is a procedural reconstruction, not a photograph-indistinguishable scan. Mountains are smoother and more stylized than real Western Ghats rock/forest detail.
- Visible sky/clouds are a procedural dome shader, not volumetric cloud geometry.
- Rice blades are broader and cleaner than field-grown plants; no crop disease, lodging or mud splash variation.
- Full-density Eevee was OOM-killed on this 3.85 GiB GPU-less sandbox. The delivered Eevee image is an explicit reduced-density/no-volume/no-ray-tracing preview, not the hero.
- House GLB compatibility export/reimport passed, but the Blender process segfaulted during shutdown after writing the report; no game-engine import was claimed.
- No animation was requested or delivered.
