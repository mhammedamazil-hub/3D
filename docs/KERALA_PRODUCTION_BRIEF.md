# Production brief — Monsoon Light, Kerala

## User request
Build an actual editable Blender landscape inspired by the two supplied paddy-field references, improve the composition, place an old Kerala house at the end of the path, add mountains, review the 94-skill library, and investigate fast rendering routes.

## Decisions
- **Hero deliverable:** editable packed `.blend`, finished PNG still, reproducible Python source, render-speed report.
- **Default canvas:** 1920 × 1080, 16:9; no animation was requested.
- **Style:** naturalistic cinematic realism, fresh monsoon greenery, warm old-house materials, humid atmospheric depth; not a literal photograph reconstruction.
- **Architecture:** a modest traditional Kerala tharavad-inspired house: broad terracotta-tiled roof, deep eaves, timber veranda, carved shutters, weathered lime plaster, laterite plinth. Not a palace or temple.
- **Compute:** local 2-vCPU / 3.85-GiB sandbox, no GPU. No paid resources. Test supported local backends and report unavailable routes honestly.
- **Skills:** review every one of the 94 actual SKILL.md documents. Apply relevant production guidance; use unrelated genre/style/engine skills as explicit exclusion, readability, or compatibility checks rather than corrupting the realistic scene. Record the distinction.

## Reference analysis (before modeling)
### image-2.jpeg — primary composition
- Portrait view, eye-level camera; a broad foreground footpath occupies the lower center.
- Path narrows rapidly, bends right in the middle distance, then returns toward a small central destination.
- Dense green fields flank the route; a continuous tropical tree belt closes the field edge.
- Layered blue/teal mountains sit behind the trees; a distinct central peak and softer side ridges.
- Broken bright clouds occupy roughly the upper third; diffuse daylight, saturated greens, slightly cool shadows.
- Preserve: strong leading line, immersive foreground, field/tree/mountain depth layers, cloudy sky.
- Change: wider cinematic frame, cleaner house destination, more legible architecture, flooded-row detail, less crushed green shadows.

### image-1.jpeg — material and planting reference
- Landscape view across flooded young rice; regular transplant rows and reflective water are clearly visible.
- Narrow grassy bund recedes toward the tree line; tiny distant buildings give scale.
- Broad misty mountains and bright upper-right sky; low contrast in the far layer.
- Preserve: paddy water, row rhythm, low seedlings, grassy bunds, palms, distant haze.
- Change: stronger foreground/midground separation and a larger old-house focal point.
- Provenance: user-supplied reference files; image-1 carries a Shutterstock watermark/ID. They are analysis references only, not rendered backplates or redistributed texture assets.

## Composition plan
- Camera around 2.5 m above the paddies, 38–42 mm full-frame lens; stable verticals, deep focus.
- Foreground: individually readable curved rice blades, shallow water, reflected clouds, wet earth and grass on the bund.
- Middle: curved path terminates at the house slightly right of center; palms and banana leaves frame rather than hide it.
- Background: dense broadleaf/palm belt, then three real mesh ridge layers with progressively cooler atmospheric perspective.
- Key light: fixed morning sun from upper right/back; soft sky fill keeps the veranda readable.
- Sky: procedural shader sky/clouds, explicitly disclosed as a sky shader, not volumetric cloud geometry. D mist is a bounded participating medium away from the camera and paddies.

## Acceptance checklist
- [x] True 3D terrain, paddies, path, vegetation, mountains, and house; no photo backplate.
- [x] House visible at path end; roof, veranda, door, windows, plinth and weathering readable.
- [x] Water has IOR ~1.333, real reflection/refraction, shallow closed volume and mud bottom.
- [x] Rice/palms/broadleaf plants have dimensional geometry and varied instances.
- [x] Opening composition visually reviewed; native-resolution house and foreground crops inspected.
- [x] Named collections, node materials, metric units, seeded source, packed assets.
- [x] Frozen `.blend` SHA-256; final still rendered from those exact bytes.
- [x] Backend claims backed by actual images/timings or explicit unavailable status.
- [x] Technical validation separate from subjective artistic approval.
