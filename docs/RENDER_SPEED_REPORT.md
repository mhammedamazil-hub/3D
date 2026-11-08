# Render-route and speed report — Monsoon Light, Kerala

Sandbox: Debian 12, 2 vCPU Intel Xeon @ 2.60 GHz, 3.85 GiB RAM, **no GPU**, Blender 4.2.23 LTS as PyPI `bpy`. Network restricted to GitHub/PyPI/npm. Timings below are measured render-operator wall times unless noted; Python startup and `.blend` load are excluded. Different revisions are labelled—do not compare them as identical scenes.

## Measured local routes

| Route | Scene / settings | Result | Time | Notes |
|---|---|---:|---:|---|
| Cycles CPU preview | v1.4 frozen, 640×360, 12 samples, adaptive, OIDN, mist | PASS | 21.0 s | Reliable lookdev route; `review/10_v14_hero.png`. |
| Cycles CPU bench | v1.3, 960×540, 24 samples | PASS | 58.9 s | Pre-freeze benchmark; `review/09_cycles_bench_540.png`. |
| Cycles CPU final | v1.4 frozen, 1920×1080, 64 samples, adaptive .03, OIDN | **PASS** | **830.3 s** | Hero still; exact frozen SHA in receipt; `output/Kerala_Monsoon_Light_1080p.png`. |
| Workbench clay proxy | v1.2, 800×450, field vegetation/mist/sky hidden | PASS | 33.8 s | Useful silhouette proxy, not a beauty renderer; `review/07_clay_proxy.png`. |
| Workbench full density | v1.0, 960×540, all instances | PASS but impractical | 622.1 s | Software OpenGL rasterized ~20M+ instanced triangles very slowly. |
| Eevee Next full density | v1.4, 480×270, 8 samples, ray tracing + volume | **FAIL / OOM** | killed | Linux OOM killer at ~3.8 GiB RSS; no image delivered. |
| Eevee Next reduced LOD | v1.4 frozen, 480×270, 8 samples, lower GN density, no volume/ray tracing | PASS | 56.7 s | `review/12_eevee_fast_lod.png`. |
| Eevee Next reduced LOD | v1.4 frozen, 960×540, 8 samples, lower GN density, no volume/ray tracing | PASS | 53.8 s | Delivered fast preview compromise: `output/Kerala_Fast_Eevee_LOD_540p.png`. |
| Cycles house detail | v1.4 frozen, 960×540, 32 samples | PASS | 80.5 s | `output/Kerala_House_Detail_540p.png`. |

## Hardware/backend availability

- **Cycles CPU:** available and used for the hero.
- **Cycles CUDA / OptiX:** no NVIDIA device; preferences expose CPU only.
- **Cycles HIP:** no AMD GPU; CPU only.
- **Cycles oneAPI:** no Intel GPU; CPU only.
- **Cycles Metal:** not available on Linux / this Blender build.
- **Eevee Next:** available through Mesa llvmpipe software OpenGL, but full-density scene exceeded RAM. Reduced LOD is being tested separately.
- **Workbench:** available through software OpenGL; fast only as a simplified clay proxy.
- **Vulkan backend:** Blender 4.2 workflow here does not provide a production Vulkan renderer; no claim made.

## External / distributed routes investigated

- **LuxCoreRender:** `pyluxcore==2.11.2` installed and imported successfully (TBB/OIDN libraries loaded). A minimal `RenderConfig` probe failed with the attempted API setup, and **no full Blender-to-LuxCore translation of this scene was validated**. It is not a delivered render of this scene.
- **appleseed:** no usable PyPI package found in this environment; not installed or claimed.
- **Octane / Redshift / V-Ray / Arnold:** proprietary licensing and/or GPU/host integration not available here; not tested.
- **GitHub Actions CPU rendering:** technically possible with the existing CI transport pattern, but no paid capacity was provisioned and no full CI render was benchmarked. For animation, use measured chunk sizes and the frozen-scene hash; do not assume more workflows create more hardware.

## Fastest honest recommendation

For this exact scene on this sandbox: **Cycles CPU with adaptive sampling + OIDN** is the reliable quality path. Eevee can be attractive on a real GPU, but here software GL plus dense instances is memory-bound. Workbench is only for simplified clay checks. The biggest speed levers are instance density, volumetrics, resolution, and samples—not pretending a GPU exists.


## Kerala photoreal v2 measured routes (Blender 4.2.23 LTS, CPU-only)

Frozen scene: `output/Kerala_Photoreal.blend`, SHA-256 `2ef97184b7efe03f790419dd7b360b512e24d9f2b860f868315aba52727c15a7`.

| Route | Settings | Result | Wall time | Notes |
|---|---|---:|---:|---|
| Cycles preview | 640×360, 12 samples, adaptive .10, OIDN, mist on | PASS | 28.180 s | Accepted composition/material preview 3; earlier previews 24.257 s / 25.830 s. |
| Cycles final hero | 1920×1080, 64 samples, adaptive .03, min 24, OIDN, mist on | PASS | 1044.869 s | Peak render memory ~1.35 GiB; receipt hashes match frozen scene. |
| Cycles house detail | 960×540, 32 samples, adaptive .03, OIDN, mist on | PASS | 122.309 s | Separate 58 mm house camera. |
| Workbench clay proxy | 960×540, vegetation/atmosphere hidden, studio cavity | PASS | 45.609 s | Composition proxy only; samples not applicable; no volume. |
| Eevee fast LOD | 480×270, v2 LOD densities, scanned canopy/understory/foothill forest hidden, no volume | KILLED | ~43.7 s | global OOM: anon-rss ~3.87 GiB; EGL_BAD_MATCH software GL. No image produced. |
| Cycles bench | 960×540, 24 samples | Not separately run for v2 | — | Preview and house-detail timings bracket this route. |
| GPU / Storm / LuxCore / BlenderKit | CUDA/OptiX/HIP/oneAPI CPU-only; Metal absent; Storm enabled but no engine enum; LuxCore import-only historical; BlenderKit binary blocked | NOT TESTED as render | — | No unavailable backend is claimed. |

Fastest usable v2 route for a full-material still remains Cycles CPU preview/LOD; Eevee software GL is not memory-safe for this scene even at 480p LOD. The final hero was rendered with Cycles CPU, not a photo backplate or external renderer.
