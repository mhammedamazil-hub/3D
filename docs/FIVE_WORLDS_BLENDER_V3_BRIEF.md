# Five Worlds Blender v3 — pure procedural 3D production brief

## User correction

The v1 WebGL capture and v2 Blender/Cycles backplate scenes are **superseded**. The user requires every scene to be recreated as an actual 3D world with `bpy`; the generated images may be used **as visual references only** and must not exist inside the `.blend` files. The work must be guided by the cloned `skills/blender-skills/.claude/skills` collection of **94 pinned `SKILL.md` documents**.

## Implementation status

All six pipeline pieces named below now exist: the `bpy` builder, shard renderer, standalone no-image auditor, finalizer, independent verifier and 15-shard CI workflow. Five production `.blend` files were rebuilt at 1920×1080/30 fps/300 frames and independently audited with **zero image datablocks, zero image-texture nodes, zero environment-texture nodes, zero linked libraries and zero movieclips** across all five scenes. Ten low-resolution look-development proof passes and a 1080p single-frame proof were reviewed. The frozen-scene manifest is `docs/FIVE_WORLDS_BLENDER_V3_MANIFEST.json`. CI run `43064656588` produced the 1,500 final frames, five MP4s, 50 s montage, contact sheet, receipt and validation, and committed them back at `4bf7b7324932d8dce33ad1ee84de7a72ff19bb43`; CI validation, CI blend audit and the post-pull local verifier all passed.

## Locked acceptance contract

| Requirement | Decision |
|---|---|
| Scene source | Five editable, reproducible Blender 4.2.23 `.blend` scenes generated entirely by `bpy` scripts. |
| Image policy | `bpy.data.images` must be empty. No `ShaderNodeTexImage`, no `ShaderNodeTexEnvironment`, no packed/generated image masks, no HDRI, no photo backplate, no image-based ground/reflection texture. |
| Reference policy | `assets/references/v6/*.jpg` remain external visual guides for composition, palette, silhouette and lighting only. They are hashed in the manifest and analyzed in `docs/FIVE_WORLDS_BLENDER_V3_REFERENCE_ANALYSIS.md`, never loaded by `bpy`. |
| World construction | Real 3D geometry, procedural shader-node materials, physical lights, atmospheric geometry, particles and camera animation. 1 Blender unit = 1 metre. |
| Skills | All 94 pinned `.claude/skills/*/SKILL.md` files rechecked with SHA-256; relevant skills applied, game-engine/backend skills as compatibility checks, character/sim disciplines N/A, incompatible styles as QA/exclusion lenses. |
| Deliverables | Five 1920×1080, 30 fps, 300-frame, 10.000 s H.264/yuv420p MP4s plus one 50.000 s montage; contact sheet; frozen-scene manifest; CI receipt; CI validation; local validation; per-scene `.blend` audit. |
| Render | Cycles CPU, 4 samples, adaptive sampling, OpenImageDenoise `RGB_ALBEDO_NORMAL`, AgX Medium High Contrast, 15 shards × 100 frames. |
| Reproduction | `scripts/build_five_worlds_blender_v3.py`, `scripts/render_five_worlds_blender_v3.py`, `scripts/finalize_five_worlds_blender_v3.py`, `scripts/verify_five_worlds_blender_v3.py`, `scripts/audit_five_worlds_blender_v3.py`, `.github/workflows/render-five-worlds-blender-v3.yml`. |
| Out of scope | Audio, GPU rendering, purchased/licensed external assets, characters, rigs, cloth/hair caches, game-engine exports, exact pixel match to generated references. |

## Production loop

1. Resource audit and branch check.
2. Reference analysis before Blender operations.
3. 94-skill review and routing.
4. Blockout, silhouette and camera match.
5. Procedural 3D geometry, materials, lighting and animation.
6. Low-resolution opening/midpoint/ending proof contact.
7. Freeze five `.blend` files, hash them, render 15 independent shards.
8. Assemble, encode, validate full decode and frame distinctness.
9. Independent local no-image audit and delivery verification.
10. Present only the final v3 Blender MP4s.

## Honest status vocabulary

- **TECHNICAL:** pass/fail from scripted audits.
- **VISUAL:** reviewed with limitations; procedural 3D reconstruction is not a pixel match to the generated references.
- **DELIVERY:** preview only / rendering / final verified.

This brief follows the separate `skills/realistic-blender-production/SKILL.md` production loop while the 94-skill matrix records the cloned specialist library decisions.
