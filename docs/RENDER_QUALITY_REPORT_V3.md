# Kerala v3 render route report

Environment: Blender 4.2.23 LTS `bpy`, Debian 12, 2 vCPU, ~3.8 GiB RAM, no GPU. Cycles CPU is the only claimed beauty route.

## Measured routes

| Route | Settings | Result |
|---|---|---|
| v3 hero preview | 640×360, 16 samples, OIDN | PASS ~25–26 s after memory reductions; used for lookdev. |
| v3 hero final | 1600×900, 64 adaptive samples, OIDN | PASS 429.287 s; receipt hashes match. | |
| v3 house detail | 960×540, 32 samples, OIDN | PASS 83.055 s; receipt hashes match. | |
| Dense realized Infinigen tree | realize=True, high density | FAIL — Blender mesh allocation abort. |
| Infinigen coconut GN | live geometry nodes | FAIL — OOM during Cycles sync. |
| v3 initial dense forest | 1072 tree instances + 91k rice | FAIL — OOM-killed during preview; reduced instances/rice and removed decimated leaf variants. |

## Memory/quality decisions

- Kept Infinigen broadleaf branch/leaf instancing live; did not decimate leaf source meshes after a .45 ratio collapsed foliage.
- Used scanned tree LOD1 meshes with light hero decimation and collection instances; background forest uses original scanned meshes at reduced counts to avoid bare decimated leaf cards.
- Recompressed oversized packed scans (4K surface maps to 2K JPEG, tree/rock scans to 1K, HDRI to 2K) to keep the delivered blend near 97 MB.
- Reduced ridge mesh resolution and mist volume bounces while retaining editable displacement and noise-driven density.

No GPU, Storm, LuxCore, BlenderKit or Eevee beauty render is claimed for v3.

- 2048×1152/96 hero was OOM-killed at sample 94/96 during denoise/composite; final route reduced to 1600×900 with RGB_ALBEDO/FAST OIDN prefilter.

- 1600×900/96 also OOM-killed near sample 92; reduced packed texture targets (surface 1K, tree/rock 512, HDRI 1K) and forest counts, final route 1600×900/64.
