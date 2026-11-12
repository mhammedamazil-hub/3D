# Five Worlds Blender v3 — reference analysis

The five generated plates in `assets/references/v6/` are **visual references only**. They are not attached to Blender materials, not packed into any `.blend`, not sampled by the builder, and not used as backplates, ground textures, reflection maps, environment maps, masks or compositor inputs. The builder never calls `bpy.data.images.load`; `scripts/audit_five_worlds_blender_v3.py` enforces zero image datablocks and zero image/environment texture nodes in each saved scene.

Reference-only analysis was completed before any v3 Blender geometry was built, following `skills/blender-skills/.claude/skills/references/reference-image-match.md` and the separate `realistic-blender-production` skill. The goal is visual convergence in composition, depth, palette and mood — not an exact pixel match.

| # | World | Reference file | Camera / horizon | Main silhouettes and depth layers | Lighting and mood | Dominant palette (quantized) |
|---:|---|---|---|---|---|---|
| 01 | Alpine Lake | `assets/references/v6/01_alpine_lake_16x9.jpg` | Eye-level wide landscape, horizon near upper-middle, calm mirror water occupying lower half. | Jagged snow mountains far, dark conifer belt mid, rocky shoreline and still water near. | Low golden-hour key from horizon, soft haze, high-detail reflections, quiet documentary realism. | `#0f110c`, `#cbc5be`, `#50565a`, `#98928d`, `#313636`, `#ecdcc7` |
| 02 | Neon Rain Alley | `assets/references/v6/02_neon_rain_alley_16x9.jpg` | Central one-point perspective at standing height, wet street converging to bright distant signage. | Tall dark facades both sides, layered signs/cables, reflective pavement, deep alley centre. | Low ambient, multicolour neon key signs, wet specular reflections, high contrast, empty noir/cyberpunk mood. | `#030708`, `#141817`, `#5d646d`, `#213034`, `#443f40`, `#a5abaa` |
| 03 | Sahara Dunes | `assets/references/v6/03_sahara_dunes_16x9.jpg` | Slightly elevated wide view, high horizon, sun near upper-right, sweeping S-curve dune foreground. | Layered dune ridges far, one dominant sunlit dune crest mid, rippled foreground sand and tiny caravan scale cue. | Warm low sun from right, long soft shadows, orange/rose gradients, dry haze. | `#613328`, `#97553c`, `#b76b44`, `#e1c4b8`, `#f7dec5`, `#ce9474` |
| 04 | Iceland Aurora | `assets/references/v6/04_iceland_aurora_16x9.jpg` | Low beach-level wide view, dark horizon, upward tilt toward aurora curtains. | Basalt cliff left, black sand foreground, foamy surf mid, glacier/mountain horizon far, aurora and stars above. | Night ambience, green/violet aurora emission, cool moon/sky fill, wet black-sand reflections. | `#0b1214`, `#3e5a64`, `#527f7d`, `#2b3d49`, `#1c292d`, `#76b79f` |
| 05 | Rainforest Temple | `assets/references/v6/05_rainforest_temple_16x9.jpg` | Eye-level symmetric path toward a mossy stone doorway, enclosed by foliage, waterfall left. | Dense canopy and vines near/above, temple gate mid, waterfall and mist left, stone path and ferns foreground. | Soft backlit canopy shafts, humid green shade, warm sun patches, ancient mossy stone. | `#14180c`, `#5d5d3a`, `#29341a`, `#868257`, `#413f25`, `#bbb388` |

## Per-scene reconstruction notes

### 01 Alpine Lake
Real mesh lake surface with animated wave/noise bump and physical reflection; one visible snow-peak mesh plus a lower distant ridge with height/slope-driven rock-to-snow shading; conifer belts and shoreline rocks scattered with Geometry Nodes; procedural Nishita sky, one low sun, soft mist ribbons and a slow dolly. No reference pixels are used.

### 02 Neon Rain Alley
Modular beveled building blocks, recessed window rows, coloured emissive text/sign geometry, pipes, cables and AC units; wet asphalt shader with procedural roughness puddles; looping streak-curve rain; transparent procedural steam; area-light bounce and subtle fog glow. The reference's one-point perspective and dark value range are preserved without embedding the image.

### 03 Sahara Dunes
A single continuous high-resolution dune mesh plus lower-LOD background ridges, all generated from seeded height functions. Procedural Wave/Noise sand ripples and height-based colour variation replace any image texture; scattered stones and wind-blown dust provide depth and motion. The camera drifts laterally without a painted backdrop.

### 04 Iceland Aurora
Hexagonal basalt prisms, displaced mountain/glacier geometry, black-sand shore, animated ocean grid and foam, emissive star geometry, and curved aurora ribbon meshes with procedural soft-edge masks and animated 4D noise. The sky is procedural; no HDRI or aurora photograph is used.

### 05 Rainforest Temple
Beveled stone gate, steps, plinths and doorway; procedural moss/erosion shader; actual curved leaf meshes, trunks, vines and ferns scattered with Geometry Nodes; waterfall mesh with animated vertical noise; mist and dust; one sun and motivated area fill. No image cards, alpha foliage textures or photo backplates.

## Visual-match status

The v3 renders are **reference-convergent 3D reconstructions**, not exact matches. Ten low-resolution proof-contact passes and one 1920×1080 single-frame proof were reviewed before freezing the scenes; the final five-scene authoring contact is `review/five_worlds_blender_v3/proof_contact_final.jpg`, and the contact sheet extracted from the delivered MP4s is `assets/references/v6/00_five_worlds_blender_v3_contact.jpg`. Remaining differences are recorded honestly in `docs/FIVE_WORLDS_BLENDER_V3.md`: CPU-only 4-sample rendering, procedural rather than scanned assets, no characters/vehicles, no audio, and simplified atmospheric volumetrics.
