# Kerala v4 — uploaded coconut realism pass

Revision: `kerala-v4.0-user-coconut`. Frozen comparison baseline remains v3 `output/Kerala_Quality.blend` (`c467e7f`).

## Deliverables
- `output/Kerala_Coconut_Realism.blend` — editable packed Cycles scene, 862 objects, 80 packed images.
- `output/Kerala_Coconut_Realism_900p.png` — 1600×900, Cycles CPU, 64 max samples, adaptive .015, OIDN.
- `output/Kerala_Coconut_Realism_House_Detail_540p.png` — 960×540, 32 samples.
- `output/Kerala_Coconut_Realism_Coconut_Detail.png` — 900×1100, 32 samples, uploaded coconut crown/trunk.
- `output/Coconut_Tree_Scene_Ready.glb` — metric, attributed, alpha-clip foliage, fruit clusters added.
- `output/References/` — two user-selected AI-generated look-development references, disclosed as non-photographic.

## What changed from v3
1. **User coconut model is actually used.** Converted `coconut_tree_low_poly.glb.txt` byte-for-byte to `.glb`, imported, normalized ×0.1 to ~15.6 m, and instanced 26 times. Procedural v3 palms were removed. Trunk/frond meshes and packed atlases are preserved; materials were enhanced and small coconut clusters added.
2. **Younger flooded rice.** Rice clumps rebuilt shorter/sparser (5–7 blades, ~0.24–0.46 m) so row structure and open water read more clearly; 79,917 row instances retained.
3. **Wet earthen path and bunds.** Replaced blocky/brick-like path remnants with a narrow displaced mud path, low continuous earthen bunds, subtle puddles, bund grass, and a foreground timber drain crossing. Floating laterite chips removed.
4. **House weathering.** Removed solid green damp skirts; clustered roof lichen/soot by world position and noise; added subtle lower-wall damp darkening.
5. **Ghats and atmosphere.** Lowered ridge meshes, cooled forest/rock tint, added low valley haze and adjusted mist banks for a more humid overcast separation.
6. **Critical scene hygiene fix.** Source scan libraries were rendering at the origin in early v4 previews. Final build excludes `COL_AssetLibrary` and all `LIB_*` source collections from the view layer; only collection instances render. Large rock-face/boulder scans inappropriate for paddy fields were removed; island-tree scans replaced with smaller forest trees.

## Verification
`sh scripts/blender-py scripts/verify_kerala_v4.py` → `docs/KERALA_VALIDATION_V4.json` PASS. Checks include render receipt blend-hash matches, ≥20 uploaded coconut instances, packed images, excluded source libraries, GLB round-trip alpha MASK, and reference disclosure.
