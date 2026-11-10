#!/usr/bin/env python3
"""Render a v5.2 visual proof plus causal A/B tests for the sunrise god rays.

Modes:
  normal     — complete single-sun, mist and world-space cloud deck
  no_mist    — hide the scattering volume; rays cannot appear
  no_sun     — hide the one directional sun; the volumetric glow disappears
  no_clouds  — hide the shadow-only deck; no distinct shadow-shaped shafts
"""
import argparse, json, os, sys, time
from pathlib import Path
import bpy
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from kerala_v5 import apply_v5, audit_lighting

ap = argparse.ArgumentParser()
ap.add_argument('--mode', choices=['normal', 'no_mist', 'no_sun', 'no_clouds'], default='normal')
ap.add_argument('--frame', type=int, default=75)
ap.add_argument('--width', type=int, default=800)
ap.add_argument('--height', type=int, default=450)
ap.add_argument('--samples', type=int, default=32)
ap.add_argument('--out', required=True)
a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'output/Kerala_Coconut_Realism.blend'))
s = apply_v5(a.samples)
if a.mode == 'no_mist':
    bpy.data.objects['SM_V52_Sunrise_MistDomain'].hide_render = True
elif a.mode == 'no_sun':
    bpy.data.objects['LGT_V52_RisingSun'].hide_render = True
elif a.mode == 'no_clouds':
    bpy.data.objects['SM_V52_CloudDeck'].hide_render = True
s.frame_set(a.frame)
s.render.resolution_x = a.width
s.render.resolution_y = a.height
s.render.resolution_percentage = 100
s.cycles.samples = a.samples
s.render.threads_mode = 'FIXED'
s.render.threads = 2
s.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL' if a.frame <= 60 else 'RGB_ALBEDO'
out = ROOT / a.out
out.parent.mkdir(parents=True, exist_ok=True)
s.render.filepath = str(out)
audit = audit_lighting(s)
t = time.time()
bpy.ops.render.render(write_still=True)
report = {
    'mode': a.mode,
    'frame': a.frame,
    'seconds': round(time.time() - t, 3),
    'resolution': [a.width, a.height],
    'samples': a.samples,
    'denoising_input_passes': s.cycles.denoising_input_passes,
    'audit': audit,
    'output': a.out,
}
Path(str(out) + '.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
sys.stdout.flush()
os._exit(0)
