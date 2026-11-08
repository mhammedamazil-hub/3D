# Kerala photoreal v2 — QA notes

Status: FINAL VERIFIED — technical PASS, final hero and house detail visually inspected.

## Reference-driven changes from v1

- Vegetation: replaced repeated broad-leaf crowns with a CC0 Poly Haven island_tree_02 LOD1 library asset, six Improved Sapling generated broadleaf variants, scanned fern/anthurium understory, and denser foothill forest. Rice clumps are finer (12 blades, ~1 cm wide) and denser (133,805 points) with seeded skips.
- Ground/path: wet scanned mud, real shallow footprint depressions, puddles, laterite edge stones, narrow side drain and a timber plank crossing.
- House: retained Kerala tharavad destination; warmer lime wash, darker teak, weathered clay relief, darker granite, corrugated metal vent cladding/ribs, laterite chips and damp skirts.
- Mountains/light: slope-aware forest/rock PBR, editable Displace crags, separated low-density mist banks, desaturated CC0 HDRI overcast mix, soft sun.

## Visual inspection

- Preview 1: rejected — neon rice, dry gray path, stone-like plaster, sparse lollipop foothill trees, harsh blue sky.
- Preview 2: improved materials but foothill forest still sparse; rejected as final.
- Preview 3: accepted for composition/material direction; frozen and sent to 1080p/64 Cycles CPU.
- House preview 2: accepted — lime/teak/clay/metal read correctly at 640×360.
- Final hero 1920×1080: inspected; finer rice, wet bund, timber crossing, layered forest/rock Ghats and house destination read clearly. Receipt hashes match frozen scene.
- Final house detail 960×540: inspected; overlapping clay tiles, metal vent, lime/teak/laterite and damp skirts read correctly.
- Eevee fast LOD 480p: OOM-killed (~3.87 GiB RSS), recorded as unavailable for v2.
- Workbench clay proxy 960×540: PASS in 45.609 s, composition proxy only.

## Honest limits

Native Blender/Cycles CPU scene, no photo backplate. CPU-only sandbox; no GPU/Storm/LuxCore/BlenderKit render claimed. Full-density Eevee previously OOMed; v2 fast Eevee route is a disclosed LOD probe. The image is a substantial realism revision, not a guarantee of photo-indistinguishability. Remaining CG tells: procedural coconut/banana silhouettes, repeated canopy instances, and simplified ridge crests. Reopened scene retains 30 materials after unused datablocks purge (46 at build).
