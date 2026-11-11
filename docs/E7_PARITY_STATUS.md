# E7 Packed-Records Parity — Status (2026-11-11)

Branch `arena/3e3c4ae6-3d` (base `main` @ `8cbf76e`). Authoritative snapshot of the
E7 parity investigation. Update this file as the work lands; do not treat it as
marketing — every claim below is tied to a CI run or a committed artifact.

## Task (standing)

Make `tools/records_parity` byte-parity between the two Vulkan paths it renders:

- **Path A (expanded):** CPU-mesher-expanded absolute vertex buffer + `voxelcore.vert`.
- **Path B (records):** vertex-pulled packed 8-byte records + `records.vert`
  (`p = local + push-constant chunk origin`), shaded in-shader.

Acceptance criteria (do not relax without explicit sign-off):

1. Byte-identical PPMs (1280x960, R8G8B8A8_UNORM) on the CI lavapipe oracle.
2. No relaxation of the single-pixel exception in the CI parity gate
   (comment in `.github/workflows/ci.yml` / gate logic) — **untouched so far.**
3. Unit tests stay green (Release): 499,210 checks / 0 failures (last verified at `207e2a5`).

## Current verdict (HEAD `15d1de0`)

`records_parity` **FAILS**: exactly one pixel differs:

```
pixel(844,300) A=(94,156,63) B=(94,94,94)   diff_pixels=1  max_channel_delta=62  diff_bytes=2
```

Deterministic across runs; A-vs-A2 and B-vs-B2 renders match exactly. The mismatch
sits exactly on the skyline silhouette — a hairline sliver ~1e-04 px ≈ 1–3 f32 ULPs
(ULP ≈ 6.1e-05 at x≈844) from several triangle edges.

**2026-11-11 CI state:** at `207e2a5` (`invariant` fix) all build jobs green,
vulkan-headless red with the usual single-pixel report. At `15d1de0` (solo probes)
**all four jobs fail at the build stage** — a compile error in the new
`records_parity.cpp` solo-probe block is suspected (no parity report is produced,
artifacts come up empty, logs are not readable via the API). Fix is in progress.

## What is confirmed (evidence)

1. **Winner in A** = grass-top face (PosY, y=21) — its depth won at the pixel.
2. **Winner in B** = an **east-wall (PosX) record of chunk (48,0)** — bisect:
   PosY-only→green, non-PosY→gray; surgical: east-only→gray, chunk30→gray,
   noc30→sky, noc30_noeast→green.
3. Per-record probes (B): only the y=16 east record (block=1, stone) paints the
   pixel, as (94,94,94). y=18 (dirt) paints (97,83,67). y=20 (grass) and y=0 paint sky.
4. **Depth readback at (844,300):** A = `0x3f7e8bd6`, B = `0x3f7e3f50`
   (different primitives winning — not a shading tie).
5. CPU math with the exact GPU mvp bits: grasstop tri0 **covers** the sample by
   1.22e-04 px; negzStone tri0 covers by 1.15e-04 px; stone16/dirt/grassEast
   slivers **miss** by 0.9–1.9e-04 px. All within a few ULPs.
6. Shading: CPU `shadeFace` vs GLSL in `records.vert` are symbol-for-symbol
   identical (aoK=0.35+0.2167·ao, lightK=0.2+0.8·light/15, sun PosY 1.0 / NegY 0.5 /
   Z 0.8 / X 0.72). The (94,94,94) B-pixel is **not** producible from any
   (base, ao, light, sun) in those tables — open anomaly, pending solo probes.
7. Pipelines verified identical in fixed-function state: viewport, scissor,
   cull NONE, MSAA 1x, depth LESS+write, same blend (src-alpha / 1-src-alpha),
   same topology, same clear color, same render pass.
8. mvp push-constant bytes identical between paths; vertex input bytes byte-identical
   for the two skyline quads checked so far (stone16/dirt byte dump added at `15d1de0`,
   blocked by the build break).
9. Scene contains **no water** (water pass empty in both paths).
10. `invariant gl_Position;` added to both vertex shaders — **no effect** on the
    mismatch or the depth values.

## What I changed (complete list)

Engine C++ (aurora/behavior preservation intent):
- `voxelcore/engine/rendering/vulkan/vulkan_headless.hpp` — depth image allocated with
  TRANSFER_SRC; render pass depth attachment `finalLayout = TRANSFER_SRC_OPTIMAL`;
  new `depthAt(x, y)` (1x1 D32 readback) for diagnostics. No draw-path change.
- `voxelcore/engine/rendering/vulkan/shaders/voxelcore.vert`,
  `.../records.vert` — added `invariant gl_Position;` (multipass invariance hint;
  observed to be a no-op here).
- `voxelcore/tools/records_parity.cpp` — diagnostics only: Y-forward-projection fix,
  containing/nearest-edge triangle dumps, bisect/reversed-order/surgical probes,
  byte dumps of quads, packed-word dump, neighborhood patch dump, depth readback,
  solo-quad probes (the bit that currently breaks the build).
- `.github/workflows/ci.yml` — extended the parity-ppm artifact list (diagnostic PPMs).

**No Rust code exists in this repository** (zero `.rs` files, no Cargo). No engine
behavior change beyond the above; **no default flip** (E7 stays opt-in); **no merge**
to any other branch; **no gate relaxation**. Unit tests unchanged since `6a400c7`,
last green Release run: 499,210 / 0 failures.

## Open items / next steps

1. **Fix the build break** (`15d1de0`): build locally against Khronos
   Vulkan-Headers fetched from `codeload.github.com` (local apt lacks libvulkan-dev),
   repair the solo-probe block in `records_parity.cpp`, push, confirm CI green-ish.
2. Read the solo probes: `solo stone16: A_pix=… A_depth=0x… B_pix=… B_depth=0x…`
   and `solo dirt: …` — decisive for *why* identical vertex bits rasterize
   differently (or for exposing an input-byte difference).
3. Then decide the fix:
   - (a) make path B's position computation bit-trivial (e.g. emit absolute
     positions), or
   - (b) pin down the rasterizer ULP behavior and force identical bits properly, or
   - (c) escalate to the user with the single-pixel evidence and explicit sign-off
     before even discussing the CI exception. No exception will be taken without that.
4. After parity is green: fix the 4 docs that still say "parity pending", then the
   default-flip decision for E7 (records pipeline on by default) — with the user.

## Reproduction

```bash
gh run list --branch arena/3e3c4ae6-3d --limit 1
jid=$(gh api repos/{owner}/{repo}/actions/runs/<run_id>/jobs --jq '.jobs[] | select(.name=="vulkan-headless") | .id')
gh api repos/{owner}/{repo}/check-runs/$jid/annotations
```
