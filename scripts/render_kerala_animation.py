#!/usr/bin/env python3
"""Render a frame range of the Kerala v5 1080p30 animation.
Builds v5 from the frozen v4 blend so the large derived blend need not be tracked.
Usage: python scripts/render_kerala_animation.py --start 1 --end 15 --out frames --samples 24
"""
import bpy,os,sys,time,json,hashlib,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from kerala_v5 import apply_v5, audit_lighting
ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=1);ap.add_argument('--end',type=int,default=150);ap.add_argument('--out',default='frames');ap.add_argument('--samples',type=int,default=20);ap.add_argument('--width',type=int,default=1920);ap.add_argument('--height',type=int,default=1080);ap.add_argument('--threads',type=int,default=0)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
src=ROOT/'output/Kerala_Coconut_Realism.blend'
bpy.ops.wm.open_mainfile(filepath=str(src))
s=apply_v5(samples=a.samples)
audit=audit_lighting(s)
if not audit['pass']:
    raise RuntimeError(f'Lighting/scene audit failed: {audit}')
s.render.resolution_x=a.width;s.render.resolution_y=a.height;s.render.resolution_percentage=100;s.render.fps=30
if a.threads>0:s.render.threads_mode='FIXED';s.render.threads=a.threads
outdir=ROOT/a.out;outdir.mkdir(parents=True,exist_ok=True)
src_sha=hashlib.sha256(src.read_bytes()).hexdigest();rows=[]
for f in range(a.start,a.end+1):
    s.frame_set(f);s.render.filepath=str(outdir/f'frame_{f:04d}.png');t=time.time()
    bpy.ops.render.render(write_still=True);dt=time.time()-t
    p=Path(s.render.filepath);rows.append({'frame':f,'seconds':round(dt,3),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    print(json.dumps(rows[-1]),flush=True)
receipt={'revision':s['revision'],'source_blend':'output/Kerala_Coconut_Realism.blend','source_blend_sha256':src_sha,'range':[a.start,a.end],'samples_max':a.samples,'resolution':[a.width,a.height],'fps':30,'engine':'CYCLES','device':'CPU','lighting_audit':audit,'frames':rows}
(outdir/f'receipt_{a.start:04d}_{a.end:04d}.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({'done':True,'range':[a.start,a.end]}),flush=True);sys.stdout.flush();os._exit(0)
