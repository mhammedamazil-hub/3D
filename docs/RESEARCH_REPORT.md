# RESEARCH REPORT — PROJECT VOXELCORE

Scope: rendering, voxel storage, visibility, LOD, shaders, performance engineering, tooling. Claims cite sources; nothing here is invented. Where we lack data, the report says so.

## 1. How the reference points work (verified from source/docs)

### Horizon `04a2621` (primary functional reference)
- World: 16³ PalettedContainers inside 24-section columns (vanilla 1.18+ height), Anvil regions, heightmaps, async light, worker-thread generation with halo sharing for LOD (`horizon-world`, `horizon-client-render/src/lod/bake.rs`).
- Meshing: visible-face elimination; AO per vertex; 24-byte packed whole-cube-face records expanded in WGSL at draw time; side buckets; opaque/cutout split; vertex arena with page reclaim (`mesher/packed.rs`, `mesher/sides.rs`, `gfx/arena.rs`).
- Visibility: frustum + cave culling (flood fill from opaque neighbors), leaf culling, entity culling (sync + async with camera-position-quantized bounds and release-on-world-change), particle culling; optional **GPU culling** (compute decision pass + `VK_KHR_draw_indirect_count`, two-phase GPU occlusion) — off by default, Vulkan-only, disabled for Intel Gen11/12 + software rasterizers (`docs/graphics.md`).
- LOD: progressively coarser voxel columns with material layers and air gaps retained; exposed matching faces merged with block repeats; brightest sky/block light per reduced cell; cached scales; screen-error-refined; BlueMap fallback; "Generated-column caches and request queues are bounded" (`docs/graphics.md`).
- Frame pacing: fixed time grid, no spin-wait (`docs/graphics.md`).

