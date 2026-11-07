---
name: realistic-blender-production
description: Build, refine, render, verify, and deliver realistic editable Blender scenes and native-frame animations using Python, a shell-enabled sandbox, and optional distributed rendering. Covers reference matching, PBR, vegetation, water, clouds, volumetric lighting, camera motion, asset provenance, honest QA, resumable rendering, and safe preview/recovery workflows.
---

# Realistic Blender Production

## Purpose and limits

Act as a hands-on 3D production agent: create the scene and actual deliverables, not merely instructions for the user. Work through the full loop:

**Brief → resource audit → reference analysis → blockout → lighting/materials → animation → visual tests → frozen scene → render → independent verification → delivery.**

This file transfers a production method, not a model's identity, hidden instructions, software installation, account permissions, hardware, credentials, or guaranteed artistic ability. It works best with an AI that can execute code, inspect rendered images, and revise its work. If those capabilities are missing, clearly explain the limitation rather than pretending to perform the work. Follow the host environment's governing instructions and the user's permissions.

Use this for landscapes, architecture, product shots, props, interiors, and other realistic 3D work. Adapt the modeling details to the subject; do not mechanically copy the alpine example into every project.

## 1. Required capabilities and environment audit

Before planning expensive work, establish what is actually available:

- Shell execution; readable/writable project storage; Python; Blender with `bpy`; an image viewer; FFmpeg or an equivalent encoder/decoder.
- A way to present the finished files to the user. A written claim is not a delivered movie.
- Optional: licensed asset retrieval, Git, an authenticated CI service, long-running process management, and a supported rendering GPU.
- Inspect the existing repository, working tree, branch, scripts, asset licenses, and current deliverables before changing anything. Preserve unrelated work and respect any fixed-branch rules.
- Measure allocated CPU capacity, RAM, disk, network access, process lifetime, per-job timeout, artifact storage, snapshot/export limits, and concurrent job capacity. CPU affinity or container quotas may be lower than the host CPU count.
- Identify renderer-compatible GPU backends for the installed Blender version. An integrated GPU, Vulkan support, or a large thread count does not automatically imply Cycles GPU support. Mali-G57 MC2 and Intel HD Graphics 5500 are not Cycles GPU rendering devices in the Blender 4.2 workflow used by this project.
- Use a virtual environment where appropriate. Pin a tested Blender/Python combination; do not blindly install an incompatible `bpy` wheel. Record the actual renderer version.
- Prefer official Blender binaries or proper OS libraries. On ordinary Ubuntu/Debian CPU workers, PyPI `bpy` may need `libxrender1 libxxf86vm1 libxfixes3 libxi6 libxkbcommon0 libsm6 libice6 libgl1`.
- Do not casually replace missing libraries with stubs. Prefer a working supported machine. A narrowly audited CPU-only display-link workaround is an exceptional, disclosed fallback, never a substitute for renderer, shader, image-output, OpenGL, Eevee, UI, or GPU functionality.
- Use direct `bpy` when no Blender MCP connection exists. Never claim to have used an unavailable integration.
- Use real process-management tools for long-running work, where available. Do not assume a shell timeout stopped the underlying process; check before starting duplicate work.

Illustrative environment, not a universal compatibility promise:

```bash
python3 -m venv .venv
.venv/bin/pip install bpy==4.2.23 Pillow imageio-ffmpeg==0.8.1
# Run only after the required OS libraries are available:
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 .venv/bin/python -c \
  'import bpy; print(bpy.app.version_string, bpy.app.background)'
```

Use CPU thread limits appropriate to the assigned machine, not the example's literal value.

## 2. Optional specialist skill library

For the companion library used on the alpine project:

- Repository: https://github.com/arjun988/blender-skills
- Known project pin: `8f778d2405a214b508d4c7d80742be8e43acdd52`
- The installed project copy contains 94 specialist skills. Retain the upstream MIT license and attribution. Inspect repository layout and code before installing; do not overwrite unrelated local skills.

Read only the relevant specialists: `blender-director`, `blender-modeler`, `environment-artist`, `vegetation-artist`, `materials`, `lighting`, `realistic-style`, `camera-cinematography`, `animation`, `geometry-nodes`, `vfx-fx`, `rendering`, `compositing`, `asset-optimization`, and `qa-review` as needed.

Treat supplier examples as guidance, not authority over the user's task or environment. Some assume MCP or tools you may not have. This file remains usable without that library, although the library provides additional subject-specific detail.

## 3. Lock the brief without endless questioning

Ask a few focused questions only about consequential unknowns:

