# E7 — Packed quad records (24-byte → record-based GPU vertex pulling) — DESIGN

**Status:** design (pre-implementation) · **Stage:** 6/13 · **Date:** 2026-11-11
**Reference:** Horizon `mesher/packed.rs` + `terrain.wgsl` (24-byte solid-face records, `PACKED_BASE = 1<<28` sentinel, WGSL expansion). Not vendored/translated — re-designed to our format.

## Why
Current GPU path expands every quad to 4 vertices + 6 indices on the CPU (`mesh_triangles.hpp`).
For a generated chunk that is ~1.3–1.6 k quads → ~5.3 k vertices × 28 B ≈ 150 KB + indices per
chunk rebuild. Records move the expansion GPU-side and slash upload size and CPU work.

## Current Quad (for reference)
`{float x,y,z,u,v (20B); FaceDir dir (1B); BlockId block (2B); uint8 ao[4] (4B); uint8 light (1B)}` ≈ 28–32 B +
heap overhead per element in the vector; 6 indices per quad on top.

## Proposed record: 8 bytes (2 × uint32)
All greedy output is axis-aligned single-block-face rectangles with per-corner AO.
Chunk-relative coords: x,z ∈ [0,16], y ∈ [0,64] (top planes at y=64 exist).

```
word0: x:4 | z:4 | y:7 | uExt-1:4 | vExt-1:4 | dir:3 | reserved:6   // 32 bits
word1: block:16 | ao[4]×2b:8 | light:4 | reserved:4                  // 32 bits
```
- `dir` = FaceDir enum (0..5), `uExt`/`vExt` = merged extents (1..16), stored minus 1.
- `ao[4]` = per-corner 2-bit corner occlusion (0..3), same order as today.
- `light` = face light 0..15 (mesher writes it since stage 9 M2).
- Position base = chunk origin; the whole record is chunk-local, so records are
  relocatable without re-mesh on chunk moves within the same y column layout.

**Why 8 B beats Horizon's 24 B:** their record carries absolute position + full AO/shade ramp
metadata for their shader-pack interface; we specialize to chunk-local greedy output and one
fixed shading model. If shader-pack support (stage 8) later needs arbitrary UVs/flags, the
reserved bits + a uint32 extension word grow the record to 12 B with an explicit version nibble
— documented here so the format is never silently broken.

## GPU expansion (Vulkan)
- One storage buffer per chunk (or one arena for all chunks with an offset table —
  vertex arena from `memory/arena.hpp` backs this later).
- `draw`: instanced, `gl_InstanceID` = record index, `gl_VertexID` ∈ [0,6).
- `records.vert`: read record, compute the 4 corners from dir/x/y/z/uExt/vExt
  (identical formulas to `expandQuads` — bitwise-identical output required),
  look up ao per corner, apply `faceSunFactor(dir)` and `light` tint, emit `vec3` + `vec4 rgba`.
- CPU fallback (`mesh_triangles.hpp`) stays as the reference expansion for tests and for
  backends without storage buffers; shared corner formula lives in one header used by both
  (single source of truth, mirrored in GLSL — the GLSL is generated from the same table).

## Acceptance criteria (implementation milestone)
1. `packed_record.hpp`: pack/unpack roundtrip property tests (all 6 dirs × extents 1..16 ×
   coord ranges incl. y=64 × ao patterns × light values). Must be exhaustive where feasible.
2. `vulkan_render --records` produces a PPM; in CI it must match the unpacked-path PPM
   **pixel-for-pixel** (or, if FP reordering occurs in the matmul path, documented ≤1 LSB/channel
   with mean 0 and aggregate |diff| reported — never silently accepted).
3. Bench: `greedy_mesh+pack`, `upload_bytes_per_chunk` reported; target ≥ 10× fewer bytes
   uploaded per chunk rebuild vs expanded path (≈150 KB → ≈10 KB at 1.3 k quads).
4. No change to greedy merge semantics, AO, cave culling, or light — records are a pure
   post-mesh compaction.
5. Arena allocation for record buffers (reuse `Engine/memory/arena.hpp`), no per-frame malloc.

## Risks & non-goals
- **Mobile vertex-pulling perf** varies (Adreno/Mali vs desktop); gate behind
  `VOXELCORE_PACKED_RECORDS` and measure on device before making it default.
- **Not** taken from Horizon: `PACKED_BASE` sentinel inside mixed vertex buffers (we keep a
  separate record path), WGSL (we use GLSL→SPIR-V), and their shader-pack-era field layout.
- E7 does **not** touch LOD records (E9/E10) or the vertex arena page reclaim (stage 6 remainder).

## Estimated effort
Record codec + tests (half day), Vulkan records pipeline + CI parity gate (1 day),
bench + docs (half day). Unpacked path remains default until CI parity is proven on lavapipe.
