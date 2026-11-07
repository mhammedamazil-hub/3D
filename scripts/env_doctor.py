#!/usr/bin/env python3
"""Environment doctor for the Blender production sandbox.

Proves, with real work (not claims):
  * bpy imports and reports its version
  * Cycles CPU renders a still to PNG (validated with Pillow)
  * a 24-frame native animation renders, encodes to H.264 (imageio-ffmpeg),
    and fully decodes with the expected frame count
  * Eevee headless (software GL) is probed in an isolated subprocess
Writes review/env_report.json and prints a summary.
Run via: scripts/blender-py scripts/env_doctor.py
"""
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "review"
REVIEW.mkdir(exist_ok=True)


def build_smoke_scene():
    import bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    ground = bpy.context.object
    ground.name = "Ground"
    mat = bpy.data.materials.new("M_Ground")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.32, 0.30, 0.27, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.85
    ground.data.materials.append(mat)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(-1.1, 0, 1.0))
    sphere = bpy.context.object
    sphere.name = "HeroSphere"
    bpy.ops.object.shade_smooth()
    mat = bpy.data.materials.new("M_Sphere")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.65, 0.16, 0.10, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.3
    sphere.data.materials.append(mat)

    bpy.ops.mesh.primitive_cube_add(size=1.4, location=(1.4, 0.4, 0.7))
    cube = bpy.context.object
    cube.name = "RotatingCube"
    bev = cube.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.04
    bev.segments = 3
    mat = bpy.data.materials.new("M_Cube")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.15, 0.32, 0.55, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.45
    cube.data.materials.append(mat)
    cube.rotation_euler = (0, 0, 0)
    cube.keyframe_insert("rotation_euler", frame=1)
    cube.rotation_euler = (0.6, 0.4, 6.2831853)
    cube.keyframe_insert("rotation_euler", frame=25)
    for fc in cube.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"

    bpy.ops.object.light_add(type="SUN", location=(4, -4, 8))
    sun = bpy.context.object
    sun.name = "Sun"
    sun.data.energy = 3.0
    sun.data.angle = 0.035
    sun.rotation_euler = (0.7, 0.15, 0.6)

    world = bpy.data.worlds.new("W_Sky")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.35, 0.45, 0.60, 1.0)
    bg.inputs["Strength"].default_value = 0.6

    bpy.ops.object.camera_add(location=(6.2, -5.4, 3.0))
    cam = bpy.context.object
    cam.name = "Camera"
    direction = cam.location - __import__("mathutils").Vector((0, 0, 0.9))
    cam.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    scene.camera = cam

    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.image_settings.file_format = "PNG"
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 24
    scene.view_settings.view_transform = "AgX"
    return scene


def cycles_still(report):
    import bpy
    from PIL import Image

    scene = build_smoke_scene()
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.05
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 320
    scene.render.resolution_y = 180
    scene.frame_set(1)
    out = REVIEW / "env_smoke_cycles.png"
    scene.render.filepath = str(out)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    with Image.open(out) as im:
        im.load()
        extrema = im.convert("L").getextrema()
        ok = im.size == (320, 180) and extrema[1] > 20 and extrema[0] < extrema[1]
    report["cycles_still"] = {
        "ok": bool(ok),
        "path": str(out.relative_to(ROOT)),
        "seconds": round(dt, 2),
        "size": [320, 180],
        "samples": 24,
        "sha256": __import__("hashlib").sha256(out.read_bytes()).hexdigest(),
    }


