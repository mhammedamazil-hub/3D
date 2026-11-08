#!/usr/bin/env python3
import bpy,os,sys,json,struct,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent;p=ROOT/'output/Coconut_Tree_Scene_Ready.glb';b=p.read_bytes()
assert b[:4]==b'glTF';v,l=struct.unpack_from('<II',b,4);assert v==2 and l==len(b)
n,t=struct.unpack_from('<II',b,12);j=json.loads(b[20:20+n])
leaf=[m for m in j['materials'] if 'Leaf' in m.get('name','')][0]
assert leaf.get('alphaMode')=='MASK',leaf
assert all('uri' not in i for i in j.get('images',[]))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(p));bpy.context.view_layer.update()
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];pts=[o.matrix_world@v.co for o in meshes for v in o.data.vertices];mn=[min(q[i] for q in pts) for i in range(3)];mx=[max(q[i] for q in pts) for i in range(3)];dims=[mx[i]-mn[i] for i in range(3)]
assert 14<dims[2]<17,dims
r={'pass':True,'file':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'leaf_alphaMode':leaf['alphaMode'],'alphaCutoff':leaf.get('alphaCutoff'),'embedded_images':len(j.get('images',[])),'mesh_objects':len(meshes),'dimensions_m':dims,'bounds_min_m':mn,'bounds_max_m':mx}
(ROOT/'docs/COCONUT_GLB_ROUNDTRIP_V4.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2),flush=True)
# Small roundtrip render to prove alpha foliage survives export/import.
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=420;s.render.resolution_y=520;s.view_settings.view_transform='AgX'
w=bpy.data.worlds.new('W');w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(.7,.76,.8,1);w.node_tree.nodes['Background'].inputs[1].default_value=1;s.world=w
cd=bpy.data.cameras.new('C');cd.type='ORTHO';cd.ortho_scale=18.5;cam=bpy.data.objects.new('C',cd);s.collection.objects.link(cam);cam.location=(9,-22,10);cam.rotation_euler=(Vector((0,0,8))-cam.location).to_track_quat('-Z','Y').to_euler();s.camera=cam
s.render.filepath=str(ROOT/'review/v4/coconut_glb_roundtrip.png');bpy.ops.render.render(write_still=True);sys.stdout.flush();os._exit(0)
