# Kerala quality-first v3 — QA notes

Status: FINAL VERIFIED — technical PASS, final hero and house detail visually inspected.

## Reference-driven changes from v2

- Rice: replaced lawn-like dense fine grass with transplanted row clumps (10–11 arching blades, ~8 mm wide, 0.48–0.82 m tall) over visible shallow water; 79,917 seeded row points with skips.
- Path/bunds: thinner irregular earthen bunds and wet muddy path, dark brown albedo, puddles, timber drain crossing; removed floating laterite brick edge stones.
- Vegetation: Infinigen BSD-3 banana monocots (broadleaf tree generated/retained in library but not scattered after leaf-visibility issue); detailed native coconut palms with pinnate leaflets; Poly Haven CC0 jacaranda/tree_small/island_tree scanned trees; mixed forest belt instead of repeated sapling lollipops.
- House: retained old Kerala tharavad at path end; upgraded 2K/4K scanned clay/laterite/wood/plaster/metal PBR, potted plants, damp skirts and metal vent.
- Mountains/light: pushed ridges farther, desaturated forest/rock shaders, stronger noise-driven mist banks, overcast pure-sky HDRI and softer sun.

## Visual inspection

- v2 crops confirmed lawn-like rice, concrete-looking bunds, geometric bananas, repeated/wrong-scale background trees and simplified ridge.
- Infinigen probes: banana monocot usable after droop/tear/material tuning; broadleaf safe live tree usable; dense realized tree crashed (mesh allocation), coconut GN OOMed during sync, aggressive leaf decimation collapsed foliage. These routes were rejected.
- v3 preview 1: rejected — faceted close mountains, bare decimated forest, sticky rice, gray path.
- v3 preview 2: improved rice/forest/mist; path still too light; rejected as final.
- v3 preview 3: darker mud/lighting; first final revealed gray specular path and bare live-GN broadleaf instances.
- v3 preview 4: reduced mud specular, replaced bare Infinigen scene instances with scanned trees, removed brick-like path stones; accepted for final re-render.
- Final hero 1600×900/64: inspected; brown wet path, row rice over water, timber crossing, house destination, mixed scanned canopy and mist-layered Ghats read clearly. Receipt hashes match frozen scene. Rendered in 429.287 s.
- Final house detail 960×540/32: inspected; overlapping clay tiles, metal vent, lime/teak/laterite, potted plants and damp skirts read correctly. Rendered in 83.055 s.

## Honest limits

Native Blender/Cycles CPU scene, no photo backplate. CPU-only sandbox; no GPU/Storm/LuxCore/BlenderKit render claimed. Infinigen coconut and dense realized tree were not used after memory failures. Scanned trees are instanced; some canopy repetition remains. The image is a quality-first CG revision, not a guarantee of photo-indistinguishability.
