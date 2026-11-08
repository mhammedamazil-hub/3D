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
