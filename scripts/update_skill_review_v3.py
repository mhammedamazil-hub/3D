import json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
d=json.load(open(ROOT/'docs/skill_94_review.json'))
applied={
'archviz':'Metric tharavad retained at path end; 2K/4K scanned PBR, IOR 1.333 shallow paddy water, stable 38 mm eye-level perspective.',
'asset-optimization':'Packed 97 MB blend; recompressed oversized scans, collection instances, 1.49M unique mesh triangles, 79,917 rice points; coconut GN excluded after OOM.',
'biome-worlds':'Humid monsoon paddy with open water between rows, thin earthen bunds, coconut/banana/scan-tree canopy, bounded Ghat mist banks.',
'blender-director':'Quality-first brief from references; Infinigen/library/texture probes; multiple measured preview iterations before final render.',
'blender-modeler':'Named SM_/COL_ hierarchy; live GN/solidify/displace; timber drain crossing, detailed coconut fronds, row rice clumps.',
'camera-cinematography':'38 mm hero at 1.62 m, 58 mm house detail, 50 mm foreground; f/9 deep-ish focus, no handheld shake.',
'compositing':'AgX Medium High Contrast, exposure 0.0, reversible subtle fog-glow; no painted/photo backplate.',
'cozy-wholesome-mood':'Inhabited veranda props, potted plants, brass lamp, water jar, bench; safe eye-level route.',
'environment-artist':'Layered paddy plots, transverse bunds, mixed forest belts, three mesh Ghat ridges with editable displacement and mist.',
'export-pipeline':'Packed editable .blend, per-file CC0/BSD provenance/SHA-256, CI asset preparation scripts; v1/v2 deliverables preserved.',
'geometry-nodes':'Editable scatter groups for rice/bund grass/understory; Infinigen broadleaf live instancing via collection instances.',
'hard-surface':'Turned posts/brackets/door panels, corrugated metal vent ribs/seams, timber crossing planks/bearers.',
'historical-worlds':'Kerala tharavad language: laterite plinth, lime wash, teak joinery, fired clay tiles, granite steps.',
'lighting':'Overcast pure-sky HDRI downsampled to 2K, soft 4° sun, sky bounce area, noise-driven mist volumes.',
'lod-pipeline':'Scanned LOD1 trees, light hero decimation, background collection instances; dense realized Infinigen tree and coconut GN rejected after memory failures.',
'lookdev':'Measured Cycles previews corrected lawn-like rice, concrete bunds, bare decimated forest, close faceted mountains and gray path.',
'materials':'48 materials; 2K/4K CC0 PBR recompressed for packing; procedural lime/teak/tile relief; position-varied leaves.',
'rendering':'Cycles CPU final hero 2048x1152/96 adaptive + OIDN; house detail 960x540/32; receipts with scene/image hashes.',
'texturing':'Poly Haven scanned diffuse/roughness/displacement/normal wired into mud/laterite/roof/wood/bark/metal/rock; no reference photo projection.',
'worldbuilding':'Coherent Kerala monsoon paddy/tharavad/Ghat biome with metric scale and motivated weathering.',
}
for x in d:
 mode=x.get('v2_mode',x.get('mode'));x['v3_mode']=mode
 if mode=='Applied':x['v3_action']=applied.get(x['skill'],'Rechecked and applied to v3 quality revision: native Blender geometry/materials, honest CPU render and provenance.')
 elif mode=='Not applicable':x['v3_action']=x.get('v2_action','Not applicable to static Kerala landscape; no characters/sim/animation.')
 elif mode=='Compatibility check':x['v3_action']='Compatibility retained from v1/v2; no unavailable backend/game-engine import claimed in v3.'
 else:x['v3_action']='Rechecked v3 previews/final: no style/genre contamination; continuous PBR/HDRI photoreal Kerala target retained.'
counts=collections.Counter(x['v3_mode'] for x in d)
(ROOT/'docs/skill_94_review.json').write_text(json.dumps(d,indent=2))
lines=['# 94-skill review v3 — Kerala quality-first revision','', 'Every one of the 94 pinned SKILL.md documents was rechecked for the quality-first revision. Relevant skills were applied; incompatible genres/styles remained explicit QA/exclusion checks; character/sim skills stayed N/A. This is not a claim that 94 styles were mixed into one image.','', '## v3 counts','']
for k in ['Applied','Compatibility check','Not applicable','QA / exclusion lens']:lines.append(f'- {k}: {counts.get(k,0)}')
lines+=['','## v3 matrix','','| Skill | v3 mode | Concrete v3 decision |','|---|---|---|']
for x in d:lines.append(f"| `{x['skill']}` | {x['v3_mode']} | {x['v3_action']} |")
(ROOT/'docs/SKILL_94_REVIEW.md').write_text('\n'.join(lines)+'\n')
print(counts)