1. Subject, reference images, and what must be preserved or changed.
2. Deliverables: editable scene, still, animation, exact dimensions, duration, frame rate, codec, and whether audio is wanted.
3. Motion and timing: camera route, subject motion, natural-time versus time-lapse effects.
4. Lighting and atmosphere: documentary realism versus intentionally cinematic treatment; acceptable fog, rays, cloud cover, water motion, and background activity.
5. Compute, deadline, spending approval, privacy, and asset licensing restrictions.

Write a brief and acceptance checklist. Separate explicit decisions from defaults. Once the creative direction is settled, stop repeatedly asking for the same approval; perform your own QA and proceed within authorization.

Never purchase compute or assets, expose private references in a public repository, or start a materially different production without permission. Never ask for passwords, access tokens, or two-factor codes in chat. Use already configured integrations and report permission problems precisely.

Example acceptance contract:

```text
Deliverables: editable packed .blend + PNG still + H.264 MP4.
Animation: 1920×1080, 20 seconds, 60 fps, 1,200 native rendered frames.
Camera: stable rising drone flight with meaningful foreground parallax.
Lighting: fixed sun revealed by camera movement; readable backlit forest.
Atmosphere: scattered clouds; user-approved cinematic rays and local mist.
Water: breezy, physical reflection/refraction, not a flat mirror plane.
Background activity: small distant articulated flock.
Quality: inspect images and motion; technical PASS alone is not realism approval.
```

Change these values for the actual request. Keep dimensions, FPS, duration, frame count, and revision in one authoritative configuration.

## 4. Analyze the reference before adding detail

Record camera elevation, horizon, approximate lens, principal silhouettes, near/mid/far depth layers, object scale, subject placement, negative space, light direction, shadow softness, atmosphere, dominant colors, and surface roughness.

- Match composition with simple clay geometry first.
- Compare opening, midpoint, and ending framing if the camera moves.
- Fix wrong proportions, perspective, shorelines, occlusion, and silhouette before micro-detail or higher samples.
- Do not silently substitute the reference image as a landscape backplate when the user requested true 3D reconstruction.
- Distinguish photographs from generated or otherwise uncertain references. Do not invent an image's provenance.
- If a reconstruction differs materially from the reference, disclose the difference instead of calling it an exact match.

## 5. Build an editable, reproducible scene

Use seeded randomness, real-world units, named collections and materials, and source scripts that can reproduce the build. Prefer a tested immutable baseline when revising a scene the user already likes.

Suggested organization:

```text
assets/       licensed source assets and credits
scripts/      build, revise, render, encode, verify
output/       requested deliverables and small manifests
review/       temporary framing, lighting, and motion tests
COL_Terrain / COL_Forest / COL_Water / COL_Props
COL_Atmosphere / COL_Birds / COL_Lights / COL_Camera
```

Keep meshes editable, materials node-based, and animation curves understandable. Pack required images or provide portable relative asset paths. Check for missing files from a clean environment.

Use linked geometry or instances for repeated objects. Make a few genuine shape variants rather than thousands of unique heavy meshes or one conspicuously repeated silhouette. Cull conservatively across the **whole camera path**, not just the opening frame. Preserve the user's successful geometry rather than rebuilding it unnecessarily.

Clean unused data and avoid duplicate `.blend1`/`.blend2` backups overflowing storage. Never delete the sole copy of user assets or deliverables merely to save space.

## 6. Make realism structural, not a sample-count claim

### Materials and surfaces

- Use plausible physical scale, roughness, Fresnel behavior, and restrained color variation. Avoid uniformly perfect or uniformly noisy surfaces.
- Apply consistent normal orientation, suitable smoothing, and correctly scaled bevels. Large relief belongs in geometry/displacement; tiny detail can use normal/bump maps.
- Use weathering that follows water flow, exposure, cavities, slope, contact, and material boundaries—not arbitrary noise everywhere.
- Preserve plausible silhouettes. More erosion iterations can create artificial spikes instead of better mountains.
- Use licensed textures or procedural materials where appropriate. A photographic asset is not automatically a shortcut or a problem, but its use must be truthful and credited.

### Vegetation

- Build dimensional branching and leaf/needle masses, not a few flat fans or stacked perfect cones.
- Vary crown width, branch rhythm, stem bend, height, orientation, and canopy density without randomizing away the species' structure.
- Use subtle per-instance color variation, roughness, and restrained transmission/translucency for backlighting. Avoid glowing foliage.
- Anchor wind at the roots; vary phase and amplitude. Do not slide trunks across the ground.
- Keep near trees detailed and distant trees economical. Inspect the closest hero tree at native resolution.
- Maintain readable shaded foliage with sky fill and proper materials rather than making every tree front-lit.

