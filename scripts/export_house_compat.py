#!/usr/bin/env python3
"""Small generic-export compatibility proof (not a game-engine import claim).
Exports the house render mesh to GLB and a separate convex collision proxy,
then reimports the GLB in a clean Blender scene and checks metre scale.
Procedural Cycles materials are not baked to glTF PBR textures here.
"""
import json, sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from kerala_config import BLEND, OUTPUT, HOUSE_X, HOUSE_Y
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
house=bpy.data.collections['COL_Kerala_House']
bpy.ops.object.select_all(action='DESELECT')
for o in house.all_objects:
    if o.type in {'MESH','EMPTY'}:o.select_set(True)
bpy.context.view_layer.objects.active=next(o for o in house.all_objects if o.type=='MESH')
glb=OUTPUT/'Kerala_House_Compat.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),use_selection=True,export_format='GLB',export_apply=True,export_yup=True)
# separate simple convex proxy, documented as UCX-style for engine handoff
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.mesh.primitive_cube_add(size=1,location=(HOUSE_X,HOUSE_Y+0.1,2.0))
proxy=bpy.context.object;proxy.name='UCX_Kerala_House_00';proxy.scale=(6.7,4.9,2.0);proxy.select_set(True)
col=OUTPUT/'Kerala_House_CollisionProxy.glb'
bpy.ops.export_scene.gltf(filepath=str(col),use_selection=True,export_format='GLB',export_yup=True)
# clean reimport scale check
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
meshes=[o for o in bpy.data.objects if o.type=='MESH']
pts=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
mn=Vector((min(p[i] for p in pts) for i in range(3)));mx=Vector((max(p[i] for p in pts) for i in range(3)))
dims=mx-mn
report={'glb':str(glb),'collision_proxy':str(col),'reimported_mesh_objects':len(meshes),'bbox_dimensions_m':[round(v,3) for v in dims],'scale_sane':10<dims.x<20 and 5<dims.y<15 and 4<dims.z<9,'engine_import':'NOT TESTED — no Unity/Unreal/Godot installed','materials':'procedural source retained in .blend; glTF material baking is a separate task'}
(OUTPUT/'house_compat_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
