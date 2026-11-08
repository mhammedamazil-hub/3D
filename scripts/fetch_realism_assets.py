#!/usr/bin/env python3
"""Run on an unrestricted CI runner. Retrieve small public CC0/GPL assets.
No credentials. Writes provenance and SHA-256; refuses to exceed 70 MB.
"""
import json,sys,urllib.request,urllib.parse,hashlib,time,re
from pathlib import Path
OUT=Path(sys.argv[1] if len(sys.argv)>1 else 'transport/realism');OUT.mkdir(parents=True,exist_ok=True)
MAX=70_000_000;records=[]
def get(url,timeout=60):
 req=urllib.request.Request(url,headers={'User-Agent':'Kerala-Blender-Production/2.0'})
 with urllib.request.urlopen(req,timeout=timeout) as f:return f.read()
def total():return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
def save(url,rel,license,source,maxbytes=18_000_000):
 if total()>MAX:raise RuntimeError('asset budget exceeded')
 data=get(url)
 if len(data)>maxbytes:print('SKIP large',rel,len(data));return None
 p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 records.append({'path':str(rel),'url':url,'source':source,'license':license,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 print('SAVED',rel,len(data));return p
def j(url):return json.loads(get(url))
# GPL Modular Tree release compatible with Blender 4.x (original upstream).
try:
 rel=j('https://api.github.com/repos/MaximeHerpin/modular_tree/releases/tags/4_0_2')
 a=next(x for x in rel['assets'] if 'linux' in x['name'])
 req=urllib.request.Request(a['url'],headers={'Accept':'application/octet-stream','User-Agent':'Kerala-Blender-Production'})
 with urllib.request.urlopen(req,timeout=90) as f:data=f.read()
 p=OUT/'addons'/a['name'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 records.append({'path':str(p.relative_to(OUT)),'url':a['url'],'source':'https://github.com/MaximeHerpin/modular_tree/releases/tag/4_0_2','license':'GPL-3.0','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
except Exception as e:print('MTree release failed:',repr(e))
# Poly Haven catalog: inspect names/categories, choose a few useful plant/tree models.
try:
 models=j('https://api.polyhaven.com/assets?t=models');(OUT/'catalog_models.json').write_text(json.dumps(models,indent=2))
 def text(v):return ' '.join(map(str,[v.get('name',''),v.get('categories',[]),v.get('tags',[])])).lower()
 candidates=[(k,v) for k,v in models.items() if any(w in text(v)+' '+k.lower() for w in ['tree','palm','banana','fern','plant'])]
 priority=['banana_plant','coconut_tree','palm_tree','fir_tree','pine_tree','oak_tree','quiver_tree','fern_02','potted_plant_01','potted_plant_02','tree_stump']
 candidates.sort(key=lambda kv:(priority.index(kv[0]) if kv[0] in priority else 99,-kv[1].get('downloads',0)))
 chosen=candidates[:4];print('MODEL CANDIDATES',[(k,text(v)) for k,v in candidates[:20]])
 for aid,meta in chosen:
  try:
   files=j('https://api.polyhaven.com/files/'+aid);blend=files.get('blend',{}).get('1k',{}).get('blend')
   if not blend:blend=files.get('blend',{}).get('2k',{}).get('blend')
   if not blend:print('no blend',aid);continue
   save(blend['url'],f'polyhaven/models/{aid}/{aid}.blend','CC0-1.0','https://polyhaven.com/a/'+aid)
   for inc,obj in blend.get('include',{}).items():save(obj['url'],f'polyhaven/models/{aid}/{inc}','CC0-1.0','https://polyhaven.com/a/'+aid)
   (OUT/'polyhaven/models'/aid/'metadata.json').write_text(json.dumps(meta,indent=2))
  except Exception as e:print('model failed',aid,repr(e))
except Exception as e:print('Poly Haven models failed:',repr(e))
# PBR texture maps, 1K JPG to stay memory/storage conscious.
try:
 tex=j('https://api.polyhaven.com/assets?t=textures');(OUT/'catalog_textures.json').write_text(json.dumps(tex,indent=2))
 wanted=['red_laterite','brown_mud','clay_roof_tiles','rock_face','bark_brown_02','forrest_ground_01','leafy_grass','plastered_wall_04','aerial_rocks_02']
 ids=[x for x in wanted if x in tex]
 if len(ids)<5:
  for k,v in tex.items():
   if any(w in (k+' '+text(v)) for w in ['laterite','mud','roof tile','rock face','bark','forest ground']) and k not in ids:ids.append(k)
   if len(ids)>=7:break
 for aid in ids:
  try:
   files=j('https://api.polyhaven.com/files/'+aid);maps=files.get('jpg',{}).get('1k') or files.get('jpg',{}).get('2k')
   if not maps:continue
   for channel in ['diffuse','rough','roughness','normal','nor_gl','disp','displacement']:
    if channel in maps and isinstance(maps[channel],dict) and 'url' in maps[channel]:save(maps[channel]['url'],f'polyhaven/textures/{aid}/{channel}.jpg','CC0-1.0','https://polyhaven.com/a/'+aid,8_000_000)
   (OUT/'polyhaven/textures'/aid/'metadata.json').write_text(json.dumps(tex[aid],indent=2))
  except Exception as e:print('texture failed',aid,repr(e))
except Exception as e:print('Poly Haven textures failed:',repr(e))
# Natural overcast/pure-sky HDRI for physically plausible fill and reflections.
try:
 hdris=j('https://api.polyhaven.com/assets?t=hdris');(OUT/'catalog_hdris.json').write_text(json.dumps(hdris,indent=2))
 hid='kloofendal_48d_partly_cloudy_puresky' if 'kloofendal_48d_partly_cloudy_puresky' in hdris else next((k for k,v in hdris.items() if 'puresky' in k and ('overcast' in text(v) or 'cloudy' in text(v))),None)
 if hid:
  f=j('https://api.polyhaven.com/files/'+hid);u=f['hdri']['2k']['hdr']['url'];save(u,f'polyhaven/hdri/{hid}_2k.hdr','CC0-1.0','https://polyhaven.com/a/'+hid)
except Exception as e:print('HDRI failed:',repr(e))
(OUT/'manifest.json').write_text(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'total_bytes':total(),'files':records},indent=2))
(OUT/'LICENSES.md').write_text('# Retrieved asset licenses\n\n- Poly Haven assets: CC0 1.0 Universal, https://polyhaven.com/license . Source URLs and SHA-256 are in manifest.json.\n- Modular Tree add-on: GPL-3.0, upstream https://github.com/MaximeHerpin/modular_tree . Add-on code is a tool, not a texture baked into the scene.\n- User reference images are NOT included or redistributed here.\n')
print('DONE total',total(),'files',len(records))
if total()>MAX:raise SystemExit('Asset budget exceeded')
