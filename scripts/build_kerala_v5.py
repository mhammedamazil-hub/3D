#!/usr/bin/env python3
"""Build v5 god-rays animation scene from v4 and render a local preview still."""
import bpy,os,sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from kerala_v5 import apply_v5
ROOT=Path(__file__).resolve().parent.parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/Kerala_Coconut_Realism.blend'))
s=apply_v5(samples=24)
out=ROOT/'output/Kerala_Coconut_Realism_GodRays.blend'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
manifest={'revision':s['revision'],'blend':str(out.relative_to(ROOT)),'blend_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'frames':[s.frame_start,s.frame_end],'fps':s.render.fps,'resolution':[s.render.resolution_x,s.render.resolution_y],'duration_seconds':(s.frame_end-s.frame_start+1)/s.render.fps}
(ROOT/'review/v5/build_manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2),flush=True)
# Preview still at mid-dolly, half resolution.
s.render.resolution_x=800;s.render.resolution_y=450;s.cycles.samples=8;s.cycles.adaptive_threshold=.04;s.render.filepath=str(ROOT/'review/v5/preview_f075.png')
bpy.ops.render.render(write_still=True);sys.stdout.flush();os._exit(0)
