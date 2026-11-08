#!/usr/bin/env python3
"""CI-only public CC0 asset preparation. Downloads Poly Haven source files,
extracts usable LODs/rocks with Blender, packs textures, records SHA-256.
No credentials or paid services. Raw downloads stay in runner temp.
"""
import json,sys,urllib.request,hashlib,time,tempfile,traceback
from pathlib import Path
import bpy
from mathutils import Vector
OUT=Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=True);REC=[];TMP=Path(tempfile.mkdtemp(prefix='kerala-quality-'))
def get(u):
 with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Kerala-Quality/3'}),timeout=180) as f:return f.read()
def j(u):return json.loads(get(u))
def save(u,rel,aid):
 d=get(u);p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(d);REC.append({'path':str(rel),'url':u,'source':'https://polyhaven.com/a/'+aid,'license':'CC0-1.0','bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()});print('SAVED',rel,len(d),flush=True);return p

def prepare_model(aid,kind='tree',target_polys=80000):
 try:
  files=j('https://api.polyhaven.com/files/'+aid);meta=j('https://api.polyhaven.com/info/'+aid)
  b=files.get('blend',{}).get('1k',{}).get('blend') or files.get('blend',{}).get('2k',{}).get('blend')
  if not b:print('NO BLEND',aid);return
  raw=TMP/f'{aid}.blend';raw.write_bytes(get(b['url']))
  for inc,o in b.get('include',{}).items():
   p=raw.parent/inc;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(get(o['url']))
  bpy.ops.wm.open_mainfile(filepath=str(raw))
  meshes=[o for o in bpy.data.objects if o.type=='MESH']
  if kind=='tree':
   cands=[o for o in meshes if 'LOD1' in o.name.upper() and len(o.data.polygons)>20000]
   if not cands:cands=[o for o in meshes if o.name in {aid,aid+'_LOD0',aid+'_LOD1'}]
   if not cands:cands=meshes
   o=max(cands,key=lambda x:len(x.data.polygons))
  else:o=max(meshes,key=lambda x:len(x.data.polygons))
  print('MODEL',aid,'choose',o.name,len(o.data.vertices),len(o.data.polygons),flush=True)
  # Evaluate any modifiers into a static editable mesh.
  dg=bpy.context.evaluated_depsgraph_get();ev=o.evaluated_get(dg);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg)
  keep=bpy.data.objects.new(aid+'_prepared',me);bpy.context.scene.collection.objects.link(keep)
  if len(me.polygons)>target_polys:
   bpy.ops.object.select_all(action='DESELECT');keep.select_set(True);bpy.context.view_layer.objects.active=keep
   md=keep.modifiers.new('Quality LOD reduction','DECIMATE');md.ratio=target_polys/len(me.polygons);bpy.ops.object.modifier_apply(modifier=md.name)
  # Origin at bottom center for scattering; preserve mesh proportions.
  vs=[keep.matrix_world@v.co for v in keep.data.vertices];mn=Vector(tuple(min(v[i] for v in vs) for i in range(3)));mx=Vector(tuple(max(v[i] for v in vs) for i in range(3)));center=Vector(((mn.x+mx.x)/2,(mn.y+mx.y)/2,mn.z))
  for v in keep.data.vertices:v.co-=center
  for obj in list(bpy.data.objects):
   if obj!=keep:bpy.data.objects.remove(obj,do_unlink=True)
  for c in list(bpy.data.collections):bpy.data.collections.remove(c)
  for _ in range(4):bpy.ops.outliner.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
  bpy.ops.file.pack_all()
  rel=f'models/{aid}.blend';p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(p),compress=True)
  d=p.read_bytes();REC.append({'path':rel,'url':b['url'],'source':'https://polyhaven.com/a/'+aid,'license':'CC0-1.0','bytes':len(d),'sha256':hashlib.sha256(d).hexdigest(),'prepared_from':o.name,'prepared_polygons':len(keep.data.polygons),'dimensions_m':list(mx-mn)})
  (OUT/'models'/f'{aid}.json').write_text(json.dumps({'metadata':meta,'chosen':o.name,'source_url':b['url'],'dimensions_m':list(mx-mn),'polygons':len(keep.data.polygons)},indent=2))
  print('PREPARED',rel,len(d),len(keep.data.polygons),flush=True)
 except Exception as e:print('FAIL MODEL',aid,repr(e),flush=True);traceback.print_exc()

for aid,kind,polys in [('jacaranda_tree','tree',220000),('tree_small_02','tree',140000),('island_tree_03','tree',140000),('rock_face_02','rock',60000),('boulder_01','rock',40000),('rock_07','rock',30000),('stone_01','rock',20000),('coast_rocks_01','rock',50000)]:prepare_model(aid,kind,polys)
# High-resolution surface maps. Keep normal/rough/displacement for actual shading.
for aid,res in [('brown_mud','4k'),('red_laterite_soil_stones','4k'),('clay_roof_tiles','4k'),('wood_planks','2k'),('worn_plaster_wall','2k'),('rock_face','2k'),('bark_brown_02','2k'),('corrugated_iron_02','2k'),('forest_ground_04','2k'),('red_dirt_mud_01','2k')]:
 try:
  files=j('https://api.polyhaven.com/files/'+aid);meta=j('https://api.polyhaven.com/info/'+aid)
  for ch in ['Diffuse','Rough','Displacement','nor_gl','AO','Metal']:
   node=files.get(ch,{});r=node.get(res) or node.get('2k') or node.get('1k')
   if not isinstance(r,dict):continue
   fmt=next((k for k in ['jpg','png','exr'] if k in r and isinstance(r[k],dict) and 'url' in r[k]),None)
   if not fmt:continue
   u=r[fmt]['url'];ext=u.split('?')[0].rsplit('.',1)[-1];save(u,f'textures/{aid}/{ch}.{ext}',aid)
  (OUT/'textures'/aid/'metadata.json').write_text(json.dumps(meta,indent=2))
 except Exception as e:print('FAIL TEX',aid,repr(e),flush=True)
for aid in ['overcast_soil_puresky','kloofendal_overcast_puresky']:
 try:
  f=j('https://api.polyhaven.com/files/'+aid);u=f['hdri']['4k']['hdr']['url'];save(u,f'hdri/{aid}_4k.hdr',aid)
 except Exception as e:print('FAIL HDRI',aid,repr(e),flush=True)
(OUT/'manifest.json').write_text(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':REC},indent=2));print('DONE',len(REC),sum(x['bytes'] for x in REC),flush=True)
