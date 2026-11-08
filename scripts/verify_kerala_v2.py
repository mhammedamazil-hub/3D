#!/usr/bin/env python3
"""Independent delivery checks for the frozen Kerala photoreal v2 scene/still."""
import hashlib, json, sys, os
from pathlib import Path
import bpy
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
BLEND=ROOT/'output/Kerala_Photoreal.blend';HERO=ROOT/'output/Kerala_Photoreal_1080p.png';REV='kerala-v2.0-photoreal'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
report={'revision_expected':REV,'checks':{}};c=report['checks']
c['blend_exists']=BLEND.exists();c['blend_sha256']=sha(BLEND) if BLEND.exists() else None
bpy.ops.wm.open_mainfile(filepath=str(BLEND));s=bpy.context.scene
c['scene_revision']=s.get('revision');c['revision_match']=s.get('revision')==REV
c['resolution']=[s.render.resolution_x,s.render.resolution_y];c['resolution_match']=c['resolution']==[1920,1080]
c['camera']=s.camera.name if s.camera else None
c['units_metric']=s.unit_settings.system=='METRIC' and s.unit_settings.scale_length==1.0
c['collections']={n:bool(bpy.data.collections.get(n)) for n in ['COL_Terrain','COL_Paddies','COL_Water','COL_Path_and_Bunds','COL_FieldVegetation','COL_Mountains','COL_Kerala_House','COL_Atmosphere','COL_Lights','COL_Cameras']}
c['collections_present']=all(c['collections'].values())
water=bpy.data.materials.get('MAT_Paddy_Water_IOR_1p333');ior=None
if water:
    p=next((n for n in water.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if p:ior=p.inputs['IOR'].default_value
c['water_ior']=round(ior,4) if ior else None;c['water_ior_ok']=bool(ior and abs(ior-1.333)<.002)
c['external_images_missing']=[im.filepath for im in bpy.data.images if im.source=='FILE' and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).exists()]
c['objects']=len(bpy.data.objects);c['materials']=len(bpy.data.materials);c['node_groups']=[g.name for g in bpy.data.node_groups if g.name.startswith('GN_')]
rice=bpy.data.objects.get('SM_Paddy_FineRice_RowInstances');c['rice_points']=rice.get('instance_points') if rice else None
c['cc0_tree_instances']=bool(bpy.data.objects.get('SM_CC0_Library_Tree_Instances'));c['sapling_library']=len(bpy.data.collections.get('COL_Library_SaplingBroadleaf',bpy.data.collections.new('tmp')).objects) if bpy.data.collections.get('COL_Library_SaplingBroadleaf') else 0
c['packed_images']=sum(1 for im in bpy.data.images if im.packed_file)
if HERO.exists():
    with Image.open(HERO) as im:
        im.load();c['hero_size']=list(im.size);c['hero_mode']=im.mode;ext=im.convert('L').getextrema();c['hero_luma_extrema']=list(ext)
    c['hero_dimensions_ok']=c['hero_size']==[1920,1080];c['hero_not_blank']=ext[0]<ext[1] and ext[1]>30;c['hero_sha256']=sha(HERO)
    rec=HERO.with_suffix('.receipt.json')
    if rec.exists():
        r=json.loads(rec.read_text());c['receipt_scene_hash_match']=r.get('scene_sha256')==c['blend_sha256'];c['receipt_image_hash_match']=r.get('image_sha256')==c['hero_sha256'];c['render_seconds']=r.get('seconds');c['engine']=r.get('engine');c['samples']=r.get('samples')
else:c['hero_exists']=False
required=['blend_exists','revision_match','resolution_match','collections_present','units_metric','water_ior_ok','hero_dimensions_ok','hero_not_blank','receipt_scene_hash_match','receipt_image_hash_match','cc0_tree_instances']
report['technical']='PASS' if all(c.get(k) for k in required) and not c.get('external_images_missing') else 'FAIL'
report['visual']='Agent-reviewed preview stills; final still inspection recorded in QA notes.'
report['delivery']='Final verified' if report['technical']=='PASS' else 'Incomplete'
(ROOT/'docs/KERALA_VALIDATION_V2.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));sys.stdout.flush()
if report['technical']!='PASS':sys.exit(1)
os._exit(0)
