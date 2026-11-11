# REIMPLEMENTATION PLAN — what Horizon does, what VOXELCORE does instead

Stages follow the mission; dependencies may overlap. Every stage ends in working software.

| Stage | Horizon approach | VOXELCORE approach | Status |
|---|---|---|---|
| 1 Acquisition & research | cloned; full source audit | cloned `04a2621`; audit in HORIZON_SOURCE_AUDIT.md; research docs | **done** |
| 2 Horizon audit | — | HORIZON_ARCHITECTURE.md, FEATURE_MATRIX, PERFORMANCE_BASELINE | **done** |
| 3 Engine foundation | Cargo workspace, crates | CMake+Ninja, C++23, paletted storage, arena, job system | **done** |
| 4 Window + renderer + GPU abstraction | winit + wgpu | Vulkan backend (planned); software renderer (works, PPM/PNG out); backend.hpp interface (next) | **in progress** |
| 5 World storage | Anvil regions, PalettedContainer, heightmaps, datafix 1.8→26.2 | PalettedSection ✓; Anvil read/write next; no datafix v1 | **in progress** |
| 6 Chunk gen + meshing | density graph worldgen, greedy mesher, packed records, side buckets, vertex arena, async upload | TerrainGen ✓; greedy mesher ✓ (AO-exact); side buckets/packed records designed (E6/E7); upload budget planned | **in progress** |
| 7 Visibility & culling | frustum + cave flood fill + leaf/entity/particle culling; GPU culling opt-in | frustum ✓; cave/leaf/entity planned (E8/E9); GPU culling stage 7+ (ADR-008) | **in progress** |
| 8 Hierarchical LOD | reduced voxel columns, cached scales, screen-error refine, BlueMap fallback | heightfield tiles ✓ v1 (bake 0.8 ms); crack prevention, material layers, disk cache next; 1024-RD far goal | **in progress** |
| 9 Lighting & materials | sky+block light, smooth AO, HDR, PBR-ish material packs | AO-at-mesh ✓; proper sky/block light engine + PBR materials with GLSL shaders | planned |
| 10 Shader packs | .hshader WGSL native + Iris/OptiFine loader | native GLSL→SPIR-V packs, quality tiers, pipeline cache; Iris feature-gated after | planned |
| 11 Minecraft compatibility | full parity via differential harnesses | Anvil + terrain parity first, then protocol; no compatibility claim until differential tests pass | planned |
| 12 Android | android_runtime crate, Vulkan/Metal/GL | NDK + NativeActivity + ES 3.2 fallback; CI compile check ✓ (arm64) | **CI check done**, app planned |
| 13 Performance | perf_bench.py, Efficient pacing, arenas | benchmark suite ✓; pacing/Arenas/GPU culling tuning; re-baseline on real GPU | planned (bench infra done) |
| 14 Testing & release | PR CI + parity runner + launcher releases | ctest ✓; ASan/UBSan CI ✓; release workflow when Android/desktop artifacts exist; **no artifact claimed unbuilt** | **CI in place**, releases planned |

## Cross-cutting workstreams

- **Correctness**: greedy-mesh invariant test, determinism tests, frustum tests — done. Next: golden-image software render test, Anvil roundtrip test, mesher fuzz (random voxel grids vs naive face count).
- **Performance**: all claims via `voxelcore/build/voxelcore_bench` CSV + PERFORMANCE_REPORT.md; BENCHMARK_HISTORY.md logs each run.
- **Documentation**: this directory; DEVELOPMENT_STATUS.md updated every session.
- **Risks** (top): (1) no GPU in dev sandbox → GPU work verified only in CI compile + user hardware; mitigation: keep software path first-class. (2) Minecraft parity scope is enormous; mitigation: explicitly stage it, claim nothing early. (3) Terrain quality vs Java — our noise terrain is a placeholder; stage 11 ports the density graph approach. (4) Single-person throughput; mitigation: strict stage gating, smallest working increments.
