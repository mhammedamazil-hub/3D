#!/usr/bin/env python3
import json,sys,urllib.request,hashlib,time
from pathlib import Path
OUT=Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=True);MAX=55_000_000;records=[]
def get(u):
 with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Kerala-Blender/2'}),timeout=90) as f:return f.read()
def j(u):return json.loads(get(u))
def total():return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
def save(u,rel,aid,limit=12_000_000):
 if total()>MAX:raise RuntimeError('budget')
 d=get(u)
 if len(d)>limit:print('SKIP',rel,len(d));return
 p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(d);records.append({'path':str(rel),'url':u,'source':'https://polyhaven.com/a/'+aid,'license':'CC0-1.0','bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()});print('SAVED',rel,len(d))
models=['island_tree_01','island_tree_02','jacaranda_tree','tree_small_02','rock_face_02','boulder_01']
for aid in models:
 try:
  meta=j('https://api.polyhaven.com/info/'+aid);files=j('https://api.polyhaven.com/files/'+aid);(OUT/'models'/aid).mkdir(parents=True,exist_ok=True);(OUT/'models'/aid/'metadata.json').write_text(json.dumps(meta,indent=2));(OUT/'models'/aid/'files_api.json').write_text(json.dumps(files,indent=2))
  b=files.get('blend',{}).get('1k',{}).get('blend') or files.get('blend',{}).get('2k',{}).get('blend')
  if not b:print('NO BLEND',aid,list(files));continue
  save(b['url'],f'models/{aid}/{aid}.blend',aid)
  for inc,o in b.get('include',{}).items():save(o['url'],f'models/{aid}/{inc}',aid)
 except Exception as e:print('FAIL model',aid,repr(e))
textures=['brown_mud','clay_roof_tiles','bark_brown_02','worn_plaster_wall','rock_face','red_laterite_soil_stones','wood_planks','corrugated_iron_02']
for aid in textures:
 try:
  meta=j('https://api.polyhaven.com/info/'+aid);files=j('https://api.polyhaven.com/files/'+aid);(OUT/'textures'/aid).mkdir(parents=True,exist_ok=True);(OUT/'textures'/aid/'metadata.json').write_text(json.dumps(meta,indent=2));(OUT/'textures'/aid/'files_api.json').write_text(json.dumps(files,indent=2))
  print('TEX KEYS',aid,list(files))
  maps=files.get('jpg',{}).get('1k') or files.get('jpg',{}).get('2k') or files.get('png',{}).get('1k')
  if not maps:print('NO MAPS',aid);continue
  print('MAP CHANNELS',aid,list(maps))
  n=0
  for ch,o in maps.items():
   if isinstance(o,dict) and 'url' in o and n<6:
    ext=o['url'].split('?')[0].rsplit('.',1)[-1];save(o['url'],f'textures/{aid}/{ch}.{ext}',aid,7_000_000);n+=1
 except Exception as e:print('FAIL texture',aid,repr(e))
(OUT/'manifest.json').write_text(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'total_bytes':total(),'files':records},indent=2));print('DONE',total(),len(records))
if total()>MAX:raise SystemExit('budget')