def native_anim_and_encode(report):
    import bpy
    import imageio_ffmpeg

    scene = bpy.context.scene
    scene.render.resolution_x = 160
    scene.render.resolution_y = 90
    scene.cycles.samples = 8
    frames_dir = REVIEW / "env_anim"
    frames_dir.mkdir(exist_ok=True)
    scene.render.filepath = str(frames_dir / "frame_")
    t0 = time.time()
    bpy.ops.render.render(animation=True)
    render_s = time.time() - t0
    pngs = sorted(frames_dir.glob("frame_*.png"))

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    mp4 = REVIEW / "env_anim_test.mp4"
    cmd = [
        ff, "-y", "-framerate", "24", "-i", str(frames_dir / "frame_%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        "-profile:v", "high", "-movflags", "+faststart", str(mp4),
    ]
    enc = subprocess.run(cmd, capture_output=True, text=True)
    dec = subprocess.run(
        [ff, "-i", str(mp4), "-map", "0:v:0", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    m = re.findall(r"frame=\s*(\d+)", dec.stderr)
    decoded = int(m[-1]) if m else -1
    err_lines = [l for l in dec.stderr.splitlines() if re.search(r"error|invalid|corrupt", l, re.I)]
    report["native_anim"] = {
        "ok": enc.returncode == 0 and dec.returncode == 0 and decoded == 24 and len(pngs) == 24 and not err_lines,
        "frames_rendered": len(pngs),
        "render_seconds": round(render_s, 2),
        "seconds_per_frame": round(render_s / max(len(pngs), 1), 2),
        "mp4": str(mp4.relative_to(ROOT)),
        "decoded_frames": decoded,
        "ffmpeg": imageio_ffmpeg.get_ffmpeg_version(),
        "mp4_bytes": mp4.stat().st_size if mp4.exists() else 0,
    }


def eevee_probe(report):
    """Run in a subprocess so a GL crash cannot kill the main report."""
    probe = subprocess.run(
        ["sh", str(ROOT / "scripts" / "blender-py"), str(Path(__file__).resolve()), "--eevee-probe"],
        capture_output=True, text=True, timeout=300,
    )
    result_file = REVIEW / "eevee_probe.json"
    if probe.returncode == 0 and result_file.exists():
        report["eevee_headless"] = json.loads(result_file.read_text())
    else:
        report["eevee_headless"] = {
            "ok": False,
            "note": "probe subprocess failed (see review/eevee_probe.log); Cycles CPU is the production path",
            "returncode": probe.returncode,
        }
    (REVIEW / "eevee_probe.log").write_text(probe.stdout + "\n" + probe.stderr)


def eevee_probe_main():
    import bpy

    scene = build_smoke_scene()
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x = 320
    scene.render.resolution_y = 180
    scene.frame_set(1)
    out = REVIEW / "env_smoke_eevee.png"
    scene.render.filepath = str(out)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    from PIL import Image

    with Image.open(out) as im:
        im.load()
        extrema = im.convert("L").getextrema()
        ok = im.size == (320, 180) and extrema[1] > 20
    (REVIEW / "eevee_probe.json").write_text(json.dumps({
        "ok": bool(ok),
        "path": str(out.relative_to(ROOT)),
        "seconds": round(time.time() - t0, 2),
        "note": "software OpenGL (llvmpipe); preview use only, no GPU present",
    }))


def main():
    if "--eevee-probe" in sys.argv:
        eevee_probe_main()
        return

    import bpy

    report = {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
        "blender": {
            "version": bpy.app.version_string,
            "background": bpy.app.background,
            "module": "PyPI bpy",
        },
        "ram_total_gib": round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30, 2),
        "disk_free_gib": round(shutil.disk_usage(ROOT).free / 2**30, 2),
    }
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.refresh_devices()
        report["cycles_devices"] = sorted({(d.name, d.type) for d in prefs.devices})
    except Exception as e:  # pragma: no cover
        report["cycles_devices_error"] = str(e)

    cycles_still(report)
    native_anim_and_encode(report)
    try:
        eevee_probe(report)
    except Exception as e:
        report["eevee_headless"] = {"ok": False, "note": f"probe error: {e}"}

    required = [report["cycles_still"]["ok"], report["native_anim"]["ok"]]
    report["technical"] = "PASS" if all(required) else "FAIL"
    (REVIEW / "env_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if report["technical"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
