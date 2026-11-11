# Horizon Source Audit — PROJECT VOXELCORE

**Target:** `github.com/horizon-rust/horizon` (MIT) · clone @ `04a26210e31fedf763175dcb05c0b0bdf2fefd21` (shallow) · audited 2026-11-11 · 3,164 Rust files, 1,760,457 lines.
**Local clone:** `/home/user/horizon` (reference only; not vendored into git). Reproduce with `scripts/fetch_horizon.sh`.
**Build status:** NOT built locally — no Rust toolchain in the sandbox and rustup hosts are unreachable. Numbers below cite the repo's own published reports.

## License & legal posture

Horizon is MIT-licensed (`LICENSE`, `THIRD_PARTY_NOTICES.md`). It contains no Minecraft code or assets: it ships with none and prepares files from the user's own Java Edition install. PROJECT VOXELCORE reimplements functionality under the same legal posture: no Minecraft assets/code, compatibility via the Java Edition data formats and protocol only.

## Repository shape (workspace of 49 crates + xtask + launcher)

| Area | Crate(s) | Notes (audited) |
|---|---|---|
| Client game loop | `horizon-client` (38 MB, largest) | tick/render, game.rs, LAN, integrated server, mobs, containers |
| Rendering | `horizon-client-render` (11 MB) | wgpu via vendored `third_party/wgpu-hal` + `naga`; WGSL shaders; `gfx/` (3.1 MB), `mesher/`, `lod/`, `streaming/`, `pack_*` (shader-pack stages) |
| World model & sim | `horizon-world` (8 MB) | Anvil region I/O (`region.rs`, `nbt.rs`), `level/` (tick, redstone, block behavior), `worldgen/` (2.6 MB; density graph, aquifer, carvers, structures, trees), datafix for 1.8→26.2 saves |
| Core | `horizon-core` (1 MB) | noise, jmath, `storage.rs` (PackedStorage), density graph, position types |
| Protocol | `horizon-protocol` (2.6 MB) | packets play/connection/entity_data — Java Edition 26.3 mapping |
| Shader ecosystem | `horizon-shaders`, `horizon-shader-api`, `horizon-optifine` (Iris/OptiFine loader), `horizon-polytone` | own WGSL pack format (`.hshader`) + Iris/OptiFine compatibility loader; shader checking, hot reload |
| Server | `horizon-server`, `horizon-bots`, `horizon-official*`, `horizon-relay` | dedicated server, LAN hosting, Velocity forwarding |
| Ops/infra | `cargo-horizon-mod`, `horizon-mod-*`, `horizon-mcp`, `horizon-telemetry*` | mod registry, MCP control, telemetry (off in CI) |
| Third party | `third_party/wgpu-hal`, `third_party/naga`, `third_party/libmimalloc-sys` | vendored GPU stack pinned to their forks |

## Key architecture findings (evidence)

