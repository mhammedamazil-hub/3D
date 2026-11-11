# BENCHMARK HISTORY — PROJECT VOXELCORE

## 2026-11-11 — run 1 (initial baseline, commit pending)
```
packed_storage_set_4096,2000,11.223,5.612
packed_storage_get_4096,2000,20.091,10.045
paletted_section_set_fill,500,30.987,61.973
terrain_gen_chunk,20,3.531,176.535
greedy_mesh_generated_chunk,20,46.001,2300.045
job_system_parallel_for_1M,20,518.986,25949.278
```
## 2026-11-11 — run 2 (after E4 template-functor reader)
```
packed_storage_set_4096,2000,12.905,6.453
packed_storage_get_4096,2000,20.466,10.233
paletted_section_set_fill,500,33.302,66.603
terrain_gen_chunk,20,3.472,173.620
greedy_mesh_generated_chunk,20,40.884,2044.218
job_system_parallel_for_1M,20,489.365,24468.254
```
Notes: container noise ±5–10% on this shared machine; E4 gain on meshing ≈ 11% (real but small); E5 (thread-local chunk cache) is the next lever.
## 2026-11-11 — run 3 (after E5 cached block reader)
```
greedy_mesh_generated_chunk: 2044 -> 1349 us (-34%)
job_system_parallel_for_1M: 24468 -> 23657 us
9-chunk mesh: 20.1 -> 9.8 ms
```
## 2026-11-11 — run 4 (software renderer backface culling)
Headless 640x360 frame: ~32 -> ~22 ms (opaque quads only).
## 2026-11-11 — run 5 (after E6 side-bucket partition, commit pending)
```
greedy_mesh_generated_chunk,20,27.398,1369.885
greedy_mesh_generated_chunk,20,27.415,1370.735
greedy_mesh_generated_chunk,20,27.410,1370.517
```
Notes: E6 partition (O(n) cursor scatter, one temp vector) costs ≈ +0.8% vs 1359 us pre-E6.
An earlier `std::stable_sort` implementation measured +7.5% (1460-1514 us) and was replaced.
ASan/UBSan: 193,870 checks, 0 failures.
## 2026-11-11 — run 6 (stage 9 M1 light, boundary-seeded flood)
```
light_volume_16x64x16_flat,100,27.539,275.391   (best of 3; naive version: 1,110)
greedy_mesh_generated_chunk,20,28.428,1421.385   (unchanged; light not yet wired into mesher)
```
ASan/UBSan: 194,168 checks, 0 failures.