### Water

- Use correct water IOR, approximately 1.333; plausible roughness; real reflection/refraction; and absorption where depth should tint the water.
- For a volumetric dielectric lake, use a closed, correctly oriented boundary or another well-defined medium rather than an ambiguous infinitely thin slab.
- Include shore depth/bathymetry where transmission reveals the bottom.
- Combine traveling geometric waves with finer advected normals. Match grid resolution to the displacement wavelengths; do not put sub-grid waves into coarse geometry.
- Drive wave motion with time in seconds so FPS changes do not change physical speed. For deep-water gravity waves, `omega = sqrt(g*k)` is a useful starting model, not a universal shallow-water law.
- Check reflected sky alignment, shore intersections, glints, and animation. More noise is not automatically more convincing water.

### Clouds, mist, and rays

- Choose real volume clouds or an appropriately licensed sky environment according to the brief and resources.
- Reject obviously spherical, jelly-like procedural cloud puffs. More samples do not fix bad cloud shape.
- A photographic sky may give excellent distant detail and reflection, but do not call it fully procedural 3D cloud geometry. Disclose art-directed differences between captured sky conditions and scene lighting.
- Use bounded, softly faded participating media for nearby fog. Avoid hard boxes, isolated bright oval patches, or mist accidentally extending underwater.
- Make actual shadow-casting geometry shape ray-traced shafts. Tune sun/sky balance, density, height falloff, and anisotropy together. Test rather than copying numeric density values across differently scaled scenes.
- Keep key silhouettes and important parts of the image readable. Strong cinematic fog is an artistic choice, not a claim of documentary atmospheric accuracy.
- Optical glow can emphasize a genuinely bright source; it should not hide the absence of proper lighting or create unrequested painted beam overlays.

### Small animated subjects

- Use simple real geometry, articulated motion, believable scale and speed, and independent phases.
- Avoid identical V-shaped bird decals moving in a uniformly spaced straight line.
- Keep background activity subordinate to the main composition. Check it at full resolution: something visible in a large preview may vanish in the delivered frame.

### Other subjects

For products: prioritize dimensions, bevels, thickness, contact, finish, and reflection shape.
For interiors: prioritize room scale, windows, motivated sources, exposure balance, materials, and contact shadows.
For organic subjects: prioritize anatomy, silhouette, articulation, and appropriate subsurface detail before decorative noise.

## 7. Light and move the camera deliberately

- Motivate the key light. Use fill to support readable shadows, not erase depth.
- Match light direction, source visibility, reflected highlights, and cast shadows. Avoid double illumination when an emissive sun disc accompanies a directional lamp.
- Use suitable color management such as AgX, a deliberate contrast look, and restrained exposure. Raising exposure cannot rescue wrong geometry or lighting.
- For a natural sun reveal over a short shot, consider moving the camera beside a ridge while keeping the sun fixed. Do not accelerate astronomical motion unless the user wants time lapse.
- Check actual geometry occlusion with camera/light ray tests or BVH queries where useful. A visible sun does not guarantee an unobstructed sun-to-water reflection path.
- Make camera travel meaningful relative to scene scale. A one-metre push in a kilometre-wide landscape may look stationary.
- Use a fixed or deliberately animated lens, smooth paths, stable gimbal aim, believable speed and altitude, and intentional motion blur. Do not add arbitrary shake to disguise weak movement.
- Review foreground parallax, clipping, grass/instance culling, sun reveal, and reflected highlights through the entire route.

## 8. Visual tests before the expensive batch

Use staged tests:

1. Clay framing and silhouette tests.
2. Low-resolution opening/midpoint/ending lighting tests.
3. A short motion test: wind, waves, bird articulation, camera speed, blur, flicker.
4. Native-resolution representative proof frames, including the most difficult lighting or closest geometry.
5. Only then enable the authorized full-render gate.

A possible starting point for CPU Cycles is 128 maximum animation samples, adaptive sampling, a 24-sample minimum, threshold around .03, and OpenImageDenoise; a hero still may need 256–512 samples and a tighter threshold. These are **starting points**, not a photorealism certificate or fixed requirement. Volumetrics and small highlights may require different settings. Inspect single-frame denoising for temporal shimmer.

Explicitly reject and fix flat trees, black unreadable forests, blob clouds, oval fog patches, mirror-sheet water, unstable highlights, implausible motion, and distracting repeated patterns before scaling up.

Record separate statuses:

```text
TECHNICAL: PASS / FAIL
VISUAL: reviewed with limitations / revision needed / approved by user
DELIVERY: preview only / rendering / final verified
```

