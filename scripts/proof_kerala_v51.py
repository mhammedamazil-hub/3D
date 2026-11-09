#!/usr/bin/env python3
"""Render a visual proof plus causal A/B tests for the single-sun fix."""
import argparse,json,os,sys,time
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from kerala_v5 import apply_v5,audit_lighting
ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['normal','no_mist','no_cloud','no_sun'],default='normal');ap.add_argument('--frame',type=int,default=75);ap.add_argument('--width',type=int,default=960);ap.add_argument('--height',type=int,default=540);ap.add_argument('--samples',type=int,default=24);ap.add_argument('--out',required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/Kerala_Coconut_Realism.blend'))
s=apply_v5(a.samples)
if a.mode=='no_mist':
    bpy.data.objects['SM_V51_SingleSun_MistDomain'].hide_render=True
elif a.mode=='no_cloud':
    bpy.data.objects['SM_V51_CloudShadow_Aperture'].hide_render=True
elif a.mode=='no_sun':
    bpy.data.objects['LGT_V51_SingleSun'].hide_render=True
s.frame_set(a.frame);s.render.resolution_x=a.width;s.render.resolution_y=a.height;s.cycles.samples=a.samples;s.render.threads_mode='FIXED';s.render.threads=2
out=ROOT/a.out;out.parent.mkdir(parents=True,exist_ok=True);s.render.filepath=str(out)
audit=audit_lighting(s);t=time.time();bpy.ops.render.render(write_still=True)
report={'mode':a.mode,'frame':a.frame,'seconds':round(time.time()-t,3),'resolution':[a.width,a.height],'samples':a.samples,'audit':audit,'output':a.out}
Path(str(out)+'.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True);sys.stdout.flush();os._exit(0)
