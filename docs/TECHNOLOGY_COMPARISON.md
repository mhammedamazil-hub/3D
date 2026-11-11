# TECHNOLOGY COMPARISON — alternatives considered, decisions taken

Each row: option A vs option B (or more), decision, evidence. Reversals require a written ADR (see ARCHITECTURE_DECISIONS.md) and a benchmark.

## Rendering API
| | Vulkan | OpenGL 3.3/4.6 | OpenGL ES 3.x (Android) | wgpu/WebGPU | DirectX 12 | Metal |
|---|---|---|---|---|---|---|
| Role | **Primary desktop + Android** | Fallback desktop | Android fallback | Reference only (Horizon uses it) | Rejected (platform) | Rejected (platform) |
| Compute | first-class | limited | limited | first-class | first-class | first-class |
| `VK_KHR_draw_indirect_count` GPU culling | yes | no | no | maps to | yes | yes |
| CI testability | lavapipe/llvmpipe possible; none here | possible | n/a | possible | n/a | n/a |
| Our experience surface | mandatory | good | good | — | — | — |

**Decision:** Vulkan 1.2 as the baseline (draw-indirect-count is KHR/promoted), OpenGL 4.6/ES 3.2 fallback behind the same `rendering/backend.hpp` interface, software CPU rasterizer as the CI verification path (already implemented). wgpu rejected: an extra abstraction/toolchain to debug when the thing we most need is measurable GPU pipelines, and Naga already serves Horizon as reference. D3D12/Metal: out of scope until a Windows/macOS port is demanded; both break parity with our Android-first path less than they cost in CI.

## Shading language
| GLSL→SPIR-V (glslang/shaderc) | HLSL→SPIR-V (DXC) | WGSL (naga) | MSL |
|---|---|---|---|
| **Adopted** — ubiquitous tooling, Khronos-native, OpenGL ES fallback for free | good, but nothing we need | Horizon's stack; ties us to naga | Apple only |

**Decision:** GLSL 450 core for Vulkan; ES-compatible subset for GLES; SPIR-V 1.5 target; pipeline cache blobs persisted; async compile on a worker; hot reload in dev builds only.

## Chunk dimensions
| 16×16×16 sections (vanilla) | 16×16×24 | 32×32×16 | 64×64 tiles |
|---|---|---|---|
| **Adopted** — matches PalettedContainer format, face culling locality, cache size | vanilla height is 24 sections×16=384 for overworld; we start 4 sections (64) for iteration, extend to full height in stage 5 | fewer section borders, worse cache + worse halo overhead | far too coarse for mesh granularity |

**Decision:** 16×16×16 now (64-block world height for iteration); full 384-block height in stage 5; benchmark 16³ vs 32³ section variants on the mesher benchmark before stage 6 ends.

## Language/runtime
| C++23 (gcc 12, MSVC 2022, clang 17) | C++20 | Rust | Zig |
|---|---|---|---|
| **Mission requirement.** gcc 12.2 accepts `-std=c++23`; we avoid std::format/std::print until toolchain matrix is proven | safe subset used in practice | Horizon is Rust — but the mission is a C++23 engine | out of scope |

**Decision:** C++23 with a C++20-compatible core (no <format>, <print>, <expected> dependency yet — expected lands in gcc 13/clang 16+; we have our own status types for now).

## Build system
| CMake + Ninja | Bazel | Meson | Premake |
|---|---|---|---|
| **Adopted** — universal, Android toolchain file support, consumers know it | too heavy here | fine but smaller ecosystem for Android | weak |

## Testing
| Custom 140-line runner (current) | Catch2 via FetchContent | GoogleTest via FetchContent |
|---|---|---|
| **Adopted for now** — zero deps, offline-safe, ctest wired | adopt at stage 14 when network-verified | alternative |

## Meshing strategy
| Greedy (exact, AO-signature) | T-junction triangle soup | Naive per-face |
|---|---|---|
| **Adopted.** Measured: 704-face flat platform → 6 quads; 24,960-face terrain → 1,296 quads (11.1%) | best for GPU but AO baking gets complicated | baseline; rejected |

## Visibility
| Frustum only (now) | + Cave culling | + GPU culling/occlusion (opt-in) | + HZB CPU |
|---|---|---|---|
| done | stage 7 | stage 7+ | rejected v1 |

## LOD distant terrain
| Heightfield columns (Horizon/Distant Horizons) | Full-voxel far chunks | BlueMap fallback | Geomipmap grid |
|---|---|---|---|
| **Adopted v1** (grid mesh, baked tiles) | rejected: sim cost doesn't scale | stage 11 optional | adopted for mesh emission |

## Storage/compression
| Paletted + uniform sections (Minecraft format) | LZ4 region files | Custom format |
|---|---|---|
| **Adopted** (in-memory) | stage 5 (regions) | rejected — interoperability wins |

## Job system
| std::thread + condvar pool, atomic batch claiming (current) | Task graph library | Lock-free work-stealing deques |
|---|---|---|
| **Adopted** — simple, measured, no oversubscription | premature | premature optimization; revisit stage 13 |
