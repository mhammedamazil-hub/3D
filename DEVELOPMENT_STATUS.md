# PROJECT VOXELCORE — DEVELOPMENT STATUS

**Date:** 2026-11-11 · **Branch:** `arena/3e3c4ae6-3d` · **Owner:** lead engineering agent

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
- `engine/meshing/mesher.hpp` — **greedy mesher**: visible-face elimination (internal solid faces never enter the mask), rectangle-merge by (block, 4-corner AO signature), per-corner Minecraft-style AO baked at mesh time, template-functor block reader (no std::function indirection in hot path).
- `engine/visibility/frustum.hpp` — Gribb–Hartmann frustum AABB culling (normalised planes, positive-vertex test).
- `engine/lod/heightfield_lod.hpp` — Distant-Horizons-style baked heightfield tiles (16×16 cells at 1<<level blocks), smooth LOD grid mesh emission.
- `engine/rendering/software_renderer.hpp` — z-buffered CPU rasterizer (verification path; proves mesh→triangles→pixels without a GPU).
- `tools/voxelcore-cli` — `gen`, `mesh`, `render`, `lod` commands; rendered `voxelcore/sample_render.png`.
- `tests/test_main.cpp` — 12 test groups (~33k checks): packed storage roundtrip across 8 widths, palette section growth/trim, arena reuse, job system, noise determinism, worldgen determinism, greedy mesher exactness (merged face area == naive visible faces; flat platform merges to 6 quads; buried 9³ cube emits exactly 486 face-area / 6 quads; AO bounds), frustum culling, LOD bake.
- `benchmarks/bench_main.cpp` — CSV micro-benchmarks (see numbers below).
- CMake (C++23) + Ninja; GitHub Actions CI: Linux build+test+bench+headless render, ASan/UBSan job, Android arm64-v8a NDK compile job.

## Measured results (this machine, gcc 12.2 -O3, 2026-11-11)

- Unit tests: **193,825 checks, 0 failures** (includes 60 random-soup mesher fuzz iterations + NBT/region roundtrips). ASan/UBSan build: 0 failures.
- `terrain_gen_chunk`: ~176 µs/chunk. `greedy_mesh_generated_chunk`: **~1.35 ms/chunk after E5** (cached block reader; was 2.0–2.3 ms).
- 9-chunk world mesh: 20.1 → **9.8 ms** (E5). Headless software frame: 32 → **21.9 ms** (backface culling).
- 9-chunk world (r=1): gen 1.5 ms, mesh 20.1 ms; 11,636 naive faces → 1,296 quads (**11.1% of naive**), `faceArea == naiveFaces` PASS.
- Flat-platform greedy merge: 704 → **6 quads**. `packed_storage_set_4096`: ~6.5 µs.
- LOD bake level 2 (4 m cells): 0.8 ms; 512-triangle grid mesh.
- **Stage 5 landed**: NBT reader/writer, Anvil `.mca` region I/O (zlib, sector allocation, full rewrite-on-flush), chunk↔NBT roundtrip — generated chunk saves and reloads byte-identically (`voxelcore saveload`).
- **Fuzz**: greedy-merge conservation law (`faceArea == naiveFaces`) holds on 60 random voxel soups.

## Honest gaps / blockers

- Horizon not built locally (no Rust toolchain in sandbox, no network to rustup). Its tests were not run here.
- No GPU/Vulkan in sandbox → GPU rendering can't be validated here; Vulkan backend is planned but intentionally not claimed working until it runs on real hardware (CI only compile-checks).
- Android app (stage 12) not started; CI only compile-checks the engine for arm64.
- Minecraft compatibility: nothing claimed yet; world I/O is not Anvil yet.
- Cross-chunk leaves are clipped at chunk edges (documented simplification).
- Mesher hot path still does hash lookups per voxel; thread-local reader cache pending.

## Next concrete tasks

1. Vulkan backend bring-up behind `rendering/backend.hpp`; keep software renderer as fallback + CI path.
2. Heightfield-informed mesher reader (chunk heightmap short-circuits buried cells).
3. Water/leaves translucent pass ordering; correct translucency.
4. Sky/block light propagation (stage 9 first milestone).
5. Side-bucket draw ordering (E6) + packed 24-byte records (E7 design).
6. First GitHub push + CI green (already pushed; CI green pending first run).
