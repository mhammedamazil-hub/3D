# ARCHITECTURE DECISIONS — PROJECT VOXELCORE (ADRs)

Format: decision, context, alternatives, consequences. Reversal needs benchmark + review.

## ADR-001: Native C++23, not a Rust translation
Horizon is 1.76 M lines of Rust with a bespoke GPU stack. Mechanical translation would import wgpu/naga complexity we cannot validate here, and would not be C++. We reimplement **functionality**, with C++-idiomatic architecture: header-first subsystems, arena allocation, SoA candidates (stage 6), templates over type erasure in hot paths. Consequence: parity is behavioral, verified by our tests + (later) differential harnesses — not by code similarity.

## ADR-002: Vulkan 1.2 primary, OpenGL ES 3.2 fallback, CPU rasterizer for CI
See TECHNOLOGY_COMPARISON. Justification: Android first-class support requires ES/Vulkan; desktop gets Vulkan; CI (no GPU) needs the software path, which we already use to prove the pixel pipeline. wgpu rejected (extra opaque layer; Horizon's wgpu bugs are not ours to inherit). D3D12/Metal rejected for v1.

## ADR-003: Minecraft-compatible storage format in memory (PalettedSection)
0-bit uniform sections, palette growth (bitsFor), on-demand widening, trim() recompaction. Interop with Anvil (stage 5) is then mostly a serialization concern. Consequence: block ids are local `BlockId` (uint16); a registry maps them to Minecraft state ids at the I/O boundary — never the other way around.

## ADR-004: Greedy meshing with baked per-corner AO and exact coverage invariant
Merge key = (BlockId, 4-corner AO). Invariant `faceArea == naiveFaces` is asserted in tests and in the `mesh` CLI. AO is Minecraft-style 4-tap, 4 levels. Consequence: merged quads interpolate AO linearly across the rect — matches Minecraft's smooth lighting approximation.

## ADR-005: Deterministic hash noise (no permutation table)
Integer-hash gradient noise; identical output on every platform for a seed — required for cross-platform save compatibility and reproducible tests. Quality is sufficient for terrain v1; worldgen 26.3 parity is a stage 11 problem (density graph port, not this).

## ADR-006: Job system = fixed pool + condvar + atomic batches; no work stealing yet
Measured 24.5 µs per 1M-iteration parallelFor dispatch on this machine with 4 workers; chunk-scale tasks dominate. Work stealing adds complexity without evidence of benefit at our task sizes; revisit stage 13 with counter instrumentation. Workers = hw−1, no spin-wait (matches Horizon's "Efficient" pacing finding).

## ADR-007: LOD as heightfield, not full-voxel far chunks
Far terrain never sims, meshes voxels, or ticks. v1 tile = 16×16 cells at 2^level m; single height per cell (fidelity gap documented; Horizon/Distant Horizons keep material layers — stage 8 upgrade). Crack strategy: skirts first, T-junction snapping if visual tests fail.

## ADR-008: Visibility is layered; GPU techniques are opt-in, never assumed
Layers: (1) frustum AABB (done), (2) cave flood fill, (3) leaf/entity/particle culling, (4) optional GPU decision pass + indirect-count draws + two-phase occlusion, capability-gated exactly as Horizon does, off by default. No GPU feature is allowed to be mandatory for correctness.

## ADR-009: Shaders = GLSL→SPIR-V, native pack first, Iris later, never rename-and-pray
Stage 10 ships a native pack format (checked, hot-reload, SHA-256 manifest, capability-based quality tiers: performance/balanced/high/experimental). Iris/OptiFine compatibility is a separate track with a feature matrix; only passed features may be claimed. Estimated unsupported initially: custom uniform namespaces, `entity.*`/`texture.*` parity gaps, frame-gen hooks, some composite buffer semantics — documented at stage 10.

## ADR-010: No telemetry, no launcher, no accounts, no ads
Engine only. If measurement is needed, it is `benchmarks/` + `PERFORMANCE_REPORT.md`, committed deliberately.

## ADR-011: Android = NDK + NativeActivity-first, GLES3.2 fallback mandatory
Vulkan requires device support we can't assume on the Android long tail; ES 3.2 is near-universal. CI compile-checks arm64-v8a every push (current). Stage 12 adds: lifecycle, touch input, asset management via APK assets, lifecycle-aware surface recreation, thermal-aware quality tier.

## ADR-012: Testing without external network dependencies
Local runner + ctest (current). Catch2 only via FetchContent with a pinned tag, adopted at stage 14 if sandbox proves the fetch. ASan/UBSan CI job (current). Benchmarks are CSV-emitting binaries; results recorded in BENCHMARK_HISTORY.md by hand per release — no fake automation of "results".

## ADR-013: Horizon clone is a read-only reference, never a dependency
Not vendored, not linked, no headers copied. `scripts/fetch_horizon.sh` re-creates it. Any code derived from studying Horizon is re-authored to C++ semantics and attributed in comments where structurally informative (e.g. side-bucket order).

## ADR-014: Correctness before performance, but benchmarks from day 1
Every optimization lands with baseline → hypothesis → implementation → benchmark → correctness test → comparison → written result. Regressions reverted or investigated, documented in REGRESSION_REPORT.md.

## ADR-015: Repository hygiene
Build dirs, generated renders, and the Horizon clone stay out of git (see `.gitignore`). Deliverable-sized binaries (APK) are CI artifacts, not repo files.
