# PROJECT VOXELCORE — DEVELOPMENT STATUS

**Date:** 2026-11-11 · **Branch:** `arena/3e3c4ae6-3d` · **Owner:** lead engineering agent

> Status after the Vulkan/Stage-5-translucency batch (commit `92f2882` and later):
> - **Cave culling** (E8) landed & tested: sealed-air flood fill from the world AABB; sealed components (caves) get ids ≥1; mesher faces adjacent to a sealed component render only when the camera is inside it. Test: 8×8×4 sealed cavity → exactly 256 cavity-wall faces culled for outside camera, all kept inside; conservation law holds.
> - **Side-bucket ordering** (E6) landed & tested: mesh output is stably partitioned into Horizon-compatible buckets (+X,+Z,other,+Y,−Z,−X,−Y); `bucketEnd[8]` offsets recorded; cost ≈ +0.8% mesh time (1.359→1.370 ms/chunk). Cutout/opaque split happens at draw time for now.
> - **Correct translucency**: water palette color carries alpha (0x9F…); software renderer draws two passes — opaque+cutout (z-write, backface-culled), then water sorted far→near with alpha blending, depth-tested against pass-1 depth, no depth writes (round-to-nearest composite). Vulkan pipeline has blend enabled (SRC_ALPHA / ONE_MINUS_SRC_ALPHA). Vulkan path has no distance sort yet (documented).
> - **Vulkan headless renderer** landed (`engine/rendering/vulkan/vulkan_headless.hpp` + `tools/vulkan_render.cpp`): instance/device/render-pass/RGBA8+D32 pipeline, push constants (MVP), index draw, PPM readback. **Compile-checked locally** (no Vulkan loader in this sandbox); shader compilation verified locally via glslang built from pinned source (`vulkan-sdk-1.4.313.0`); **runtime verification pending CI** (new `vulkan-headless` job: `libvulkan-dev`, `mesa-vulkan-drivers` Lavapipe, `glslang-tools`, validates the PPM and asserts non-sky pixels > 1000). Exit code 77 = "no Vulkan device" (clean skip); any other non-zero = failure.

## What was investigated

- **Horizon reference clone** (`github.com/horizon-rust/horizon`, MIT, shallow clone @ `04a26210e31fedf763175dcb05c0b0bdf2fefd21`, 2026-11-05 nightly era) cloned to `/home/user/horizon` (188 MB, 1,760,457 lines of Rust across 3,164 `.rs` files). Audited: workspace layout (49 crates + xtask + launcher), renderer (`horizon-client-render`: gfx, mesher, lod, streaming, pack_* shader-pack stages), world (`horizon-world`: Anvil region storage, PalettedContainer/PackedStorage, Minecraft 26.3 parity), core (`horizon-core`: noise, jmath, density graph, PackedStorage), docs (`architecture.md`, `graphics.md`, `shaders.md`), CI (`.github/workflows/ci.yml`), benchmarks (`benchmarks/perf/*.json`, `docs/benchmark.md`).
- **Horizon build**: not possible in this sandbox — no Rust toolchain, and rustup/static.rust-lang.org is not reachable from here. Baseline numbers therefore cite Horizon's published in-repo benchmark reports (see `docs/HORIZON_PERFORMANCE_BASELINE.md`). Horizon's test suite has not been run locally; this is an explicit gap, not a hidden one.
- Environment: Debian 12, gcc/g++ 12.2 (`-std=c++23` accepted), cmake 4.4.4 + ninja 1.13 (installed via PyPI), Python 3.11, no GPU, no Vulkan SDK, apt unavailable.

## What was implemented (voxelcore, all in `voxelcore/`)

Working, tested C++23 engine foundation:

