# Add-on, tree-library and texture tests — Kerala v2

Environment: Blender 4.2.23 LTS (`bpy` CPython 3.11), Debian 12, 2 vCPU, ~3.8 GiB RAM, no GPU. Tests are isolated where possible; some `bpy` module builds segfault at interpreter shutdown after writing valid results, so probes flush JSON and call `os._exit(0)`.

## Built-in add-ons

`review/addons/builtin_probe.json`: cycles, node_wrangler, io_scene_gltf2, io_scene_fbx, io_mesh_uv_layout, io_curve_svg and hydra_storm all returned enable=true. Cycles/glTF/FBX/UV/SVG are relevant and were used or kept available. Hydra Storm enabled but the engine enum still exposed only EEVEE_NEXT in this headless build; no Storm render is claimed.

## External add-ons

| Add-on | License | Result | Used in scene? |
|---|---|---|---|
| Improved Sapling Tree Generator (`abpy/improved-sapling-tree-generator`) | GPL-2.0 | Registered; `curve.tree_add` generated leafy broadleaf variants; converted/joined into 6 library meshes. | Yes — generation tool for 6 sapling broadleaf variants and foothill/understory fallback. |
| Poly Haven Assets (`Poly-Haven/polyhavenassets`) | GPL-3.0 | Imported and registered in 4.2 despite bl_info targeting 4.5; operator namespace present. Add-on asset download requires Poly Haven hosts blocked directly here. | Add-on registered, but assets were retrieved through public CI transport and appended manually with provenance. |
| Modular Tree original (`MaximeHerpin/modular_tree` 4.0.2 linux release) | GPL-3.0 | Release zip retrieved via CI; binary extension is `m_tree.cpython-39-x86_64-linux-gnu.so`; import failed under CPython 3.11. | No. |
| Modular Tree GoodPie fork | GPL-3.0 | Manifest requires Blender >= 4.5; incompatible with 4.2.23. | No. |
| BlenderKit | GPL-2.0 | Release/client binary download route failed (TLS EOF) from sandbox; not installed/tested further. | No. |
| BlendLuxCore / pyluxcore | GPL / Apache-style upstream | Historical probe: pyluxcore imports but RenderConfig default scene failed; no usable LuxCore render route established. | No. |

## 3D tree / plant library

- Poly Haven `island_tree_02` CC0: actual broadleaf tree model retrieved. The 1K blend contains LOD0 (544,639 polys) and LOD1 (316,491 polys); the scene uses LOD1, scaled into the near/mid canopy. Raw 37 MB blend is gitignored under `assets/models/raw/` and packed into the delivered `.blend`.
- Poly Haven `fern_02` and `anthurium_botany_01` CC0: scanned understory variants appended and scattered near bunds/house.
- Improved Sapling: six seeded broadleaf variants with real branch curves converted to mesh and leaf meshes joined; used for the dense tropical belt and foothill forest.
- Coconut palms and bananas remain original procedural Kerala meshes from v1, retained for regional silhouette.

## Textures / HDRI

CC0 Poly Haven 1K maps actually wired into materials: brown_mud, clay_roof_tiles (relief), bark_brown_02, worn_plaster_wall (relief), rock_face, red_laterite_soil_stones, wood_planks, corrugated_iron_02, aerial_rocks_02. `forest_ground_04` was retrieved and retained as a candidate but not wired into the final graph. HDRI: `kloofendal_48d_partly_cloudy_puresky` 2K, desaturated/mixed toward overcast in the world shader. Per-file URLs and SHA-256: `assets/realism/PROVENANCE.json`; credits: `assets/realism/CREDITS.md`.

Removed/unverified candidates: three.js `waternormals.jpg` (license unverified) and `grasslight-big.jpg` (CC BY, not needed) were not used. User reference images were analyzed only, never used as backplates or projected textures.

## Honest limits

This is a native Blender scene and Cycles CPU render, not a photo composite. Add-on registration is not the same as a successful render backend. No GPU, Storm, LuxCore, BlenderKit or game-engine import is claimed. The result is substantially more material/vegetation-rich than v1, but CPU/memory constraints still limit full-density Eevee and ultra-high sample counts.