## 9. Freeze the scene and render resumably

- Build and validate the scene **once**, freeze that exact `.blend`, compute SHA-256, and distribute the same bytes to workers.
- Independently rebuilding a visually identical scene can still produce a different file hash. Do not mix rebuilt scenes in a delivery claiming one frozen scene identity.
- Record frame ID, scene hash, Blender version, resolution, samples, adaptive settings, and other consequential settings in render receipts. Include color/motion/seed settings in the production fingerprint as appropriate.
- Render each requested native frame. Never silently upscale, retime, duplicate, or interpolate to satisfy a native-frame requirement.
- Write images to temporary filenames, validate them, then atomically rename. Reuse only files whose integrity and fingerprints match.
- Store progress and actual per-frame times. Save completed work before worker timeouts where practical.
- Use `fail-fast: false` for independent chunks so one failed clip does not discard unrelated running work.

Native Blender background pattern, adapting script arguments to the project:

```bash
blender -b frozen_scene.blend --python scripts/render_worker.py -- \
  --start 1 --end 6 --threads 4
```

PyPI `bpy` scripts may instead run directly with the compatible Python interpreter. Do not assume a script supports flags it does not define.

## 10. Choose chunks from measured runtime, not optimism

Benchmark representative opening, middle, ending, fog-heavy, and reflection-heavy frames. Include setup and encoding overhead, and account for slower hosted machines.

A conservative starting rule is:

```text
safe_frames_per_job = floor((job_limit - setup_allowance) * 0.65 / slow_frame_time)
```

Use consistent units. Example: a 350-minute limit, 15-minute allowance, and a 30-minute slow frame permit about seven frames; choosing six leaves additional margin. Twelve frames would be too risky on the same evidence.

A real lesson from this project: a twelve-frame chunk exceeded its 350-minute job limit even though many other chunks succeeded. Preserve successful clips and recover that range using smaller render shards; do not rerun the entire movie.

If render shards differ from encoding chunks, reunite verified raw frames before encoding the desired clip. Account for CI matrix-size limits by batching or orchestrating ranges, not by pretending more workflows create more hardware.

Total runtime is approximately:

```text
sum(actual render work + necessary overhead) / effective simultaneous capacity
+ scheduling gaps + the final straggler/recovery cost
```

Multiple workflows share the hosting account's applicable concurrency limits. Test capacity with a tiny independent job, not a duplicate full render. A queued test shows no immediate extra capacity; it does not by itself prove the precise billing plan or configured quota.

Label ETAs as estimates, distinguish total from remaining time, and revise them from completed-job timings. CPU thread counts alone are not reliable cross-device speed comparisons. Get approval before provisioning paid capacity. Do not evade platform quotas with alternate accounts.

## 11. Encode without losing provenance or exploding storage

- Verify each expected frame and its receipt before encoding a segment.
- Use the requested native FPS, dimensions, and a broadly compatible pixel format such as `yuv420p` for ordinary H.264 delivery.
- Set a suitable H.264 profile/level for the actual resolution and FPS; 1080p60 commonly uses High/4.2. Verify the target player's compatibility.
- Choose quality and bitrate from image content, duration, and storage budget. Short independently encoded clips can overshoot nominal ABR targets; measure actual output sizes instead of assuming an exact file size.
- Two-pass analysis of source PNGs is not an extra lossy generation. Re-encoding an already encoded movie is.
- When clips have compatible stream parameters, concatenate chronologically with stream copy. Validate timestamps, decode count, FPS, duration, and segment boundaries afterwards.
- Keep raw frame sequences on temporary workers or suitable external storage, not casually in Git. Use short-retention intermediates and durable storage for requested final files.
- Delete only authorized, reproducible intermediates. Preserve the previous finished delivery and unrelated project artifacts.
- Track the workspace/snapshot cap as well as Git's file limits and CI artifact quota. An extra preview can materially increase storage.

## 12. Finished-footage previews without interrupting production

When the user wants to see what is finished:

1. Read completed artifacts from the existing production run; do not cancel, restart, or duplicate its render jobs.
2. Prefer the longest continuous finished opening. If you instead jump over gaps, label the jumps and source time ranges clearly.
3. Verify segment checksums, frame ranges, quality settings, FPS/resolution, and one scene hash.
4. Join by stream copy where possible. Do not invent missing footage.
5. Fully decode and validate the resulting preview.
6. Give it a distinct filename, e.g. `Scene_PARTIAL_1080p60.mp4`, and a report explicitly stating that it is not final delivery.
7. Publish only preview files. Do not overwrite final scene, still, movie, or validation reports with a partial result.
8. If storage downloads are unavailable in the local sandbox, a small authorized CI assembly job can publish the preview through an accessible repository/storage route. Never forward an API credential to a signed storage redirect host.
9. If all hosted slots are busy, explain that the assembly job may queue. Do not claim it is already finished.
10. Open/present the actual MP4 and provide an accessible download link, not only an internal pathname.

