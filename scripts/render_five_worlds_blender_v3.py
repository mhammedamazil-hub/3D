#!/usr/bin/env python3
"""Render a frame range from a frozen pure-3D Five Worlds Blender v3 scene.

Every shard opens the committed .blend, enforces a no-image audit before any
rendering, renders native Cycles CPU PNG frames, and writes a receipt with
frame SHA-256, lighting audit and pure-3D audit results.
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


def audit_pure_3d(scene):
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
        "pass": (len(bpy.data.images) == 0 and not image_nodes
                 and not image_textures and len(bpy.data.libraries) == 0
                 and len(bpy.data.movieclips) == 0),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=int, required=True, choices=range(1, 6))
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--out", default="frames_v3")
    parser.add_argument("--manifest", default="docs/FIVE_WORLDS_BLENDER_V3_MANIFEST.json")
    parser.add_argument("--blend", default="", help="Override blend path")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--samples", type=int, default=4)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if args.end < args.start:
        raise SystemExit("--end must be >= --start")

    out_root = Path(args.out).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    frames_dir = out_root / f"scene_{args.scene:02d}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"scenes": []}
    entry = next((e for e in manifest.get("scenes", []) if e["index"] == args.scene), None)
    if args.blend:
        blend_path = Path(args.blend).resolve()
    elif entry:
        blend_path = (ROOT / entry["blend"]).resolve()
    else:
        raise SystemExit(f"No blend path for scene {args.scene}; pass --blend or build the manifest")
    if not blend_path.is_file():
        raise SystemExit(f"Blend not found: {blend_path}")

    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    scene = bpy.context.scene
    pure = audit_pure_3d(scene)
    if not pure["pass"]:
        raise SystemExit(f"Pure-3D audit failed for {blend_path}: {pure}")

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.threads_mode = "FIXED"
    scene.render.threads = args.threads
    scene.render.use_persistent_data = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.use_overwrite = True
    scene.render.use_placeholder = False
    scene.render.use_file_extension = True
    scene.render.filepath = str(frames_dir / "frame_")
    scene.frame_start = args.start
    scene.frame_end = args.end
    scene.frame_step = 1
    scene.frame_set(args.start)

    print(f"[render] scene={args.scene} blend={blend_path} frames={args.start}-{args.end} "
          f"size={args.width}x{args.height} samples={args.samples} threads={args.threads} "
          f"pure_3d={pure['pass']}")
    bpy.ops.render.render(animation=True)

    expected = [f"frame_{f:04d}.png" for f in range(args.start, args.end + 1)]
    actual = sorted(p.name for p in frames_dir.glob("frame_*.png"))
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise SystemExit(f"Frame mismatch: missing={missing[:5]} extra={extra[:5]} count={len(actual)}")

    light_counts = {}
    for obj in scene.objects:
        if obj.type == "LIGHT":
            light_counts[obj.data.type] = light_counts.get(obj.data.type, 0) + 1
    receipt = {
        "revision": REVISION,
        "rendered_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "blender": bpy.app.version_string,
        "scene": args.scene,
        "name": entry["name"] if entry else f"Scene {args.scene:02d}",
        "slug": entry["slug"] if entry else f"Scene{args.scene:02d}",
        "blend": str(blend_path.relative_to(ROOT)) if blend_path.is_relative_to(ROOT) else str(blend_path),
        "blend_sha256": sha256(blend_path),
        "reference": entry.get("reference") if entry else None,
        "reference_sha256": entry.get("reference_sha256") if entry else None,
        "reference_usage": "visual_reference_only_not_embedded",
        "start": args.start,
        "end": args.end,
        "frames_rendered": len(expected),
        "frame_names": expected,
        "frame_sha256": {name: sha256(frames_dir / name) for name in expected},
        "engine": "CYCLES",
        "device": "CPU",
        "samples": args.samples,
        "width": args.width,
        "height": args.height,
        "fps": scene.render.fps,
        "lighting_audit": {
            "sun_lights": light_counts.get("SUN", 0),
            "spot_lights": light_counts.get("SPOT", 0),
            "area_lights": light_counts.get("AREA", 0),
            "pass": light_counts.get("SUN", 0) == 1 and light_counts.get("SPOT", 0) == 0,
        },
        "pure_3d_audit": pure,
    }
    receipt_path = out_root / f"receipt_scene_{args.scene:02d}_{args.start:04d}_{args.end:04d}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({
        "receipt": str(receipt_path),
        "frames": len(expected),
        "first": expected[0],
        "last": expected[-1],
        "lighting_audit": receipt["lighting_audit"],
        "pure_3d_audit": {"pass": pure["pass"], "image_datablocks": pure["image_datablocks"],
                          "image_texture_nodes": pure["image_texture_nodes"]},
    }, indent=2))


if __name__ == "__main__":
    main()
