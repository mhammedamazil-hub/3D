# Horizon Feature Matrix (Java Edition 26.3 parity, audit-derived)

Status: **present in Horizon** (from README + docs + source inspection). VOXELCORE reimplementation status is tracked in `DEVELOPMENT_STATUS.md` and `REIMPLEMENTATION_PLAN.md`.

| System | Horizon | VOXELCORE (now) | VOXELCORE target |
|---|---|---|---|
| Survival/creative/hardcore/spectator | Yes | — | stage 11 |
| Vanilla worldgen 3 dims (overworld/nether/end) | Yes, differential-tested | partial (deterministic overworld-like) | stage 11 |
| Datafix 1.8→26.2 save upgrade | Yes | — | drop v1 (document) |
| Mobs / raids / villagers / redstone / commands | Yes | — | stage 11 |
| Multiplayer (online mode, LAN, dedicated server) | Yes | — | stage 11 |
| Vanilla resource/data packs | Yes | — | stage 9/10 |
| Shader packs: Horizon native (.hshader WGSL) | Yes (checked, hot-reload) | — | stage 10 (GLSL→SPIR-V native) |
| Shader packs: Iris/OptiFine (Complementary/BSL/SEUS) | Loader present, compatibility bounded — **not** universally claimed | — | stage 10, investigate; never claim untested |
| Distant terrain (LOD) | Yes, up to 1,024 chunks | **Bake + render path implemented (heightfield)** | stage 8 |
| GPU culling + GPU occlusion culling | Vulkan only, opt-in | **Frustum culling done**; GPU culling planned stage 7 | stage 7 |
| Cave culling | Yes | — | stage 7 |
| Leaf culling | Yes | partial (leaves vs leaves face elimination) | stage 7 |
| Entity/particle culling (sync/async) | Yes | — | stage 7 |
| HDR pipeline, FXAA/TAA, frame gen | Yes | — | stage 9/13 |
| Frame pacing (efficient grid) | Yes | — | stage 13 |
| Controllers / HDR / narration / split-screen | Yes (roadmap) | — | out of scope |
| Android | Yes (client crate has android_runtime) | CI compile check only | stage 12 |
| Telemetry, launcher, accounts, mod registry | Yes | dropped by design | — |
| Compact packed-quad records / side buckets | Yes | planned stage 6/13 | stage 6/13 |
| Vertex arena w/ page reclaim | Yes | planned stage 6 | stage 6 |
| Paletted chunk storage | Yes | **Yes (PalettedSection)** | ✓ |
| Greedy meshing | Yes (AO-baked per vertex) | **Yes (exact, tested)** | ✓ |
| Headless test harness | parity.py differential | ctest, 12 groups green | stage 14 |

Legend: ✓ implemented & tested this session · partial/planned = scheduled, not claimed working.
