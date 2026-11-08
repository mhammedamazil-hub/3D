# v4 provenance and attribution

## User-supplied coconut asset
- Original upload: `coconut_tree_low_poly.glb.txt` → restored byte-for-byte as `assets/models/user/coconut_tree_low_poly.glb`.
- SHA-256: `348ed52f1320941ba80c49e8b2bf4c7fb7612ca6adb19c578c64db3a8a414198`.
- Title: “Coconut Tree Low poly”. Author: Pixel_Monster / ar.jethin. License: CC BY 4.0.
- Source: https://sketchfab.com/3d-models/coconut-tree-low-poly-8c5d6b661b2f4c37834d87cd187eb907
- License: https://creativecommons.org/licenses/by/4.0/
- Changes: uniform metric normalization (×0.1), material enhancement, added coconut fruit clusters, scene instancing, and a derived `output/Coconut_Tree_Scene_Ready.glb` with glTF-compatible alpha-mask materials. Uploaded trunk/frond meshes and texture atlases preserved.

## Other assets
The v4 scene builds on the frozen v3 packed blend. Existing Poly Haven / scanned texture and model provenance remains in v3 docs (`docs/PROVENANCE*`, `docs/COCONUT_TREE_CREDITS.md`, asset manifests). No new external photo backplate was introduced.

## Generated references
`output/References/Kerala_Paddy_Reference.png` and `output/References/Coconut_Palm_Reference.png` are AI-generated look-development images selected by the user. They are not used as scene backplates or textures. See `output/References/README.md`.

## Reproducibility
- Convert upload: `python3 scripts/convert_coconut_upload.py`
- Build/export coconut asset: `sh scripts/blender-py scripts/build_coconut_asset_v4.py`
- Verify GLB round-trip: `sh scripts/blender-py scripts/verify_coconut_glb_v4.py`
- Build v4 scene: `sh scripts/blender-py scripts/build_kerala_v4.py`
- Render: `sh scripts/blender-py scripts/render_kerala_v4.py --camera ... --width ... --height ... --samples ... --out ...`
- Verify scene/renders: `sh scripts/blender-py scripts/verify_kerala_v4.py`