### Minecraft Java Edition (vanilla / Sodium)
- Rendering: OpenGL, chunk section meshes (sodium replaces vanilla's translation-heavy path with a compact multidraw approach). Sodium (CaffeineMC) reports ~1.5–2× over vanilla at high RD and is the de-facto performance oracle ([Sodium README](https://github.com/CaffeineMC/sodium-fabric)).
- Sodium technique highlights: multidraw + chunk sorting by translucency, compact vertex formats, "renderpasses" separation (opaque/cutout/translucent/weather/entities).

### Iris Shaders
- Iris ([IrisShaders/iris](https://github.com/IrisShaders/iris)) emulates OptiFine's shader pack pipeline on Fabric: pack-provided GLSL programs patched into fixed pipeline stages (gbuffers_*, shadow, composite, deferred), with its own uniform/format compatibility layer. Lesson: **shader-pack compatibility is a large emulation problem, not a renaming exercise** — Horizon likewise treats it as its own loader with a compatibility matrix (`docs/shaders.md`). VOXELCORE stage 10 starts with a native format; Iris emulation is research-only until we pass the same gates Horizon does.

### Distant Horizons ([Distant-Horizons-Team/DistantHorizons](https://github.com/Distant-Horizons-Team/DistantHorizons))
- LOD columns at 4/8/16/32/64 m; full simulation never happens for LOD; seam handling via ring transitions; distant shadows. Confirms our heightfield+grid approach; Horizon independently converged on the same (their columns keep material layers + air gaps, we currently keep single-height columns — a known fidelity gap, stage 8 remedy).

### Unreal Engine (Nanite, VSM, World Partition)
- Nanite ([UE5 docs: Nanite Virtualized Geometry](https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine)): cluster (meshlet) hierarchy, GPU-driven culling + LOD selection, micropolygon rasterizer. Not directly portable: voxel chunk meshes are tiny vs Nanite clusters; our meshes are already minimal after greedy meshing.
- Virtual Shadow Maps ([UE VSM docs](https://dev.epicgames.com/documentation/en-us/unreal-engine/virtual-shadow-maps-in-unreal-engine)): page-table shadow caching with per-page invalidation — directly applicable to stage 9 cascades for 1024-chunk worlds; researched, not scheduled yet.
- World Partition: cell-based streaming with data layers and runtime grids — our chunk ticket system mirrors this; full WP machinery unnecessary.

### Terrain clipmaps & multiresolution terrain
- Clipmaps (Tanner, 2004; "The Geometry Clipmap", NVIDIA GPU Gems 2): nested concentric grids centered on camera; T-junction elimination via snapping rings; one-pass upsampling for blend regions. We use clipmap-style ring selection conceptually in stage 8.
- Geomipmapping (de Boer, 2000, SIGGRAPH course notes): screen-error-based LOD selection — same criterion as Horizon's LOD refinement; we adopt it for tile selection.

### MagicaVoxel, Teardown
- MagicaVoxel: sparse 40³ octree-ish storage + palette; our PalettedSection is the same idea at Minecraft scale (4096 cells with 0-bit uniform sections).
- Teardown: fully destructible voxel scenes via SDF-ish/height voxel representation + ray tracing; orthogonal to our goals; documented and rejected for VOXELCORE (we need Minecraft-compatible block worlds, not destruction-first ray tracing).

### Vulkan-based voxel engines
- bevy_voxel_world, VoxelGameEngine (GitHub), and Horizon itself: consensus — compute-indirect + section arenas scale best; CPU path caps at a few hundred sections/frame.

## 2. Techniques investigated: cost / complexity / verdict

| # | Technique | CPU cost | GPU cost | Complexity | HW/API compat | Verdict |
|---|---|---|---|---|---|---|
| 1 | Greedy meshing | low | n/a | medium | any | **Adopt (done)** |
| 2 | Paletted storage | low | n/a | medium | any | **Adopt (done)** |
| 3 | Frustum AABB cull | low | n/a | low | any | **Adopt (done)** |
| 4 | Side-bucket draw ordering | low | saves vertex fetch | low | any | **Adopt stage 6** |
| 5 | Packed 24-byte quad records | low (pack time) | large vertex-bandwidth saving | medium | any (needs vertex pulling or unrolled expansion) | **Adopt stage 6/13** |
| 6 | Cave culling (flood fill) | medium (BFS) | saves everything downstream | medium | any | **Adopt stage 7** |
| 7 | Entity/particle culling | low | saves draw calls | low | any | **Adopt stage 7** |
| 8 | GPU culling + drawIndirectCount | ~0 CPU | compute + indirect | high | Vulkan + feature bit; not Intel Gen11/12, not D3D12 path | **Adopt stage 7+ (opt-in, capability-gated)** |
| 9 | GPU two-phase occlusion culling | ~0 CPU | 2 compute passes | high | same gating as #8 | **Adopt stage 7+ (opt-in)** |
| 10 | Software occlusion culling (HZB on CPU) | high | saves GPU | high | any | **Reject for v1** (redundant with #8) |
| 11 | HZB occlusion on GPU | medium | depth-pyramid build + tests | high | Vulkan | **Stage 13 candidate** |
| 12 | Virtual shadow maps (clipmap shadows) | low | page cache | high | Vulkan/D3D12 | **Research; stage 9/13** |
| 13 | Heightfield LOD tiles + grid mesh | medium bake, amortized | trivial | medium | any | **Adopt stage 8 (done, v1)** |
| 14 | Meshlet/cluster rendering (Nanite-style) | high build | high decode | very high | mesh shaders | **Reject** (wrong scale; no mesh-shader baseline) |
| 15 | Mesh shaders | — | — | high | optional ext | **Reject v1; monitor** |
| 16 | Bindless resources | low | descriptor indexing | medium | Vulkan 1.2 feature | **Stage 9 (materials)** |
| 17 | Virtual texturing | medium | page table | high | Vulkan | **Stage 13 candidate** |
| 18 | Temporal anti-aliasing / upscaling | 0 CPU | ~1 spp | medium | any | **Stage 9/13** |
| 19 | Dynamic resolution scaling | 0 | 0 | low | any | **Stage 13 (frame pacing)** |
| 20 | Fixed-grid frame pacing | low | 0 | low | any | **Adopt stage 13** |
| 21 | Async shader compilation + pipeline cache | low | 0 | medium | Vulkan (pipeline cache blob) | **Adopt stage 10/13** |
| 22 | Shader permutation management (ubershader + specialization constants) | low | 0 | medium | Vulkan | **Adopt stage 10** |
| 23 | Thread-local chunk cache for readers | low | 0 | low | any | **Adopt stage 6** |
| 24 | SIMD for meshing/AO (AVX2) | — | — | medium | x86 | **Measure first; stage 13** |
| 25 | Compressed voxel storage (palette+uniform) | 0 | 0 | done | any | **Adopt (done)** |
| 26 | Texture streaming | medium | memory mgmt | high | any | **Stage 13** |
| 27 | Async resource decompression worker | low | 0 | medium | any | **Stage 8/13** |
| 28 | Adaptive workload scheduling (budgeted uploads) | low | 0 | low | any | **Adopt stage 6/13** |
| 29 | Cache-aware SoA layouts (BlockId arrays) | 0 | 0 | low | any | **Adopt stage 6** |
| 30 | Deterministic terrain (hash noise) | 0 | 0 | done | any | **Adopt (done)** |
| 31 | TAA-sampled BlueMap fallback | 0 CPU | 0 | medium | any | **Stage 11 (optional far-field)** |

## 3. Findings that changed our design

1. **Horizon's answer to "render distance vs cost" is not bigger GPUs, it's refusing to do work**: 0-bit uniform sections, face-hidden leaves, cave flood fill, LOD columns that never simulate. We copied this principle wholesale.
2. **GPU culling is the wrong default for weak GPUs** — Horizon gates it off by default with hardware exclusions. Our capability detector (stage 10) will do the same.
3. **Shader-pack compatibility is emulation**, not translation; Iris/OptiFine support will only be claimed after passing documented feature gates.
4. **Differential testing** is the only trustworthy correctness oracle for Minecraft compatibility; it needs Java Edition, so it's scheduled at stage 11+, not faked now.

## 4. Open questions (being tracked)

- 24-byte packed records with per-corner AO: does AO still fit the record? (Horizon solves this with per-corner light codes; our AO needs 2 bits/corner = 8 bits, fits word 5 alongside face; verify at stage 6.)
- Heightfield LOD crack prevention (skirts vs T-junction fixing) — we will test skirts first (simpler).
- Whether to keep C++23 ranges or drop to C++20 for Android NDK r26/r27 toolchains — check CI matrix at stage 12.

## 5. Sources

- Horizon repo: `docs/graphics.md`, `docs/shaders.md`, `docs/architecture.md`, `docs/benchmark.md`, `benchmarks/perf/windows-9800x3d-5080-2026-10-29.md` (local clone @ 04a2621).
- Sodium: https://github.com/CaffeineMC/sodium-fabric
- Iris: https://github.com/IrisShaders/iris
- Distant Horizons: https://github.com/Distant-Horizons-Team/DistantHorizons
- Unreal Nanite: https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine
- Unreal Virtual Shadow Maps: https://dev.epicgames.com/documentation/en-us/unreal-engine/virtual-shadow-maps-in-unreal-engine
- Unreal World Partition: https://dev.epicgames.com/documentation/en-us/unreal-engine/world-partition-in-unreal-engine
- Geometry clipmaps (Tanner et al., GPU Gems 2, ch. 2): https://developer.nvidia.com/gpugems/gpugems2/part-i-geometric-complexity/chapter-2-terrain-rendering-using-geometry-clipmaps
- Geomipmapping: de Boer, W.H. (2000), "Fast Terrain Rendering Using Geometrical MipMapping", SIGGRAPH course 28 notes.
- MagicaVoxel: https://ephtracy.github.io/
- Vulkan draw indirect count: VK_KHR_draw_indirect_count; Vulkan 1.2 core.
- WGSL / Naga: https://github.com/gfx-rs/naga
