import math, random
import bpy
from mathutils import Vector, noise

def collection(name, parent=None):
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c

def move_to(obj,c):
    for old in list(obj.users_collection): old.objects.unlink(obj)
    c.objects.link(obj)
    return obj

def mesh_obj(name,verts,faces,c,mat=None,smooth=False,materials=None,indices=None):
    m=bpy.data.meshes.new(name+'_Mesh'); m.from_pydata(verts,[],faces); m.update()
    o=bpy.data.objects.new(name,m); c.objects.link(o)
    if materials:
        for mm in materials: m.materials.append(mm)
        if indices:
            for p,i in zip(m.polygons,indices): p.material_index=i
    elif mat: m.materials.append(mat)
    if smooth:
        for p in m.polygons: p.use_smooth=True
    return o

def box(name,loc,dims,c,mat,bevel=0.0,rot=None):
    x,y,z=[v/2 for v in dims]
    v=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    f=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    o=mesh_obj(name,v,f,c,mat); o.location=loc
    if rot: o.rotation_euler=rot
    if bevel:
        b=o.modifiers.new('Small real edge bevel','BEVEL'); b.width=bevel; b.segments=2
    return o

def tube(name,points,radii,c,mat,sides=8):
    pts=[Vector(p) for p in points]; verts=[]; faces=[]
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
        ref=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((1,0,0))
        u=tangent.cross(ref).normalized(); v=tangent.cross(u).normalized()
        r=radii[i] if isinstance(radii,(list,tuple)) else radii
        for j in range(sides):
            a=2*math.pi*j/sides; verts.append(tuple(p+r*(math.cos(a)*u+math.sin(a)*v)))
    for i in range(len(pts)-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides))
    faces.append(tuple(range(sides-1,-1,-1))); faces.append(tuple((len(pts)-1)*sides+j for j in range(sides)))
    return mesh_obj(name,verts,faces,c,mat,True)

def linked_copy(source,name,loc,c,scale=1.0,rot=None):
    o=bpy.data.objects.new(name,source.data); c.objects.link(o); o.location=loc
    o.scale=(scale,scale,scale) if isinstance(scale,(int,float)) else scale
    if rot: o.rotation_euler=rot
    return o

def fbm(x,y,seed=0,octaves=5):
    s=0.;a=.5;f=1.
    for i in range(octaves):
        s+=a*noise.noise(Vector((x*f,y*f,seed+i*13.7)));a*=.5;f*=2.03
    return s

def path_x(y):
    from kerala_config import PATH_NODES
    if y<=PATH_NODES[0][1]: return PATH_NODES[0][0]
    if y>=PATH_NODES[-1][1]: return PATH_NODES[-1][0]
    for i in range(len(PATH_NODES)-1):
        x0,y0=PATH_NODES[i];x1,y1=PATH_NODES[i+1]
        if y0<=y<=y1:
            t=(y-y0)/(y1-y0)
            xm0=(PATH_NODES[i+1][0]-PATH_NODES[max(i-1,0)][0])/(PATH_NODES[i+1][1]-PATH_NODES[max(i-1,0)][1])
            xm1=(PATH_NODES[min(i+2,len(PATH_NODES)-1)][0]-PATH_NODES[i][0])/(PATH_NODES[min(i+2,len(PATH_NODES)-1)][1]-PATH_NODES[i][1])
            h=t*t*(3-2*t)
            return (2*t**3-3*t*t+1)*x0+(t**3-2*t*t+t)*(y1-y0)*xm0+(-2*t**3+3*t*t)*x1+(t**3-t*t)*(y1-y0)*xm1

def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def scatter_group(name,library,count):
    ng=bpy.data.node_groups.new(name,'GeometryNodeTree')
    ng.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
    ng.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    for nm,typ,default,lo,hi in [('Density','NodeSocketFloat',1.0,0.0,1.0),('Seed','NodeSocketInt',0,0,100000),('Scale Min','NodeSocketFloat',.8,0.01,5.0),('Scale Max','NodeSocketFloat',1.2,0.01,5.0)]:
        s=ng.interface.new_socket(name=nm,in_out='INPUT',socket_type=typ);s.default_value=default;s.min_value=lo;s.max_value=hi
    n=ng.nodes; l=ng.links
    gi=n.new('NodeGroupInput');gi.location=(-700,100)
    go=n.new('NodeGroupOutput');go.location=(650,100)
    m2p=n.new('GeometryNodeMeshToPoints');m2p.mode='VERTICES';m2p.location=(-480,180);l.new(gi.outputs['Geometry'],m2p.inputs['Mesh'])
    ci=n.new('GeometryNodeCollectionInfo');ci.location=(-480,-80);ci.inputs['Collection'].default_value=library;ci.inputs['Separate Children'].default_value=True;ci.inputs['Reset Children'].default_value=True;ci.transform_space='ORIGINAL'
    iop=n.new('GeometryNodeInstanceOnPoints');iop.location=(380,120);iop.inputs['Pick Instance'].default_value=True
    l.new(m2p.outputs['Points'],iop.inputs['Points']);l.new(ci.outputs['Instances'],iop.inputs['Instance'])
    sel=n.new('FunctionNodeRandomValue');sel.data_type='BOOLEAN';sel.location=(-220,330);l.new(gi.outputs['Density'],sel.inputs['Probability']);l.new(gi.outputs['Seed'],sel.inputs['Seed']);l.new(sel.outputs['Value'],iop.inputs['Selection'])
    idx=n.new('FunctionNodeRandomValue');idx.data_type='INT';idx.location=(-220,100);idx.inputs['Min'].default_value=0;idx.inputs['Max'].default_value=max(0,count-1);l.new(gi.outputs['Seed'],idx.inputs['Seed']);l.new(idx.outputs['Value'],iop.inputs['Instance Index'])
    rot=n.new('FunctionNodeRandomValue');rot.data_type='FLOAT_VECTOR';rot.location=(80,-100);rot.inputs['Min'].default_value=(-.035,-.035,0);rot.inputs['Max'].default_value=(.035,.035,6.283185);l.new(gi.outputs['Seed'],rot.inputs['Seed']);l.new(rot.outputs['Value'],iop.inputs['Rotation'])
    sc=n.new('FunctionNodeRandomValue');sc.data_type='FLOAT';sc.location=(80,-320);l.new(gi.outputs['Scale Min'],sc.inputs['Min']);l.new(gi.outputs['Scale Max'],sc.inputs['Max']);l.new(gi.outputs['Seed'],sc.inputs['Seed']);l.new(sc.outputs['Value'],iop.inputs['Scale'])
    l.new(iop.outputs['Instances'],go.inputs['Geometry'])
    return ng

def scatter_points(name,points,c,ng,seed,density=1.,smin=.8,smax=1.2):
    o=mesh_obj(name,points,[],c)
    md=o.modifiers.new('Editable non-realized instances','NODES');md.node_group=ng
    for s in ng.interface.items_tree:
        if s.item_type=='SOCKET' and s.in_out=='INPUT':
            if s.name=='Seed':md[s.identifier]=seed
            elif s.name=='Density':md[s.identifier]=density
            elif s.name=='Scale Min':md[s.identifier]=smin
            elif s.name=='Scale Max':md[s.identifier]=smax
    o['instance_points']=len(points);o['realized']=False
    return o
