# v4 research and realism decisions

## Botanical / scene references
The uploaded asset is titled “Coconut Tree Low poly” and its leaf material is internally named `date_palm_leaf`. It was accepted because the visible silhouette matches a plausible cultivated coconut palm: single slender ring-scarred trunk, pinnate crown, long recurved fronds, and clustered fruit added below the crown. Botanical checks were visual/morphological, not based on the material name.

Sources consulted:
- World Flora Online, *Cocos nucifera*: stems ~20–30 m, ringed leaf scars, swollen base; pinnate leaves 4–7 m with two-ranked stiff pinnae; fruits green/yellow/bronzy-red when immature, brown when mature. https://www.worldfloraonline.org/taxon/wfo-0000903570
- Springer coconut morphology chapter: crown often 25–35 paripinnate leaves; trunk ~30–50 cm diameter; leaves 4–8 m; segments ~0.5–1 m. https://link.springer.com/chapter/10.1007/978-1-59259-887-8_3
- NTBG *Cocos nucifera*: single trunk 20–30 m, grey ringed bark, pinnate leaves 4–6 m, linear-lanceolate recurved bright-green leaflets, axillary inflorescences. https://ntbg.org/database/plants/detail/cocos-nucifera

The uploaded palm normalizes to ~15.6 m, shorter than a wild maximum but plausible for a cultivated/younger coconut in a house compound. Fruit clusters were added because the upload had none.

## Material / rendering references
- Thin foliage is better served by a restrained backface/translucent contribution than volume SSS: https://devtalk.blender.org/t/diffuse-translucency-way-too-difficult-to-set-up-in-cycles/807
- Alpha cutout foliage needs explicit alpha clipping/mask behavior: https://www.katsbits.com/codex/transparency-cycles/
- glTF export requires alpha on a Principled-compatible graph; Cycles-only translucent mixes do not export: https://discourse.threejs.org/t/how-do-i-use-transparency-in-gltf-exports/23680

Implementation: the Blender scene keeps the uploaded leaf atlas and adds a small Translucent BSDF mix for Cycles. The exported scene-ready GLB swaps to Principled-only materials with a `GREATER_THAN` alpha threshold so glTF `alphaMode` is `MASK` (cutoff .494), verified by reimport.

## Generated image references
Two look-development images were generated and the user selected option 1 for each. They are disclosed in `output/References/README.md` as AI-generated art direction, not photographs, backplates, projection textures, or proof of render quality. The final scene is native editable Blender geometry rendered in Cycles.

## Honest limitations
This is still a real-time-friendly low-poly/alpha-card asset, not a photogrammetry coconut. Remaining CG tells include repeated instanced crowns, simplified leaf cards at distance, procedural rice repetition, and artist-directed mist. The pass prioritizes correct scale, believable silhouette, open-water paddy structure, wet ground, and a clean house view over claiming photographic capture.
