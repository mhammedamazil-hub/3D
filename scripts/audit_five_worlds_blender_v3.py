#!/usr/bin/env python3
"""Independent bpy audit: open every v3 .blend and prove it contains no images.

Run with `sh scripts/blender-py scripts/audit_five_worlds_blender_v3.py`.
This is intentionally separate from the renderer so local verification can
inspect the frozen scene files without rendering them.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
REVISION = "five-worlds-blender-v3-pure-3d"
IMAGE_NODE_TYPES = {
    "ShaderNodeTexImage", "ShaderNodeTexEnvironment", "GeometryNodeImageTexture",
    "CompositorNodeImage", "ShaderNodeTexIES",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    path = path.resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def inspect_scene(scene):
    image_nodes = []
    trees = []
    for mat in bpy.data.materials:
        if mat.use_nodes:
            trees.append(mat.node_tree)
    for world in bpy.data.worlds:
        if world.use_nodes:
            trees.append(world.node_tree)
    for group in bpy.data.node_groups:
        trees.append(group)
    if scene.use_nodes and scene.node_tree:
        trees.append(scene.node_tree)
    for tree in trees:
        for node in tree.nodes:
            if node.bl_idname in IMAGE_NODE_TYPES:
                image_nodes.append(f"{tree.name}:{node.name}:{node.bl_idname}")
    image_textures = [t.name for t in bpy.data.textures if getattr(t, "type", "") == "IMAGE"]
    return {
        "image_datablocks": len(bpy.data.images),
        "image_datablock_names": [i.name for i in bpy.data.images],
        "image_texture_nodes": len(image_nodes),
        "image_texture_node_details": image_nodes,
        "image_texture_datablocks": len(image_textures),
        "environment_texture_nodes": sum(1 for x in image_nodes if "Environment" in x),
        "linked_libraries": len(bpy.data.libraries),
        "movieclips": len(bpy.data.movieclips),
        "objects": len(bpy.data.objects),
        "meshes": len(bpy.data.meshes),
        "materials": len(bpy.data.materials),
        "lights": len(bpy.data.lights),
        "cameras": len(bpy.data.cameras),
        "node_groups": len(bpy.data.node_groups),
        "textures": len(bpy.data.textures),
        "engine": scene.render.engine,
        "device": scene.cycles.device,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "fps": scene.render.fps,
        "frame_range": [scene.frame_start, scene.frame_end],
        "pass": (len(bpy.data.images) == 0 and not image_nodes
                 and not image_textures and len(bpy.data.libraries) == 0
                 and len(bpy.data.movieclips) == 0
                 and scene.render.engine == "CYCLES"
                 and scene.cycles.device == "CPU"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="docs/FIVE_WORLDS_BLENDER_V3_MANIFEST.json")
    ap.add_argument("--out", default="review/five_worlds_blender_v3/blend_audit.json")
    args = ap.parse_args()
    manifest_path = (ROOT / args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text())
    scenes, errors = [], []
    for entry in manifest["scenes"]:
        blend = (ROOT / entry["blend"]).resolve()
        if not blend.is_file():
            errors.append(f"{entry['index']}: missing blend {blend}")
            continue
        digest = sha256(blend)
        if digest != entry["blend_sha256"]:
            errors.append(f"{entry['index']}: blend SHA mismatch")
        ref = (ROOT / entry["reference"]).resolve()
        if not ref.is_file() or sha256(ref) != entry["reference_sha256"]:
            errors.append(f"{entry['index']}: reference SHA mismatch")
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        audit = inspect_scene(bpy.context.scene)
        audit.update({
            "index": entry["index"], "name": entry["name"],
            "blend": rel(blend), "blend_sha256": digest,
            "reference": entry["reference"],
            "reference_usage": manifest["reference_usage"],
        })
        if not audit["pass"]:
            errors.append(f"{entry['index']}: pure-3D audit failed")
        scenes.append(audit)
    result = {
        "revision": REVISION,
        "audited_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "manifest": rel(manifest_path),
        "scene_count": len(scenes),
        "pass": not errors and len(scenes) == 5 and all(s["pass"] for s in scenes),
        "image_policy": manifest["image_policy"],
        "reference_usage": manifest["reference_usage"],
        "skills": manifest["skills"],
        "scenes": scenes,
        "errors": errors,
    }
    out = (ROOT / args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "pass": result["pass"], "scene_count": len(scenes),
        "report": rel(out), "errors": errors,
        "image_datablocks": sum(s["image_datablocks"] for s in scenes),
        "image_texture_nodes": sum(s["image_texture_nodes"] for s in scenes),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