1. **Renderer is wgpu (WebGPU-class), not Vulkan directly.** Evidence: `third_party/wgpu-hal`, `third_party/naga`, `crates/horizon-client-render/src/gfx/*.rs` + `*.wgsl` (capture.rs, compositor.rs, gpu_culling.rs + `gpu_culling.wgsl`, `gpu_occlusion.wgsl`, pack_sky/pack_post/...), `docs/graphics.md` ("GPU Culling … Vulkan with VK_KHR_draw_indirect_count … OpenGL, Metal …"), README (Vulkan on Windows/Linux, Metal on macOS). Metal gets two solid passes; Vulkan gets GPU culling + two-phase GPU occlusion culling.
2. **Compact solid-quad records.** `mesher/packed.rs`: most solid quads that are whole cube faces store a 24-byte record instead of 4×24-byte vertices; `terrain.wgsl` expands records at draw time; `PACKED_BASE = 1<<28` marks packed base vertices.
3. **Side-bucket ordering.** `mesher/sides.rs`: solid quads sorted into 7 side buckets (+X,+Z,other,+Y,−Z,−X,−Y) so the eye-facing runs are typically 1–2 draws; per-section planes skip whole buckets behind the eye; coplanar quads keep model order; cutout vs opaque parts separated.
4. **Paletted storage everywhere.** `horizon-world/src/chunk.rs`: `PalettedContainer` with `bits_for_palette`, uniform sections (0 bits), grows storage bits on demand; `horizon-core/src/storage.rs`: `PackedStorage` (5/8/… bit widths, 4096-cell sections, tests included).
5. **Leaf culling** (`mesher/leaf_culling.rs`, 676 lines): hides interior leaves; `visibility_tests.rs` etc. gate mesh correctness; **LOD** (`lod/mesh.rs` 1867 lines, `bake.rs`, `cache.rs`, `packed.rs`, `samples.rs`): reduced voxel columns at progressively coarser scales, cached generated columns, refinement by screen error, BlueMap fallback, seed-sampled density terrain beyond server view distance; supports 1,024-chunk render distance (README).
6. **Async everything heavy**: chunk generation workers, streaming with upload budgets, `streaming/`, background BlueMap fetch, async PBO-ish GPU culling; `terrain-gen` indirect; mesh rebuild budgets.
7. **Differential testing vs vanilla** is the correctness backbone: parity harnesses per subsystem (`python3 tools/parity.py`), `docs/parity/`, "hundreds of differential tests" (README), hundreds of CI-linked checks; GPU tests degrade gracefully on lavapipe (`.github/workflows/ci.yml`).
8. **Memory discipline**: arena allocators (`gfx/arena.rs`, vertex arena), mimalloc vendored, 1.1–1.7 GB working set vs vanilla's 1.9–2.9 GB (published).
9. **Frame pacing**: "Efficient" pacing on fixed time grid vs vanilla spin-wait; present-mode selection; resolution scale; FXAA/TAA; HDR pipeline (`hdr.rs`); frame generation (`gfx/frame_gen.rs`).
10. **Isolation**: rendering vs simulation separated (`horizon-world` has no rendering deps; renderer reads committed chunk state; LAN host = integrated server in background thread).

## What to preserve / redesign / optimize / replace

| Component | Decision | Why |
|---|---|---|
| PalettedContainer + PackedStorage semantics | **Preserve (reimplement in C++)** | Proved design; matches Java format; compact memory |
| Greedy meshing + side buckets | **Preserve concept, reimplement clean** | World-class quad reduction; our AO-signature merge is exact |
| wgpu abstraction | **Replace** (with Vulkan primary; OpenGL ES fallback) | wgpu adds a 3rd abstraction layer we can't control/validate in CI without GPU; direct Vulkan is narrower and Android-friendly. Trade-off documented in ARCHITECTURE_DECISIONS.md |
| WGSL shaders | **Replace with GLSL→SPIR-V** | Tooling (glslang/shaderc/SPIRV-Tools) is ubiquitous; Vulkan-native path; Naga/WGSL stack stays a read-only reference |
| 1024-chunk LOD design | **Preserve concept, simplify v1** | Heightfield tiles + refinement is the right shape; our stage 8 does 2-level LOD first |
| GPU culling/occlusion | **Adopt in stage 7+ (Vulkan path)** | Big wins at high draw counts; gate behind capability detection + perf fallback as Horizon does |
| Differential tests vs vanilla | **Adopt later (stage 11)** | Requires Java Edition harness; out of scope until world I/O lands |
| Iris/OptiFine pack loader | **Study, do not port now** | License/complexity; stage 10 starts with native .hshader-style format |
| Telemetry/mods/launcher/account | **Drop entirely** | Out of scope for an engine reimplementation |
| Datafix (1.8→26.2 migrations) | **Drop for v1** | Read current-format worlds only; document |

## Test & CI observations

Horizon CI: single `verify` job (PR triage), parity harnesses on a self-hosted Mac mini with real Minecraft files, ASan builds, launcher/site deploy pipelines. Takeaway for VOXELCORE: one fast Linux gate per PR + a heavier scheduled job; never gate merges on proprietary assets.
