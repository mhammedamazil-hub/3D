# Add-on, generator, tree-library and texture tests — Kerala v3

Environment: Blender 4.2.23 LTS (`bpy` CPython 3.11), Debian 12, 2 vCPU, ~3.8 GiB RAM, no GPU.

## Procedural botanical generator: Princeton Infinigen

Source: `princeton-vl/infinigen` main snapshot, BSD-3-Clause, extracted under gitignored `vendor/sources/infinigen/infinigen-main`. Minimal dependencies installed while constraining bpy 4.2.23 / numpy 1.26.4; `procfunc` metadata pins bpy 4.2.0 and emits a compatibility warning, but Blender imports and factories ran.

| Factory | Result | Used? |
|---|---|---|
| `BananaMonocotFactory` | PASS after tuning count/droop/tear/vein material; 3 variants, ~55–62k polys each. | Yes — banana clumps near house/field. |
| `PlantBananaTreeFactory` | Generated but read as a single narrow leaf/stem in preview. | No. |
| `TreeFactory` broadleaf summer | PASS as live-instanced tree; safe preview retained foliage. | Generated/retained in library; not scattered in final because live-GN leaf collections did not survive view-layer exclusion. |
| Dense realized `TreeFactory` | FAIL — Blender mesh allocation abort / integer overflow. | No. |
| Source leaf decimation .45 | FAIL — collapsed leaves to fragments/bare branches. | No. |
| `CoconutTreeFactory` live GN | FAIL — OOM-killed during Cycles sync (~2 GB peak). | No; replaced by native detailed coconut palms. |

## Poly Haven CC0 library / CI transport

Direct Poly Haven hosts remain blocked from the sandbox; GitHub Actions run `42478934638` retrieved and prepared assets with `bpy` 4.2.23. Prepared models: jacaranda_tree LOD1, tree_small_02 LOD1, island_tree_03 LOD1, rock_face_02, boulder_01, stone_01, rock_07 (coast_rocks_01 prepared but omitted from final to control size). Textures: 4K brown_mud/red_laterite_soil_stones/clay_roof_tiles, 2K wood/plaster/bark/metal/rock/forest ground; overcast_soil_puresky 4K HDRI downsampled to 2K for packing. Potted plant CC0 assets recovered from earlier CI transport. Per-file URLs/SHA-256: `assets/quality/manifest.json` (gitignored raw) and `docs/QUALITY_ASSET_PROVENANCE_V3.json`.

## Built-in / external add-ons

v2 add-on probes remain valid: Cycles/glTF/FBX/UV/SVG enabled; Hydra Storm enabled but no Storm engine render; Improved Sapling registered but not used in v3 final (replaced by scanned/Infinigen trees); Poly Haven Assets add-on registered but downloader blocked, assets retrieved via CI; MTree cp39/GoodPie >=4.5/BlenderKit TLS/LuxCore routes unchanged and not claimed.

## Honest limits

Add-on registration is not a successful render backend. No GPU, Storm, LuxCore, BlenderKit or game-engine import is claimed. Infinigen is a generator source dependency, not a magic quality guarantee; failed factories are recorded. Final scene is native editable Blender geometry with packed textures.
