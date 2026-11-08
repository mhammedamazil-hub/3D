#!/usr/bin/env python3
"""Render Kerala v3 quality scene and write an honest receipt.
Run: sh scripts/blender-py scripts/render_kerala_quality.py --camera CAM_Q_Hero_LeadingBund --width 2048 --height 1152 --samples 96 --out output/Kerala_Quality_1152p.png
"""
import bpy,os,sys,time,json,hashlib,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
ap=argparse.ArgumentParser();ap.add_argument('--camera',default='CAM_Q_Hero_LeadingBund');ap.add_argument('--width',type=int,default=2048);ap.add_argument('--height',type=int,default=1152);ap.add_argument('--samples',type=int,default=96);ap.add_argument('--out',default='output/Kerala_Quality_1152p.png');ap.add_argument('--pct',type=int,default=100)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
blend=ROOT/'output/Kerala_Quality.blend'
bpy.ops.wm.open_mainfile(filepath=str(blend))
s=bpy.context.scene;s.camera=bpy.data.objects[a.camera];s.render.resolution_x=a.width;s.render.resolution_y=a.height;s.render.resolution_percentage=a.pct;s.cycles.samples=a.samples;s.cycles.adaptive_threshold=.015;s.cycles.adaptive_min_samples=16;s.render.filepath=str(ROOT/a.out)
s.cycles.use_denoising=True;s.cycles.denoiser='OPENIMAGEDENOISE'
try:s.cycles.denoising_input_passes='RGB_ALBEDO'
except Exception:pass
try:s.cycles.denoising_prefilter='FAST'
except Exception:pass
s.render.use_persistent_data=False
scene_sha=hashlib.sha256(blend.read_bytes()).hexdigest();t=time.time();bpy.ops.render.render(write_still=True);dt=time.time()-t
img=Path(s.render.filepath);receipt={'revision':'kerala-v3.0-quality','camera':a.camera,'engine':'CYCLES','device':'CPU','resolution':[int(a.width*a.pct/100),int(a.height*a.pct/100)],'samples_max':a.samples,'adaptive_threshold':.015,'denoiser':'OPENIMAGEDENOISE','render_seconds':round(dt,3),'blend_sha256':scene_sha,'image_sha256':hashlib.sha256(img.read_bytes()).hexdigest(),'image_bytes':img.stat().st_size,'output':str(img.relative_to(ROOT)),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
(ROOT/(a.out+'.receipt.json')).write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2));sys.stdout.flush();os._exit(0)
