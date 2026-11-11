# Horizon Architecture — How It Actually Works (audit-derived)

Companion to `HORIZON_SOURCE_AUDIT.md`. Paths are relative to the Horizon clone (`/home/user/horizon`).

## 1. Data flow (frame and world)

```
window event loop (about_to_wait)                crates/horizon-client/src/game.rs
  → tick: input → player physics → world tick (chunks, redstone, block entities, mobs)
  → render: build/reuse chunk meshes → cull (frustum, cave, leaf, entity, particle)
           → sort into opaque/cutout/translucent → draw (Vulkan/Metal/GL)
           → post chain (hdr/tonemap/fxaa|taa/frame-gen)
```

Chunk pipeline: **generate (workers, density graph) → light (async) → mesh (workers) → upload budget per frame (vertex arena) → draw**. Mesh rebuild is budgeted and incremental; only dirty sections re-mesh.

## 2. World storage

- Sections are 16³ cells stored as **PalettedContainer**: palette (block state tags) + `PackedStorage` of N-bit indices; uniform sections store nothing. Evidence: `horizon-world/src/chunk.rs`, `horizon-core/src/storage.rs`.
- Persistence: **Anvil region files** (`.mca`, 32×32 chunks/region), zlib/LZ4-ish compression via `compression.rs`, NBT (`nbt.rs`), `datafix/` migrates saves 1.8→26.2 on load.
- Heightmaps are maintained per chunk for lighting/generation queries.

## 3. Meshing (`horizon-client-render/src/mesher/`)

- Per-face emission with per-vertex AO; **visible faces only** (leaf culling: interior leaves hidden; `leaf_culling.rs` + tests).
- **Compact packed quads**: whole-cube-face quads stored as 24-byte records expanded in `terrain.wgsl` (`PACKED_BASE = 1<<28`), vertex arena hands pages back when unused.
- **Side buckets** (`sides.rs`): 7 ordered buckets so eye-visible buckets render in 1–2 runs; coplanar order preserved; opaque and cutout parts separated for two-pass renderers (Metal).
- AO/lighting baked per vertex (`lighting.rs`): sky+block light, 4 levels, with smooth lighting paths.
- Reuse tests (`reuse_tests.rs`): meshes survive unrelated changes; rebuild minimization.

## 4. Visibility & culling (`gfx/cull.rs`, `gfx/occlusion.rs`, `gpu_culling.*`)

- Frustum culling per section; **cave culling** (flood-fill from opaque neighbors to drop never-visible cave sections); leaf culling; entity culling (sync/async, camera-position-quantized cache); particle culling.
- **GPU culling** (optional, off by default, Vulkan only): compute pass decides per resident section what CPU would decide; one `drawIndirectCount` per arena page; two-phase GPU occlusion culling with per-section decisions. Needs `VK_KHR_draw_indirect_count` + compute; Intel Gen11/12 and software rasterizers excluded; D3D12 excluded (loses base-vertex).

## 5. LOD / distant terrain (`lod/`)

- Progressively coarser **voxel columns** keeping material layers and air gaps; matching exposed faces merged with block-scale texture repeats; brightest sky/block light retained per reduced cell.
- Baked once on the terrain worker; cached per scale (`lod/cache.rs`); refinement prioritizes **screen error**; high aerial views coarsen below the camera; BlueMap lowres tiles are an optional far-field source for servers without seed access; generated-chunk LOD via a separate bounded worker (4×4 halos) that never enters gameplay.
- Render distance up to **1,024 chunks**; distant terrain beyond it renders as cached reduced columns (Bobby-compatible read-only cache).

## 6. Shader packs

- **Horizon's own format** (`.hshader`, WGSL, checked before execution, hot reload 2 Hz, SHA-256, `Options → Video Settings → Shaders`): stages sky/material/post.
- **Iris/OptiFine format**: separate loader (`horizon-optifine`, `docs/shaders.md`); compatibility is real but bounded — many advanced packs rely on unsupported uniforms; unsupported features documented, not silently ignored.
- **Pack stages** are compiled from declarative stage descriptions (`pack_sky.rs`, `pack_post.rs`, `pack_shadow.rs`, …) into naga WGSL; per-pack options screens.

## 7. Frame pacing & perf

- "Efficient" fixed-grid frame limiter (no spin-wait); resolution scale; FXAA/TAA; HDR; frame generation (opt-in); **1–2 orders of magnitude less CPU per frame** at RD 16–32 vs vanilla (published).
- Memory: vendored mimalloc; vertex arena; 1.1–1.7 GB working set at gameplay.

## 8. Build & quality

- Cargo workspace; `rust-version = 1.95`; vendored wgpu/naga; CI single `verify` job; self-hosted parity runner with real Minecraft for differential tests; `tools/perf_bench.py` for before/after performance evidence with confidence intervals; benchmark reports committed under `benchmarks/perf/`.

## 9. What we take from this (and what we don't)

| Take | Leave |
|---|---|
| Paletted storage, greedy meshing, side buckets, packed records, vertex arena | wgpu, naga/WGSL, mimalloc vendoring |
| Heightfield LOD with per-cell material + light retention, cache + screen-error refinement | 1024-chunk ambition for v1 |
| GPU culling design (compute decision pass + drawIndirectCount + two-phase occlusion) | Making it default; it's off by default upstream too |
| Differential testing philosophy | Running it now (needs Java Edition + harness) |
| Frame pacing philosophy (fixed grid, no spin) | Telemetry, launcher, accounts, mods |
