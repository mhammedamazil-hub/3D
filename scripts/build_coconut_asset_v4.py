#!/usr/bin/env python3
import bpy,os,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from coconut_asset_v4 import import_user_coconut,export_glb
ROOT=Path(__file__).resolve().parent.parent
bpy.ops.wm.read_factory_settings(use_empty=True)
c,sm,em=import_user_coconut(scale=.1)
pts=[o.matrix_world@v.co for o in c.objects if o.type=='MESH' for v in o.data.vertices]
mn=[min(p[i] for p in pts) for i in range(3)];mx=[max(p[i] for p in pts) for i in range(3)]
out=ROOT/'output/Coconut_Tree_Scene_Ready.glb';export_glb(c,sm,em,out)
report={'source_glb':'assets/models/user/coconut_tree_low_poly.glb','source_sha256':hashlib.sha256((ROOT/'assets/models/user/coconut_tree_low_poly.glb').read_bytes()).hexdigest(),'export':str(out.relative_to(ROOT)),'export_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'bounds_min_m':mn,'bounds_max_m':mx,'dimensions_m':[mx[i]-mn[i] for i in range(3)],'objects':[o.name for o in c.objects],'note':'Uploaded trunk/frond meshes preserved; metric scale and fruit clusters added. GLB uses Principled alpha-clip foliage; Blender scene adds restrained Cycles translucency.'}
(ROOT/'output/Coconut_Tree_Scene_Ready.glb.report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
# Inspection render of the enhanced Blender asset.
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=32;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=700;s.render.resolution_y=840;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX'
w=bpy.data.worlds.new('Sky');w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(.72,.78,.82,1);w.node_tree.nodes['Background'].inputs[1].default_value=1.0;s.world=w
ld=bpy.data.lights.new('Key','AREA');ld.energy=1800;ld.size=8;lo=bpy.data.objects.new('Key',ld);s.collection.objects.link(lo);lo.location=(-6,-9,16);lo.rotation_euler=(Vector((0,0,10))-lo.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Cam');cd.type='ORTHO';cd.ortho_scale=18.5;cam=bpy.data.objects.new('Cam',cd);s.collection.objects.link(cam);cam.location=(9,-22,10);cam.rotation_euler=(Vector((0,0,8))-cam.location).to_track_quat('-Z','Y').to_euler();s.camera=cam
s.render.filepath=str(ROOT/'review/v4/coconut_asset_enhanced.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'review/v4/coconut_asset_v4.blend'),compress=True);sys.stdout.flush();os._exit(0)
