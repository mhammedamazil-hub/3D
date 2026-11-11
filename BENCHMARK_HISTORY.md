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
