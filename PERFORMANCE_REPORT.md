# PERFORMANCE REPORT — PROJECT VOXELCORE

Methodology: `voxelcore/build/voxelcore_bench` (committed CSV format), this machine: Debian 12, gcc 12.2.0, `-O3 -std=c++23`, no GPU load during runs. Numbers are real, single-run unless noted; rerun-to-verify is encouraged. Horizon comparison numbers are **not** measured here (see HORIZON_PERFORMANCE_BASELINE.md).

## 2026-11-11 baseline (run 1)

| Benchmark | Iterations | per op |
|---|---|---|
| packed_storage_set_4096 | 2000 | 5.61 µs |
| packed_storage_get_4096 | 2000 | 10.05 µs |
| paletted_section_set_fill | 500 | 61.97 µs |
| terrain_gen_chunk | 20 | 176.5 µs |
| greedy_mesh_generated_chunk | 20 | 2300 µs → 2044 µs after E4 (template reader) |
| job_system_parallel_for_1M | 20 | 25,949 µs → 24,468 µs |

World-level: 9-chunk (r=1) world gen 1.5 ms; greedy mesh 20.1 ms (2.23 ms/chunk avg); 11,636 naive visible faces merged to 1,296 quads (11.1%); `faceArea == naiveFaces` verified; LOD level-2 tile bake 0.8 ms; headless 640×360 software frame 32–42 ms end-to-end.

## Regressions / anomalies

- `greedy_mesh_generated_chunk` is dominated by world-reader hash lookups (see OPTIMIZATION_CATALOG E5) — known, backlogged, not hidden.
- Software-renderer color interpolation is affine in barycentric weights — acceptable for verification, rejected for shipping (ADR-014).

## Rules

Every optimization entering the tree must append its before/after numbers here (and BENCHMARK_HISTORY.md), or state why it cannot be measured yet.
