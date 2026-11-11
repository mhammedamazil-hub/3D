# OPTIMIZATION CATALOG — PROJECT VOXELCORE

Living list. Every entry: purpose, cost, complexity, hardware dependence, status. Measured = benchmark exists; estimated = reasoning, not measurement. Never delete an entry — mark it REJECTED with reason.

## E1. Paletted storage with uniform-section 0-bit fast path — **IMPLEMENTED**
- Purpose: memory + cache. 4096-cell section: uniform = ~48 B; 4-bit palette = ~2 KB.
- Cost: O(1) get, O(palette) set; measured 6.5 µs set-fill of 4096 cells.
- Complexity: medium. HW: universal. Risk: low.

## E2. Greedy meshing with (block, AO-signature) merge — **IMPLEMENTED, MEASURED**
- Purpose: cut quads/indices/overdraw.
- Measured: flat platform 704→6 quads; terrain chunk 2,496 naive faces → 138 quads (5.5%); 9-chunk world 11,636→1,296 (11.1%). faceArea invariant checked by tests.
- Cost: mask scan + rectangle merge, ~2.0 ms/chunk (world-reader path). Complexity: medium. Risk: correctness — guarded by invariant tests.

## E3. Frustum AABB culling — **IMPLEMENTED**
- Purpose: reject unseen chunk meshes before GPU submission. Cost: 6 planes × AABB. Measured: validated by tests (identity box degenerate case avoided with real projection). Risk: low.

## E4. Template-functor block reader (no std::function in hot path) — **IMPLEMENTED**
- Purpose: remove indirect call + closure overhead in faceCell. Gain: small (~10% of mesh time); kept because free.

## E5. Thread-local last-chunk cache for block reader — **BACKLOGGED (next)**
- Purpose: replace per-cell hash lookups with one cached pointer per worker.
- Hypothesis: mesh time dominated by unordered_map lookups (~2 ms/chunk). Expected: 2–5× mesh speedup.
- Risk: stale pointer if chunk map rehashes → guard by map generation counter. Measure before adopting.

## E6. Side-bucket ordering (7 buckets, opaque/cutout split) — **DONE (2026-11-11)**
- Implemented: mesh output stably 7-way partitioned into buckets (+X=0, +Z=1, other=2 reserved, +Y=3, −Z=4, −X=5, −Y=6) with `bucketEnd[8]` exclusive-offset table in `Result`; single-cursor scatter (O(n), one temp vector) instead of `std::stable_sort` after measurement showed +7.5% → +0.8%.
- Tests: non-decreasing bucket order; `bucketEnd` boundaries match the sorted layout exactly; suite green (193,870 checks).
- Cost measured: 1.359 → 1.370 ms/chunk greedy mesh (<1%). Coplanar insertion order preserved per bucket.
- Cutout/opaque split deferred to draw time (software renderer two passes; Vulkan single pass with alpha blend) — revisit with packed records (E7).

## E7. Packed quad records + vertex pulling — **M1+M2 IMPLEMENTED (2026-11-11, `docs/design/E7_PACKED_RECORDS.md`)**
- Horizon's 24-byte record redesigned to an 8-byte chunk-local record (`x4 z4 y6 u4 v4 dir3 | block16 ao8 light4`);
  plane positions stored as slice indices (boundary planes fit in 6 bits) after M1's layout rework. CPU codec +
  exhaustive tests (3,456 cases + 20k fuzz) + Vulkan vertex-pulled pipeline (`records.vert`, storage buffer per
  draw, origin in push constants) + `tools/records_parity.cpp` byte-identical-PPM CI gate (`Packed-records parity
  gate (E7)` in the vulkan-headless job). dlopen loader extended with descriptor/draw symbols.
- CPU-float32-vs-GLSL shading verified bit-identical on the full (ao × light × sun × colors) domain.
- Upload bytes: 28 B/vert × 4 + 4 B × 6 indices ≈ 136 B/quad → 8 B/quad (≈17× fewer bytes at equal quad count;
  bench row for unpacked vs records path still pending). Unpacked path remains default; M3 (bench + arena-backed
  record buffers) open. Runtime parity verdict pending the GLSL→SPIR-V CI run for the records pipeline commit.

## E8. Cave culling (flood fill from opaque boundary) — **STAGE 7**
- Purpose: discard never-visible interior sections. Horizon: big win at high RD. Cost: one BFS per world load + incremental on block change. Risk: correctness (needs conservative boundary rules).

## E9. Entity/particle culling (sync + async with position-quantized cache) — **STAGE 7**
- Mirror Horizon's approach; async variant only after sync variant is verified.

## E10. GPU culling + two-phase occlusion (`drawIndirectCount`) — **STAGE 7+, OPT-IN**
- Capability gates: Vulkan + indirect-count + compute; excluded: Intel Gen11/12, software rasterizers, non-Vulkan fallbacks. Off by default (Horizon does the same). Auto-mode later (stage 13).

## E11. Heightfield LOD tiles + grid mesh — **IMPLEMENTED v1 (STAGE 8 polish)**
- Purpose: render 100+ chunk distances without simulating/meshing voxels.
- Implemented: bake (0.8 ms/tile), triangulated grid, LOD mesh emission. Missing: crack prevention (skirts), material layers per cell, screen-error refinement, seamless transition ring, cache on disk.

## E12. Budgeted chunk upload queue (N sections/frame) — **STAGE 6**
- Purpose: eliminate frame spikes at stream-in. Implemented as design; not yet coded.

## E13. Fixed-grid frame pacing — **STAGE 13** (Horizon "Efficient" mode).

## E14. Vulkan async shader compile + pipeline cache blob — **STAGE 10/13**.

## E15. Virtual shadow maps (clipmap + page invalidation) — **RESEARCH** — potentially decisive for RD≥32 with real sun shadows. Decision after stage 9.

## E16. Thread oversubscription guard — **IMPLEMENTED** (workers = hw−1 default; no spin).

## E17. Chunk heightmap short-circuit for buried cells in mesher — **DESIGNED** (skip full column scans); stage 6.

## E18. SIMD AO/mesh scan (AVX2) — **MEASURE FIRST** at stage 13.

## E19. Texture streaming + mip bias by distance — **STAGE 13**.

## E20. Deterministic replay benchmarks (flyover camera path) — **STAGE 13** (mirrors `tools/perf_bench.py`; our numbers must come from a committed script, not hand-waving).

## Reversal log
- 2026-11-11: software-raster color interpolation uses affine weighting — acceptable for verification, rejected for shipping quality (marked as such in `software_renderer.hpp`).

## Light propagation (Stage 9 M1) — **DONE (2026-11-11)**
- Column sky seeding + BFS boundary-relaxation flood fill; opacity precomputed per cell (1 byte); initial queue contains only lit/unlit boundary cells (O(boundary), not O(region)); no world lookups inside the flood loop.
- `light_volume_16x64x16_flat`: 1,110 → ~250–430 µs per compute (4-5×). Correctness: sealed caves fully dark; exact Manhattan falloff from seeds; occluded block sources emit nothing; above-region reads as open sky.
