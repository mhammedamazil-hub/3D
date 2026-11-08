#!/usr/bin/env python3
"""Import the supplied GLB unchanged, inventory it and render an inspection still."""
import bpy,os,sys,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'review/v4';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/models/user/coconut_tree_low_poly.glb'));bpy.context.view_layer.update()
obs=list(bpy.context.scene.objects);meshes=[o for o in obs if o.type=='MESH'];pts=[];ms=[]
for o in meshes:
 pts.extend(o.matrix_world@v.co for v in o.data.vertices)
 ms.append({'name':o.name,'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'materials':[m.name for m in o.data.materials if m],'world_matrix':[list(v) for v in o.matrix_world]})
mn=[min(p[i] for p in pts) for i in range(3)];mx=[max(p[i] for p in pts) for i in range(3)]
r={'objects':[{'name':o.name,'type':o.type} for o in obs],'meshes':ms,'bounds_min':mn,'bounds_max':mx,'dimensions':[mx[i]-mn[i] for i in range(3)],'images':[{'name':i.name,'size':list(i.size),'packed':bool(i.packed_file)} for i in bpy.data.images],'materials':[m.name for m in bpy.data.materials]}
(OUT/'coconut_import_inventory.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2),flush=True)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=640;s.render.resolution_y=760;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX'
w=bpy.data.worlds.new('Reference inspection sky');w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(.65,.72,.78,1);w.node_tree.nodes['Background'].inputs[1].default_value=.8;s.world=w
size=max(mx[i]-mn[i] for i in range(3));ld=bpy.data.lights.new('Inspection key','AREA');ld.energy=size*size*7;ld.shape='DISK';ld.size=size*.6;lo=bpy.data.objects.new('Inspection key',ld);s.collection.objects.link(lo);lo.location=(-size*.5,-size*.8,size*1.2);lo.rotation_euler=(Vector((0,0,size*.5))-lo.location).to_track_quat('-Z','Y').to_euler()
cen=Vector([(mn[i]+mx[i])/2 for i in range(3)]);cd=bpy.data.cameras.new('Inspection camera');cd.type='ORTHO';cd.ortho_scale=size*1.17;cd.clip_end=5000;cam=bpy.data.objects.new('Inspection camera',cd);s.collection.objects.link(cam);cam.location=cen+Vector((size*.8,-size*1.7,size*.25));cam.rotation_euler=(cen-cam.location).to_track_quat('-Z','Y').to_euler();s.camera=cam
s.render.filepath=str(OUT/'coconut_upload_original.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'coconut_upload_import.blend'),compress=True);sys.stdout.flush();os._exit(0)