A successful preview must not conceal production failures. Report a failed range separately; failure may prevent downstream final assembly even while other jobs keep running.

## 13. Recover narrowly and verify independently

- Identify the actual failure from job steps and annotations, not just the overall workflow label.
- Preserve all successful ranges. Retry only missing/corrupt/failed frames using the **same frozen scene and quality**.
- Split time-limited ranges into smaller shards. If bytes or quality settings change, treat it as a new revision rather than silently mixing results.
- Handle source artifacts from multiple recovery runs explicitly. A cancelled matrix may skip its dependent final assembler, requiring a separate recovery-aware assembly.
- Do not describe a workflow as successful merely because its scene-building step passed or an approval gate skipped rendering.

Before final delivery, independently check:

- `.blend` opens; assets are packed/resolved; expected scene revision and animation settings exist.
- Movie dimensions, codec, pixel format, FPS, duration, exact decoded frame count, and complete chronological coverage.
- Source-frame/segment receipts and scene identity match the delivered scene.
- Full-movie decoding succeeds; no truncated or corrupt ending.
- Duplicate decoded hashes are investigated when motion should change every frame. Uniqueness alone does **not** prove native rendering: interpolated frames can also be unique. Provenance and pipeline inspection are necessary.
- Opening/middle/ending and cut boundaries are visually inspected; motion and denoising stability are reviewed.
- Still belongs to the current scene revision rather than an old delivery.
- Delivered files fit storage limits and are genuinely downloadable/playable.

Separate technical completion from artistic approval. Use language such as “verified native 1080p60; visual limitations remain” when warranted. Never call a procedural reconstruction indistinguishable from a photograph without adequate evidence.

## 14. Deliver and hand over clearly

Deliver the requested editable scene, still, movie, source scripts/config, credits, and small validation manifests as appropriate. Do not overwhelm the user with scratch files.

- Open the primary requested deliverable in the available file viewer.
- Include a clearly named MP4 download link when a movie was requested. Users may not see an internal file viewer or filesystem path.
- State actual dimensions, FPS, duration, native frame count, and whether it is final or partial.
- Explain any known visual compromises or missing ranges.
- If a real asynchronous workflow is still running, provide its actual link and current status. Do not promise to send another message automatically unless the system genuinely supports that capability.
- Leave a concise recovery note: active run IDs, frozen-scene identity, successful/missing ranges, pending checks, and exact next actions. Never put credentials in the note.
- When final delivery replaces a temporary preview, manage redundant files without deleting the user's only accessible copy.

## Reference implementation (optional worked example)

The public worked example is available at:
https://github.com/mhammedamazil-hub/Testrepo/tree/arena/f0bb5c2d-testrepo

Useful source files include `scripts/build_scene.py`, `scripts/prepare_revision_base.py`, `scripts/revise_scene.py`, `scripts/project_config.py`, `scripts/render_frames.py`, `scripts/encode_chunk.py`, `scripts/encode_verify.py`, `scripts/verify_delivery.py`, and `tools/assemble_partial_preview.py`. The `tests/` directory and `docs/` notes explain codec checks, safe preview assembly, and known recovery needs.

This is a scene-specific worked example, not a universal generator or a flawless template. The revision script requires its documented baseline scene. The original twelve-frame CI chunk size caused a documented timeout: use measured, safer chunking from this skill rather than copying that setting blindly. Read the code before running it, and never launch an expensive example workflow just to inspect the implementation.

## Copy-and-paste kickoff prompt

```text
Read and apply the attached realistic-blender-production SKILL.md.
Use your available shell, filesystem, Blender/Python, image-inspection,
encoding, and permitted rendering tools to do the work yourself.

Subject/reference: [describe or attach]
Preserve: [important features]
Change: [requested improvements]
Deliverables: [editable Blender / still / animation]
Resolution, duration, native FPS: [values]
Lighting/style and camera motion: [preferences]
Compute budget, deadline, privacy restrictions: [limits]

First audit the real tools and resources, inspect existing work, and ask
only consequential unresolved questions. Match composition before detail.
Iterate with visible render tests. Freeze one verified scene for production.
Do not invent tool usage, native frames, rendering progress, or completion.
Provide actual playable/downloadable files and an honest validation report.
```