- `engine/core/types.hpp` — SectionPos/ChunkPos with hashing, section indexing.
- `engine/core/packed_storage.hpp` — bit-packed dense array (1–64 bits/entry, word-straddling writes). 2000-iteration benchmarked.
- `engine/core/paletted_section.hpp` — palette-compressed 4096-cell section; 0-bit uniform sections, on-demand palette growth (bitsFor), trim() re-compaction, hash-mapped palette index.
- `engine/memory/arena.hpp` — linear bump arena (O(1) alloc, O(1) bulk reset).
- `engine/jobs/job_system.hpp` — fixed worker pool, condvar wakeup, `parallelFor` with atomic batch claiming + inline participation (no oversubscription).
- `engine/terrain/noise.hpp` — deterministic permutation-free gradient noise (2D/3D) + fBm (integer hash → identical across platforms).
- `engine/terrain/terrain_gen.hpp` — deterministic terrain: continentalness fBm + detail fBm + ridge; bedrock/stone/dirt/grass/sand/snow; sea level water; hash-seeded trees.
- `engine/world/world.hpp` — sparse chunk container (hash map), cross-chunk get/set.
- `engine/meshing/mesher.hpp` — **greedy mesher**: visible-face elimination (internal solid faces never enter the mask), rectangle-merge by (block, 4-corner AO signature), per-corner Minecraft-style AO baked at mesh time, template-functor block reader (no std::function indirection in hot path), culler hook (NoCaveCuller fast path / CaveCuller), E6 side-bucket partition with `bucketEnd` offsets.
- `engine/visibility/cave_culling.hpp` — sealed-air cave culling (flood fill from AABB boundary; sealed components ≥1; 0 = reachable).
- `engine/rendering/vulkan/vulkan_headless.hpp` — headless Vulkan renderer (offscreen RGBA8+D32, MVP push constants, PPM readback) behind `VOXELCORE_WITH_VULKAN`; CI runs it on Lavapipe.
- `engine/rendering/math.hpp` — look-at / Vulkan-NDC (z[0,1]) perspective matrices.
- `engine/visibility/frustum.hpp` — Gribb–Hartmann frustum AABB culling (normalised planes, positive-vertex test).
- `engine/lod/heightfield_lod.hpp` — Distant-Horizons-style baked heightfield tiles (16×16 cells at 1<<level blocks), smooth LOD grid mesh emission.
- `engine/rendering/software_renderer.hpp` — z-buffered CPU rasterizer (verification path; proves mesh→triangles→pixels without a GPU); two-pass translucency (opaque+cutout, then water far→near with alpha blending).
- `tools/voxelcore-cli` — `gen`, `mesh`, `render`, `lod` commands; rendered `voxelcore/sample_render.png`.
- `tests/test_main.cpp` — 12 test groups (~33k checks): packed storage roundtrip across 8 widths, palette section growth/trim, arena reuse, job system, noise determinism, worldgen determinism, greedy mesher exactness (merged face area == naive visible faces; flat platform merges to 6 quads; buried 9³ cube emits exactly 486 face-area / 6 quads; AO bounds), frustum culling, LOD bake.
- `benchmarks/bench_main.cpp` — CSV micro-benchmarks (see numbers below).
- CMake (C++23) + Ninja; GitHub Actions CI: Linux build+test+bench+headless render, ASan/UBSan job, Android arm64-v8a NDK compile job.

## Measured results (this machine, gcc 12.2 -O3, 2026-11-11)

- Unit tests: **193,870 checks, 0 failures** (includes 60 random-soup mesher fuzz iterations + NBT/region roundtrips + bucket-order checks + translucency blend tests). ASan/UBSan build: 0 failures.
- `terrain_gen_chunk`: ~170 µs/chunk. `greedy_mesh_generated_chunk`: **~1.37 ms/chunk** (cached block reader + O(n) E6 bucket partition; was 2.0–2.3 ms pre-E5, 1.36 ms pre-E6).
- 9-chunk world mesh: 20.1 → **9.8 ms** (E5). Headless software frame: 32 → **21.9 ms** (backface culling).
- 9-chunk world (r=1): gen 1.5 ms, mesh 20.1 ms; 11,636 naive faces → 1,296 quads (**11.1% of naive**), `faceArea == naiveFaces` PASS.
- Flat-platform greedy merge: 704 → **6 quads**. `packed_storage_set_4096`: ~6.5 µs.
- LOD bake level 2 (4 m cells): 0.8 ms; 512-triangle grid mesh.
- **Stage 5 landed**: NBT reader/writer, Anvil `.mca` region I/O (zlib, sector allocation, full rewrite-on-flush), chunk↔NBT roundtrip — generated chunk saves and reloads byte-identically (`voxelcore saveload`).
- **Fuzz**: greedy-merge conservation law (`faceArea == naiveFaces`) holds on 60 random voxel soups.

## Honest gaps / blockers

- Horizon not built locally (no Rust toolchain in sandbox, no network to rustup). Its tests were not run here.
- No GPU/Vulkan in sandbox → GPU rendering can't be validated here; Vulkan backend is intentionally not claimed working until it runs in CI (Lavapipe) or real hardware. The `vulkan-headless` CI job is the gate. First run failed at the PPM-validation step — root cause was a double-escaped `\n` in the inline Python (partition never matched, every frame was "empty"); fixed by moving validation to `voxelcore/scripts/validate_ppm.py` (unit-tested locally) and accepting only exit 0/77. The renderer now also dlopens libvulkan at runtime (`vulkan_loader.hpp`, Android-style) so builds never depend on a system loader.
- Android app (stage 12) not started; CI only compile-checks the engine for arm64.
- Minecraft compatibility: nothing claimed yet; world I/O is not Anvil yet.
- Cross-chunk leaves are clipped at chunk edges (documented simplification).
- Mesher hot path still does hash lookups per voxel; thread-local reader cache pending.

## Next concrete tasks

1. Vulkan backend bring-up behind `rendering/backend.hpp`; keep software renderer as fallback + CI path.
2. Heightfield-informed mesher reader (chunk heightmap short-circuits buried cells).
3. Sky/block light propagation (stage 9 first milestone).
4. Heightfield-informed mesher reader (chunk heightmap short-circuits buried cells).
5. Packed 24-byte records (E7 design) once backend draw path is perf-relevant.
6. CI green on the `vulkan-headless` job; then Windows/Android jobs reuse the same guard.
