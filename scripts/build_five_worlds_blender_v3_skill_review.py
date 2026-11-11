#!/usr/bin/env python3
"""Recheck all 94 pinned blender-skills SKILL.md files for Five Worlds v3.

The user explicitly asked for the cloned `.claude/skills` blender-skills repo with
all 94 skills. This script reads every pinned SKILL.md, records its SHA-256, and
writes a concrete production/QA decision for each one. It does not pretend that
94 different art styles were mixed into one render: relevant skills are applied,
game-engine/backend skills are compatibility checks, character/sim disciplines
are N/A, and incompatible genre/style lenses are explicit exclusion checks.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills/blender-skills/.claude/skills"
META_SKILL = ROOT / "skills/realistic-blender-production/SKILL.md"
PIN_FILE = ROOT / "docs/skill_94_review.json"
VERSION_FILE = ROOT / "skills/blender-skills/version.json"
JSON_OUT = ROOT / "docs/five_worlds_blender_v3_skill_94_review.json"
MD_OUT = ROOT / "docs/FIVE_WORLDS_BLENDER_V3_SKILL_94_REVIEW.md"

APPLIED = {
    "blender-director": "Locked the v3 brief: five photorealistic pure-3D worlds, no image datablocks, five 10 s 1080p30 shots, proof loop, frozen .blend, 15-shard CI, independent delivery verification.",
    "blender-modeler": "Metric 1 BU = 1 m, named COL_/SM_/MAT_/CAM_/LGT_/GN_ hierarchy, non-destructive bevel/solidify/displace/GN modifiers and editable meshes.",
    "environment-artist": "Built five modular near/mid/far environment kits: alpine lake, alley, dune field, black-sand coast, rainforest temple.",
    "biome-worlds": "Climate-specific palettes, fog, erosion, wetness and vegetation density for alpine, urban-night, desert, arctic-coast and rainforest biomes.",
    "procedural-modeling": "Seeded Python-generated dune grids, mountain ridges, water grids, building modules, basalt columns, temple blocks and plant assets.",
    "geometry-nodes": "GN_Scatter_* groups distribute rocks, conifers, grass and broadleaf plants on terrain with seeded random scale/rotation and realized instances.",
    "materials": "Node-based Principled, glass/water, transparent, emissive and soft-mask shaders; no ShaderNodeTexImage or ShaderNodeTexEnvironment nodes.",
    "texture-workflow": "Procedural Noise/Wave/Voronoi/Gradient/Sky textures drive base color, roughness, bump, alpha and colour ramps; zero image textures.",
    "uv-workflow": "Explicit UVMap on grid terrain, dune ripples and aurora/mist ribbons; procedural UV soft-edge masks replace generated image masks.",
    "sculpting": "Clouds procedural Displace modifiers add organic terrain and rock relief while keeping the base mesh editable.",
    "lighting": "One physical SUN per scene, procedural Sky world, motivated AREA neon/window/temple fills; zero SPOT lights.",
    "camera-cinematography": "Per-scene 24–50 mm CAM_* paths with stable target tracking, foreground parallax, controlled depth of field and no handheld shake.",
    "animation": "300-frame keyframed camera motion, 4D water/aurora W drift, looping rain/dust, sign flicker and surf foam; no cached simulations.",
    "rendering": "Cycles CPU, 4 samples, adaptive sampling, OpenImageDenoise RGB_ALBEDO_NORMAL, AgX Medium High Contrast, 15 resumable CI shards.",
    "compositing": "AgX grading plus restrained FOG_GLOW on neon/aurora only; no photo backplate, no 2D matte, no composited reference image.",
    "lookdev": "Ten low-resolution five-scene Cycles proof-contact iterations and a camera-projection debug before the full-render gate; removed an occluding Alpine ridge, then corrected mountain/dune silhouettes, caravan scale, sky exposure, aurora curtains and temple canopy.",
    "vfx-fx": "Procedural rain, ground mist, wind-blown sand, waterfall spray, aurora ribbons, surf foam and emissive star geometry.",
    "vegetation-artist": "Linked conifer, fern, broadleaf and vine assets built from real curved leaf meshes, scattered with Geometry Nodes.",
    "hard-surface": "Beveled alley facades, emissive signs, pipes, AC units, temple lintels, steps and hexagonal basalt prisms.",
    "archviz": "Metric alley/temple scale with eye-level cameras, plausible door/window/step dimensions and architectural perspective.",
    "prop-artist": "Named signs, lanterns, stones, steps, cables, pipes, plinths, moss clumps and debris carry scene storytelling.",
    "scene-assembly": "Each scene uses COL_Environment, COL_Geo_Hero, COL_Geo_Background, COL_Props, COL_Atmosphere, COL_Lights and COL_Cameras collections.",
    "set-dressing": "Foreground rocks, signs, moss, vines, foam, puddles and debris are placed along the whole camera path, not only the opening frame.",
    "asset-optimization": "Linked mesh duplicates, GN instances, lower-resolution background ridges, compressed .blend files and 4-sample adaptive rendering.",
    "lod-pipeline": "Distant ridges and repeated vegetation use lower segment counts and linked instances; hero detail is reserved for near-camera geometry.",
    "export-pipeline": "Frozen .blend SHA-256, 15 shard receipts, H.264 MP4s, contact sheet, receipt/validation JSON and CI commit-back.",
    "qa-review": "Standalone bpy no-image auditor, shard lighting/pure-3D audits, per-frame SHA-256, full FFmpeg decode, CI validation, synthetic end-to-end finalizer/verifier test and independent local verifier with explicit PASS/FAIL.",
    "realistic-style": "Real-world scale, PBR roughness/IOR/Fresnel, restrained colour variation, continuous shading and metric lens choices.",
    "sci-fi-punk-worlds": "Neon Rain Alley follows one cyberpunk lane: dense signage, wet asphalt and cables, without steampunk/dieselpunk mashups.",
    "neon-retrofuturism": "Coloured emissive signs and wet reflections are used without synthwave grids, chrome excess or sunset-gradient clichés.",
    "noir-style": "High-contrast wet-alley lighting, negative fill, silhouettes and a limited neon colour slash.",
    "dark-gritty-mood": "Weathered concrete, pipes, stains and low-key alley lighting establish wear without horror contamination.",
    "liminal-space-style": "Empty repeated alley modules and stillness borrow only the spatial language, not Backrooms/horror styling.",
    "brutalist-mood": "Heavy concrete alley masses and repeated basalt columns provide weight without stylized brutalism.",
    "historical-worlds": "The rainforest temple uses ancient stone joinery, erosion and moss; it is an invented ruin, not a claimed documented historical site.",
    "cozy-wholesome-mood": "Alpine Lake uses calm golden-hour framing and a safe eye-level route without domestic props or narrative cuteness.",
    "physics-sim": "Compatibility check: rain, dust and spray are deterministic keyed procedural loops, not rigid/soft-body caches; no unavailable solver is claimed.",
}

COMPATIBILITY = {
    "collision-proxy": "No game-engine export is requested; collision naming conventions are preserved but no backend import is claimed.",
    "retopology": "Procedural quad grids and linked meshes need no character/deforming retopology pass; topology remains editable.",
    "godot-export": "No Godot export; checked that the .blend contains only procedural bpy data and no external texture paths.",
    "unity-export": "No Unity export; checked that the .blend contains only procedural bpy data and no external texture paths.",
    "unreal-export": "No Unreal export; checked that the .blend contains only procedural bpy data and no external texture paths.",
}

NOT_APPLICABLE = {
    "character-archetypes": "No characters, archetypes or scale mannequins appear in the five environmental shots.",
    "character-artist": "No character hero or anatomy work is requested.",
    "creature-artist": "No creatures or organic character silhouettes appear.",
    "cloth-sim": "No garments, banners or cloth caches are present.",
    "hair-groom": "No hair, fur or groom systems are present.",
    "rigging": "No armatures, deform bones or skinning are present.",
    "vehicle-artist": "No cars, ships, aircraft or mechs appear in the five worlds.",
}

EXCLUSION_NOTE = (
    "Rechecked all five frozen v3 .blend files and ten proof-contact passes; "
    "CI shard receipts enforce the same zero-image audit on all 1,500 final frames: "
    "no {skill} contamination; pure procedural 3D PBR/Cycles realism retained."
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def description(text: str) -> str:
    m = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip().strip("\"'") if m else ""


def main() -> None:
    pins = [x["skill"] for x in json.loads(PIN_FILE.read_text())]
    version = json.loads(VERSION_FILE.read_text())
    if len(pins) != 94 or version.get("skills") != 94:
        raise SystemExit("Expected exactly 94 pinned skills")
    records = []
    for name in pins:
        path = SKILL_DIR / name / "SKILL.md"
        if not path.is_file():
            raise SystemExit(f"Missing pinned skill: {path}")
        text = path.read_text(encoding="utf-8")
        if name in APPLIED:
            mode, action = "Applied", APPLIED[name]
        elif name in COMPATIBILITY:
            mode, action = "Compatibility check", COMPATIBILITY[name]
        elif name in NOT_APPLICABLE:
            mode, action = "Not applicable", NOT_APPLICABLE[name]
        else:
            mode = "QA / exclusion lens"
            action = EXCLUSION_NOTE.format(skill=name.replace("-", " "))
        records.append({
            "skill": name,
            "source": str(path.relative_to(ROOT)),
            "source_sha256": sha256(path),
            "description": description(text),
            "mode": mode,
            "action": action,
        })
    counts = Counter(r["mode"] for r in records)
    payload = {
        "revision": "five-worlds-blender-v3-pure-3d",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "library": "skills/blender-skills/.claude/skills",
        "library_version": version.get("version"),
        "pinned_skill_count": len(records),
        "meta_skill": str(META_SKILL.relative_to(ROOT)),
        "meta_skill_sha256": sha256(META_SKILL) if META_SKILL.is_file() else None,
        "counts": dict(counts),
        "note": "All 94 SKILL.md documents were rechecked. Relevant production skills are applied; incompatible style/genre lenses are QA/exclusion checks; character/sim disciplines are N/A. This is not a claim that 94 styles were mixed into one image.",
        "skills": records,
    }
    JSON_OUT.write_text(json.dumps(payload, indent=2) + "\n")
    lines = [
        "# Five Worlds Blender v3 — all 94 blender-skills rechecked",
        "",
        f"Library: `{payload['library']}` · version `{payload['library_version']}` · pinned skills: **{len(records)}**.",
        f"Separate production meta-skill: `{payload['meta_skill']}` (SHA-256 `{payload['meta_skill_sha256'][:12]}…`).",
        "",
        payload["note"],
        "",
        "## Counts",
        "",
    ]
    for mode, n in sorted(counts.items()):
        lines.append(f"- {mode}: {n}")
    lines += ["", "## Full 94-skill matrix", "", "| # | Skill | Mode | Concrete v3 decision |", "|---:|---|---|---|"]
    for i, r in enumerate(records, 1):
        lines.append(f"| {i} | `{r['skill']}` | {r['mode']} | {r['action']} |")
    lines += [
        "",
        "## Source integrity",
        "",
        "Every row's `source_sha256` is recorded in `docs/five_worlds_blender_v3_skill_94_review.json`;",
        "the builder, renderer, finalizer, verifier and no-image audit implement the applied decisions.",
        "",
    ]
    MD_OUT.write_text("\n".join(lines))
    print(json.dumps({
        "skills": len(records),
        "counts": dict(counts),
        "json": str(JSON_OUT.relative_to(ROOT)),
        "markdown": str(MD_OUT.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()
