"""Render an original toy-scale research manor. No external assets or .blend files.

Usage:
  /Applications/Blender.app/Contents/MacOS/Blender --factory-startup --background \
      --python scripts/render_manor.py
Outputs site/static/manor-hero.webp. Pass -- --guide to also render an alpha avatar.
"""
from pathlib import Path
import math
import sys
import tempfile
import subprocess
import shutil

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'site' / 'static'
GUIDE = '--guide' in sys.argv
EXPORT_SCENE = '--export-scene' in sys.argv
if not bpy.app.background or bpy.data.filepath:
    raise RuntimeError("Render the manor in a new Blender background process with --factory-startup.")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


def rgba(hexcode):
    text = hexcode.lstrip('#')
    rgb = [int(text[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v < .04045 else ((v+.055)/1.055)**2.4 for v in rgb)+(1,)


def material(name, color, rough=.55, metal=0, transmission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=rgba(color)
    p.inputs['Roughness'].default_value=rough
    p.inputs['Metallic'].default_value=metal
    p.inputs['Transmission Weight'].default_value=transmission
    return m

M={
 'sky':material('powder-blue backdrop','#dceefd'),
 'grass':material('sage velvet grass','#8ebd9c'), 'base':material('mint ceramic base','#b5d0b4'),
 'cream':material('warm ivory porcelain','#fff3d8'), 'wall':material('apricot library plaster','#efcba4'),
 'roof':material('amber glazed clay','#d99d55'), 'rooflight':material('sunny clay seam','#e9b76b'),
 'teal':material('muted research teal','#598f95'), 'dark':material('deep teal trim','#3d686c'),
 'glass':material('lilac translucent greenhouse','#b3b5e4',.22,0,.35),
 'glass2':material('cornflower glass roof','#a4c7e2',.24,0,.30),
 'frame':material('lavender ivory greenhouse frame','#d7d9f0'),
 'leaf':material('soft jade tree canopy','#75a884'), 'leaf2':material('sunlit mint canopy','#9cc49c'),
 'bark':material('caramel trunk','#a77c59'), 'stone':material('warm limestone path','#efe3c5'),
 'crystal':material('blue research crystal','#8dcbd9',.3), 'pink':material('rose crystal','#d0a8c5',.4),
 'gold':material('brass details','#d0a663',.36,.25),
 'skin':material('peach porcelain skin','#f3d3b8',.62),
 'hair':material('mocha toy hair','#59483f'), 'hairlight':material('warm mocha locks','#70594c'),
 'eye':material('espresso eyes','#352e2d',.3), 'white':material('frosted labcoat','#faf5e9',.68),
 'blush':material('warm blush','#e9b0a9',.7), 'pants':material('ink blue trousers','#536b83'),
 'shoe':material('brown scholar shoes','#715b50'), 'paper':material('warm book paper','#f8eccf'),
 'ink':material('muted printed book lines','#b2a483'),
}
CHAR=[]


def finish(obj, name, mat, bevel=0, smooth=False, character=False):
    obj.name=name;obj.data.materials.append(mat)
    if bevel:
        mod=obj.modifiers.new('Soft toy edge','BEVEL');mod.width=bevel;mod.segments=2 if EXPORT_SCENE else 3
        obj.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    if smooth and hasattr(obj.data,'polygons'):
        for p in obj.data.polygons:p.use_smooth=True
    if character:CHAR.append(obj)
    return obj


def cube(name, loc, dims, mat, bevel=.05, rot=None, character=False):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object;o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if rot:o.rotation_euler=rot
    return finish(o,name,mat,bevel,character=character)


def sphere(name, loc, scale, mat, character=False):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16 if EXPORT_SCENE else 40,ring_count=10 if EXPORT_SCENE else 24,location=loc)
    o=bpy.context.object;o.scale=scale
    return finish(o,name,mat,smooth=True,character=character)


def cylinder(name, loc, radius, depth, mat, vertices=48, character=False):
    bpy.ops.mesh.primitive_cylinder_add(vertices=min(vertices,16) if EXPORT_SCENE else vertices,radius=radius,depth=depth,location=loc)
    return finish(bpy.context.object,name,mat,.035,smooth=True,character=character)


def rod(name, a, b, radius, mat, character=False):
    middle=(Vector(a)+Vector(b))/2;direction=Vector(b)-Vector(a)
    o=cylinder(name,middle,radius,direction.length,mat,24,character)
    o.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
    return o


def mesh(name, verts, faces, mat, bevel=0, character=False):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    return finish(obj,name,mat,bevel,character=character)


def curve(name, coords, radius, mat, character=False):
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.resolution_u=4 if EXPORT_SCENE else 16
    p=d.splines.new('BEZIER');p.bezier_points.add(len(coords)-1)
    for point,co in zip(p.bezier_points,coords):point.co=co;point.handle_left_type='AUTO';point.handle_right_type='AUTO'
    d.bevel_depth=radius;d.bevel_resolution=2 if EXPORT_SCENE else 4
    obj=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(obj);obj.data.materials.append(mat)
    if character:CHAR.append(obj)
    return obj


def arch(name,x,y,z,width,height,mat):
    r=width/2;bottom=z-height/2;shoulder=z+height/2-r
    shape=[(x-r,bottom),(x+r,bottom)]
    shape += [(x+r*math.cos(t),shoulder+r*math.sin(t)) for t in [i*math.pi/24 for i in range(25)]]
    verts=[(xx,y,zz) for xx,zz in shape]+[(xx,y+.10,zz) for xx,zz in shape]
    n=len(shape);faces=[tuple(range(n)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,verts,faces,mat,.025)


# Pillowed, floating garden plinth with a matte sky-blue ground.
cube('Rounded ceramic garden plinth',(0,0,.02),(8.8,6.8,.46),M['base'],.40)
cube('Sage lawn surface',(0,0,.26),(8.48,6.48,.16),M['grass'],.35)
cube('Infinite blue studio floor',(0,0,-.48),(200,200,.1),M['sky'],.01)

# Small original library: orange gables, arched windows, a book emblem.
lx,ly=-1.75,.85
cube('Apricot research library',(lx,ly,1.62),(2.65,2.20,2.55),M['wall'],.10)
cube('Library limestone foundation',(lx,ly,.47),(2.86,2.38,.30),M['cream'],.07)
roofverts=[(lx-1.57,ly-1.37,2.87),(lx+1.57,ly-1.37,2.87),(lx,ly-1.37,3.85),
           (lx-1.57,ly+1.37,2.87),(lx+1.57,ly+1.37,2.87),(lx,ly+1.37,3.85)]
roof=mesh('Solid amber gabled roof',roofverts,[(0,3,5,2),(2,5,4,1),(0,2,1),(3,4,5),(0,1,4,3)],M['roof'],.055)
for i in range(8):
    yy=ly-1.31+i*.375
    rod('Raised clay roof seam L',(lx-1.53,yy,2.91),(lx,yy,3.89),.022,M['rooflight'])
    rod('Raised clay roof seam R',(lx,yy,3.89),(lx+1.53,yy,2.91),.022,M['rooflight'])
arch('Ivory arched doorway',lx,ly-1.16,1.23,.87,1.72,M['cream'])
arch('Teal library front door',lx,ly-1.21,1.20,.67,1.52,M['teal'])
sphere('Brass doorknob',(lx+.20,ly-1.28,1.15),(.065,.045,.065),M['gold'])
for xx in [lx-.91,lx+.91]:
    arch('Ivory arched window',xx,ly-1.17,1.96,.59,.92,M['cream'])
    arch('Teal window glass',xx,ly-1.23,1.96,.43,.74,M['teal'])
    cube('Window mullion',(xx,ly-1.30,1.93),(.045,.04,.69),M['cream'],.01)
    cube('Window sill',(xx,ly-1.28,1.53),(.74,.25,.10),M['cream'],.03)
# Side windows on visible east wall.
for yy in [ly-.53,ly+.55]:
    cube('Library east window frame',(lx+1.36,yy,1.90),(.10,.69,.82),M['cream'],.06)
    cube('Library east teal panes',(lx+1.42,yy,1.90),(.03,.52,.64),M['teal'],.03)
    cube('Library east mullion',(lx+1.45,yy,1.90),(.04,.035,.66),M['cream'],.01)
# Book-shaped crest, no generated text.
cube('Library book crest backing',(lx,ly-1.40,3.14),(.67,.09,.43),M['cream'],.08)
for sign in [-1,1]:
    cube('Book crest page',(lx+sign*.14,ly-1.46,3.15),(.24,.04,.26),M['dark'],.025,rot=(0,0,sign*.04))
cube('Library chimney',(lx-.8,ly+.65,3.65),(.40,.43,1.0),M['wall'],.05)
cube('Chimney cap',(lx-.8,ly+.65,4.14),(.53,.55,.12),M['cream'],.035)

LIBRARY = [o for o in bpy.context.scene.objects if o.name not in ('Rounded ceramic garden plinth','Sage lawn surface','Infinite blue studio floor')]

# Blue-violet crystal greenhouse, with open-looking front and thick ivory ribs.
gx,gy=1.85,1.15;w,d=2.55,2.25;floor=.43;walltop=2.30;peak=3.17
cube('Greenhouse pale lavender foundation',(gx,gy,.46),(w+.18,d+.20,.24),M['frame'],.10)
for side in [-1,1]:
    cube('Frosted blue side glass',(gx+side*w/2,gy,1.43),(.055,d,1.70),M['glass2'],.025)
    cube('Rear lilac glass',(gx,gy+d/2,1.43),(w,.055,1.70),M['glass'],.025)
for xx in [gx-w/2,gx,gx+w/2]:
    for yy in [gy-d/2,gy+d/2]:rod('Greenhouse ivory upright',(xx,yy,.52),(xx,yy,walltop),.065,M['frame'])
for xx in [gx-w/2,gx+w/2]:
    for yy in [gy-.4,gy+.4]:rod('Greenhouse side rib',(xx,yy,.52),(xx,yy,walltop),.045,M['frame'])
    rod('Greenhouse top side rail',(xx,gy-d/2,walltop),(xx,gy+d/2,walltop),.065,M['frame'])
for yy in [gy-d/2,gy+d/2]:
    rod('Greenhouse eave',(gx-w/2,yy,walltop),(gx+w/2,yy,walltop),.065,M['frame'])
    rod('Greenhouse gable L',(gx-w/2,yy,walltop),(gx,yy,peak),.07,M['frame'])
    rod('Greenhouse gable R',(gx,yy,peak),(gx+w/2,yy,walltop),.07,M['frame'])
rod('Greenhouse ridge',(gx,gy-d/2,peak),(gx,gy+d/2,peak),.075,M['frame'])
for side in [-1,1]:
    mesh('Blue-purple glass roof',[(gx+side*w/2,gy-d/2,walltop),(gx,gy-d/2,peak),
          (gx,gy+d/2,peak),(gx+side*w/2,gy+d/2,walltop)],[(0,1,2,3)],M['glass2'])
    for yy in [gy-.38,gy+.38]:rod('Thin roof glazing rib',(gx+side*w/2,yy,walltop),(gx,yy,peak),.035,M['frame'])
# Front half-panel leaves the crystal display readable.
for xx in [gx-.98,gx+.98]:cube('Greenhouse low lilac front panel',(xx,gy-d/2,1.09),(.52,.055,1.15),M['glass'],.03)


def crystal(name,loc,radius,height,mat):
    x,y,z=loc;n=6
    verts=[(x+radius*math.cos(i*2*math.pi/n),y+radius*math.sin(i*2*math.pi/n),z+height*.22) for i in range(n)]
    verts += [(x+radius*.70*math.cos(i*2*math.pi/n),y+radius*.70*math.sin(i*2*math.pi/n),z+height*.78) for i in range(n)]
    verts += [(x,y,z),(x+.06,y-.04,z+height)]
    faces=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]+[(i+n,(i+1)%n+n,2*n+1) for i in range(n)]+[(i,(i+1)%n,2*n) for i in range(n)]
    return mesh(name,verts,faces,mat,.012)

cube('Crystal display table',(gx,gy-.18,.85),(1.70,1.05,.16),M['cream'],.06)
for xx in [gx-.64,gx+.64]:rod('Display table leg',(xx,gy-.1,.54),(xx,gy-.1,.83),.07,M['gold'])
crystal('Tall faceted cyan laboratory crystal',(gx+.10,gy-.17,.94),.32,1.18,M['crystal'])
crystal('Small pink companion crystal',(gx-.52,gy-.35,.94),.21,.73,M['pink'])
crystal('Warm honey crystal',(gx+.56,gy-.3,.94),.19,.56,M['gold'])

# Toy trees and garden shrubs.
def tree(x,y,height=2.7):
    rod('Rounded caramel tree trunk',(x,y,.35),(x,y,height*.70),.13,M['bark'])
    for dx,dy,dz,sc in [(-.32,0,-.05,.70),(.27,.03,.1,.75),(0,.06,.57,.66)]:
        sphere('Soft toy tree crown',(x+dx,y+dy,height+dz),(sc,sc*.82,sc*.95),M['leaf2'] if dx>0 else M['leaf'])
for args in [(-3.45,1.9,2.40),(-2.8,2.75,2.55),(3.30,2.55,2.40)]:tree(*args)
for xx,yy in [(-3.30,-.95),(3.36,.03),(3.45,1.0),(-3.6,2.65)]:
    sphere('Low rounded garden shrub',(xx,yy,.59),(.42,.36,.37),M['leaf2'])
for xx,yy in [(-1.75,-.62),(-1.9,-1.2),(-2.1,-1.81),(-2.28,-2.43)]:
    stone=cylinder('Circular stepping stone',(xx,yy,.39),.29,.10,M['stone']);stone.scale.y=.78
# Tiny flowers, white and buttercup.
for xx,yy in [(-3.28,-1.9),(-3.0,-2.2),(3.25,-.8),(3.55,-.65)]:
    rod('Tiny flower stem',(xx,yy,.36),(xx,yy,.63),.018,M['dark'])
    for a in range(5):sphere('Buttercup petal',(xx+.065*math.cos(a*math.tau/5),yy+.065*math.sin(a*math.tau/5),.64),(.058,.058,.036),M['cream'])
    sphere('Buttercup center',(xx,yy,.67),(.038,.038,.03),M['gold'])

# Closed books on the lawn, their pages are distinct from covers.
for idx,(color,angle) in enumerate([('dark',-.12),('roof',.10),('pink',-.05)]):
    zz=.43+idx*.19
    cube('Research book pages',(-2.92,-2.57,zz+.09),(.84,.52,.13),M['paper'],.025,rot=(0,0,angle))
    for dz in [0,.17]:cube('Research book cover',(-2.92,-2.57,zz+dz),(.92,.58,.045),M[color],.02,rot=(0,0,angle))

# Brass tripod and blue telescope, aimed toward the roofline sky.
base=(2.85,-1.75,.40);pivot=(2.85,-1.75,1.50)
for dx,dy in [(-.43,-.22),(.4,-.20),(0,.43)]:rod('Telescope brass tripod',(base[0]+dx,base[1]+dy,.40),pivot,.045,M['gold'])
sphere('Telescope pivot',pivot,(.14,.14,.14),M['gold'])
a=Vector((2.61,-1.78,1.52));b=Vector((3.16,-1.39,2.18));v=(b-a).normalized()
rod('Frosted blue telescope tube',a,b,.19,M['teal'])
rod('Ivory telescope lens collar',b-v*.07,b+v*.10,.22,M['cream'])
rod('Sky blue telescope lens',b+v*.10,b+v*.12,.17,M['crystal'])
rod('Telescope dark eyepiece',a-v*.18,a,.10,M['dark'])

# Foreground original chibi scholar. The character faces the viewer, book in hand.
cx,cy=.02,-2.30
for side in [-1,1]:
    rod('Scholar trouser leg',(cx+side*.22,cy,.45),(cx+side*.22,cy,.91),.145,M['pants'],True)
    sphere('Scholar rounded shoe',(cx+side*.23,cy-.09,.46),(.19,.29,.13),M['shoe'],True)
sphere('Pear-shaped frosted lab coat',(cx,cy,1.30),(.48,.34,.65),M['white'],True)
cube('Teal shirt bib',(cx,cy-.335,1.61),(.32,.035,.41),M['teal'],.04,character=True)
# Broad folded lapels and hem seam.
for side in [-1,1]:
    lapel=cube('Ivory labcoat lapel',(cx+side*.20,cy-.35,1.69),(.20,.07,.40),M['white'],.03,character=True)
    lapel.rotation_euler[1]=side*.30
    rod('Coat sleeve',(cx+side*.42,cy,1.68),(cx+side*.58,cy-.20,1.29),.18,M['white'],True)
    rod('Bent coat cuff',(cx+side*.58,cy-.20,1.29),(cx+side*.42,cy-.51,1.39),.16,M['white'],True)
    sphere('Tiny book-holding hand',(cx+side*.43,cy-.57,1.40),(.14,.12,.14),M['skin'],True)
for zz in [.94,1.12]:sphere('Little brass coat button',(cx+.04,cy-.34,zz),(.035,.025,.035),M['gold'],True)
# Small blue pocket, with a gold pen.
cube('Scholar labcoat pocket',(cx+.30,cy-.31,1.12),(.18,.04,.17),M['cream'],.025,character=True)
rod('Pocket pencil',(cx+.32,cy-.34,1.13),(cx+.32,cy-.34,1.36),.018,M['gold'],True)
rod('Scholar neck',(cx,cy,1.75),(cx,cy,2.03),.15,M['skin'],True)
sphere('Large soft peach scholar face',(cx,cy-.02,2.58),(.74,.63,.73),M['skin'],True)
for side in [-1,1]:sphere('Scholar ear',(cx+side*.71,cy-.02,2.56),(.15,.12,.20),M['skin'],True)
# Sculpted hair cap and rounded side locks preserve a clean full face.
sphere('Mocha hair cap',(cx,cy+.02,2.99),(.77,.65,.43),M['hair'],True)
for side in [-1,1]:
    lock=sphere('Rounded temple hair',(cx+side*.62,cy-.12,2.82),(.19,.43,.40),M['hair'],True)
    lock.rotation_euler[1]=side*.20
for xx,zz,angle in [(-.36,3.04,-.35),(-.04,3.11,.18),(.31,3.08,.42)]:
    bang=sphere('Sculpted forehead fringe',(cx+xx,cy-.51,zz),(.27,.15,.25),M['hairlight'] if xx==-.04 else M['hair'],True)
    bang.rotation_euler[1]=angle
curve('Playful scholar hair tuft',[(cx+.15,cy,3.30),(cx+.18,cy-.02,3.52),(cx+.36,cy-.01,3.51)],.055,M['hair'],True)
# Large expressive eyes: dark ovals with tiny porcelain glints.
for side in [-1,1]:
    ex=cx+side*.25
    sphere('Large bright scholar eye',(ex,cy-.606,2.62),(.095,.046,.135),M['eye'],True)
    sphere('Eye light catch',(ex-.026,cy-.648,2.67),(.028,.013,.034),M['white'],True)
    sphere('Soft cheek blush',(cx+side*.43,cy-.560,2.42),(.115,.023,.055),M['blush'],True)
    curve('Gentle eyebrow',[(ex-.09,cy-.586,2.85),(ex,cy-.608,2.88),(ex+.08,cy-.586,2.85)],.021,M['hair'],True)
sphere('Tiny scholar nose',(cx,cy-.66,2.45),(.065,.055,.075),M['skin'],True)
curve('Small smiling mouth',[(cx-.095,cy-.614,2.31),(cx,cy-.641,2.28),(cx+.095,cy-.614,2.31)],.017,M['hairlight'],True)
# Round brass spectacles; the glasses sit around, rather than over, the eyes.
for side in [-1,1]:
    bpy.ops.mesh.primitive_torus_add(major_radius=.185,minor_radius=.014,major_segments=24 if EXPORT_SCENE else 64,minor_segments=6 if EXPORT_SCENE else 12,
        location=(cx+side*.25,cy-.68,2.62),rotation=(math.pi/2,0,0))
    finish(bpy.context.object,'Fine round scholar spectacles',M['gold'],smooth=True,character=True)
curve('Spectacle bridge',[(cx-.065,cy-.68,2.64),(cx,cy-.70,2.67),(cx+.065,cy-.68,2.64)],.014,M['gold'],True)
# Open book with two tilted pages, cover and legible miniature line marks.
for side in [-1,1]:
    xx=cx+side*.205;angle=side*-.18
    cube('Open teal book cover',(xx,cy-.68,1.47),(.43,.065,.55),M['dark'],.025,rot=(0,0,angle),character=True)
    cube('Open ivory book page',(xx,cy-.721,1.48),(.38,.025,.49),M['paper'],.015,rot=(0,0,angle),character=True)
    for zz,length in [(1.63,.22),(1.53,.28),(1.43,.24),(1.33,.19)]:
        cube('Printed book line',(xx,cy-.741,zz),(length,.012,.014),M['ink'],.006,rot=(0,0,angle),character=True)
rod('Gold book spine',(cx,cy-.69,1.20),(cx,cy-.69,1.76),.027,M['gold'],True)

# Large, soft studio illumination.
world=bpy.data.worlds.new('Pastel daylight');bpy.context.scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=rgba('#dceefd')
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65

def light(name,loc,power,size):
    bpy.ops.object.light_add(type='AREA',location=loc);obj=bpy.context.object;obj.name=name;obj.data.energy=power;obj.data.shape='DISK';obj.data.size=size
    obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
light('Large warm window key',(-4,-6,10),1250,7)
light('Cool soft fill',(6,-1,8),750,6)
light('Gentle skylight rim',(-1,5,9),1100,5)

bpy.ops.object.camera_add(location=(9,-16,11.5))
camera=bpy.context.object;camera.name='Manor orthographic portrait camera';camera.data.type='ORTHO';camera.data.ortho_scale=12.4
camera.rotation_euler=(Vector((0,0,1.40))-camera.location).to_track_quat('-Z','Y').to_euler()
scene=bpy.context.scene;scene.camera=camera;scene.render.engine='CYCLES'
scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.cycles.adaptive_threshold=.035
scene.cycles.max_bounces=8;scene.cycles.transmission_bounces=6
scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.render.film_transparent=False
scene.render.image_settings.color_depth='8'
OUT.mkdir(parents=True,exist_ok=True)


def render_webp(name,quality=87):
    with tempfile.TemporaryDirectory(prefix='ai4s-manor-') as temp:
        image=Path(temp)/'render.png';scene.render.filepath=str(image);bpy.ops.render.render(write_still=True)
        target=OUT/(name+'.webp');encoder=shutil.which('cwebp')
        if encoder:
            subprocess.run([encoder,'-quiet','-q',str(quality),'-m','6',str(image),'-o',str(target)],check=True)
        else:
            # Blender also supports WebP; this branch avoids an extra dependency.
            scene.render.image_settings.file_format='WEBP';scene.render.image_settings.quality=quality
            bpy.data.images['Render Result'].save_render(str(target),scene=scene)
            scene.render.image_settings.file_format='PNG'
        print('MANOR_ASSET',target,target.stat().st_size,flush=True)

if not EXPORT_SCENE:
    render_webp('manor-hero')
if GUIDE and not EXPORT_SCENE:
    for obj in list(scene.objects):
        if obj.type not in ('LIGHT','CAMERA') and obj not in CHAR:obj.hide_render=True
    camera.location=(4.2,-12,6.3);camera.data.ortho_scale=4.35
    camera.rotation_euler=(Vector((cx,cy,1.93))-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x=640;scene.render.resolution_y=640
    scene.render.film_transparent=True
    render_webp('manor-guide',90)
