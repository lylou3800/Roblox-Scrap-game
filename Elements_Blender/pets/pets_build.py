# pets_build.py — Procedural Blender build of the 10 UFO-Catchers pets (arcade-industrial mascots).
# Run inside Blender (5.x). Each pet = a small, well-proportioned creature, ~3 units tall, feet on Z=0,
# centered on X/Y. Built from primitives then JOINED into "one object per color zone" (the validated
# Blender->Roblox pipeline: separate object per color zone -> upload each as a MeshPart, reassemble).
# Blender Z = up -> Roblox Y (up). Front of the creature faces +X. Y = left/right.
#
# Roster (ids match ReplicatedStorage.Shared.Config.Pets[*].model):
#   bunny_plush, bolt_bot, foam_cube, windup_duck, neon_kitten,
#   magnet_drone, golden_teddy, mini_clawbot, holo_fox, ufo_mascot
#
# Usage in Blender:  exec(open(r"<path>/pets_build.py").read())
#   build_all()                 -> builds every pet in its own collection, laid out in a grid
#   build_one("bunny_plush")    -> builds a single pet at the origin
#   render_contact(r"out.png")  -> renders a top-down-ish contact sheet of the grid
#   save_blend(r"pets.blend")   -> saves the .blend

import bpy, bmesh, math
from mathutils import Vector

# ---------------------------------------------------------------- scene utils
def reset():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
    for mat in list(bpy.data.materials): bpy.data.materials.remove(mat)

def _apply(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# ---------------------------------------------------------------- primitives
# Every primitive helper returns (object, color). color is an (r,g,b) 0..1 tuple used later to
# group parts into color zones. Positions are set by the caller via place()/rot().

def sphere(rx, ry, rz, color, segs=28, rings=18):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=segs, ring_count=rings)
    o = bpy.context.active_object
    o.scale = (rx, ry, rz); _apply(o)
    bpy.ops.object.shade_smooth()
    return (o, color)

def box(sx, sy, sz, color, bevel=0.08, segs=2, smooth=False):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    o = bpy.context.active_object
    o.scale = (sx/2, sy/2, sz/2); _apply(o)
    if bevel > 0:
        m = o.modifiers.new("b", 'BEVEL'); m.width = bevel; m.segments = segs; m.limit_method = 'ANGLE'
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier=m.name)
    if smooth: bpy.ops.object.shade_smooth()
    return (o, color)

def cyl(r, h, color, axis='Z', verts=24, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts)
    o = bpy.context.active_object
    if axis == 'X': o.rotation_euler = (0, math.radians(90), 0)
    elif axis == 'Y': o.rotation_euler = (math.radians(90), 0, 0)
    _apply(o)
    if bevel > 0:
        m = o.modifiers.new("b", 'BEVEL'); m.width = bevel; m.segments = 2; m.limit_method = 'ANGLE'
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.ops.object.shade_smooth()
    return (o, color)

def cone(r1, r2, h, color, axis='Z', verts=24):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=h, vertices=verts)
    o = bpy.context.active_object
    if axis == 'X': o.rotation_euler = (0, math.radians(90), 0)
    elif axis == 'Y': o.rotation_euler = (math.radians(90), 0, 0)
    _apply(o)
    bpy.ops.object.shade_smooth()
    return (o, color)

def torus(R, r, color, axis='Z', major=28, minor=14):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=major, minor_segments=minor)
    o = bpy.context.active_object
    if axis == 'X': o.rotation_euler = (0, math.radians(90), 0)
    elif axis == 'Y': o.rotation_euler = (math.radians(90), 0, 0)
    _apply(o)
    bpy.ops.object.shade_smooth()
    return (o, color)

# ---------------------------------------------------------------- transforms
def place(part, x, y, z):
    o = part[0]; o.location = (x, y, z); return part

def rot(part, rx, ry, rz):
    o = part[0]; o.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz)); _apply(o); return part

def scale(part, sx, sy, sz):
    o = part[0]; o.scale = (sx, sy, sz); _apply(o); return part

def squash(part, frac, axis='Z'):
    # flatten a sphere/part along one axis after creation (e.g. a domed belly)
    o = part[0]
    bm = bmesh.new(); bm.from_mesh(o.data)
    for v in bm.verts:
        if axis == 'Z' and v.co.z < 0: v.co.z *= frac
        if axis == 'Z' and v.co.z > 0 and frac > 1: v.co.z *= 1
    bm.to_mesh(o.data); bm.free(); return part

# Build a left+right mirrored pair (for ears/eyes/legs). Returns [left, right] as two parts (same color).
def pair(part_factory, x, y, z, **kw):
    a = part_factory(); place(a, x,  y, z)
    b = part_factory(); place(b, x, -y, z)
    return [a, b]

# ---------------------------------------------------------------- materials / assemble
def _mat(color, rough, metal, emis):
    key = "m_%0.2f_%0.2f_%0.2f_%0.2f_%0.2f" % (color[0], color[1], color[2], rough, metal)
    m = bpy.data.materials.get(key)
    if m: return m
    m = bpy.data.materials.new(key); m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emis is not None:
        try:
            bsdf.inputs["Emission Color"].default_value = (emis[0], emis[1], emis[2], 1.0)
            bsdf.inputs["Emission Strength"].default_value = 1.5
        except Exception: pass
    m.diffuse_color = (color[0], color[1], color[2], 1.0)  # viewport solid
    return m

def assemble(name, parts, mats=None):
    """parts = flat list of (obj,color). Joins all parts sharing the same color into one object
    named '<name>_z<i>'. Seats the assembly so min Z = 0 and centers X/Y. Puts everything in a
    collection named <name>. mats: optional {colortuple: (rough,metal,emis)} for finish overrides."""
    mats = mats or {}
    # group by rounded color
    groups = {}
    for o, c in parts:
        key = (round(c[0],3), round(c[1],3), round(c[2],3))
        groups.setdefault(key, []).append(o)
    coll = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(coll)
    zones = []
    for i, (key, objs) in enumerate(groups.items()):
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        z = bpy.context.active_object; z.name = "%s_z%d" % (name, i)
        rough, metal, emis = mats.get(key, (0.55, 0.0, None))
        z.data.materials.clear(); z.data.materials.append(_mat(key, rough, metal, emis))
        zones.append(z)
    # seat + center the whole assembly
    mins = Vector(( 1e9,  1e9,  1e9)); maxs = Vector((-1e9, -1e9, -1e9))
    for z in zones:
        for corner in z.bound_box:
            w = z.matrix_world @ Vector(corner)
            mins.x=min(mins.x,w.x); mins.y=min(mins.y,w.y); mins.z=min(mins.z,w.z)
            maxs.x=max(maxs.x,w.x); maxs.y=max(maxs.y,w.y); maxs.z=max(maxs.z,w.z)
    cx = (mins.x+maxs.x)/2; cy = (mins.y+maxs.y)/2
    for z in zones:
        z.location.x -= cx; z.location.y -= cy; z.location.z -= mins.z
    # move zones into the pet collection (out of scene root)
    for z in zones:
        for c in list(z.users_collection): c.objects.unlink(z)
        coll.objects.link(z)
    return coll

# ---------------------------------------------------------------- registry
BUILDERS = {}
def builder(name):
    def deco(fn): BUILDERS[name] = fn; return fn
    return deco

ROSTER = ["bunny_plush","bolt_bot","foam_cube","windup_duck","neon_kitten",
          "magnet_drone","golden_teddy","mini_clawbot","holo_fox","ufo_mascot"]

def build_one(name):
    parts, mats = BUILDERS[name]()
    return assemble(name, parts, mats)

def build_all():
    reset()
    cols = 5
    for i, name in enumerate(ROSTER):
        coll = build_one(name)
        gx = (i % cols) * 5.0; gy = (i // cols) * 5.0
        for o in coll.objects: o.location.x += gx; o.location.y += gy

def render_contact(path, res=1400):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    sc.render.resolution_x = res; sc.render.resolution_y = int(res*0.5)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

def save_blend(path):
    bpy.ops.wm.save_as_mainfile(filepath=path)

# ================================================================ PET BUILDERS
# Each builder returns (parts, mats). parts = flat list of (obj,color). mats keyed by rounded color
# tuple -> (roughness, metallic, emission_rgb_or_None). Build with FRONT facing +X.

# palette helpers
def C(r,g,b): return (r/255.0, g/255.0, b/255.0)
BLACK = C(28,28,32); WHITE = C(245,245,248)

@builder("bunny_plush")
def _bunny():
    # Plush bunny: cream fur, pink inner-ears + nose, black bead eyes, blush cheeks. Stylized chibi.
    fur   = C(247,240,230)
    pink  = C(243,170,190)
    parts = []
    # body (egg, fat) + head (big, chibi)
    parts.append(place(sphere(0.95,0.85,1.05, fur), 0,0,1.05))
    parts.append(place(sphere(1.05,1.0,0.95, fur), 0.15,0,2.45))
    # ears (long, leaning back), inner ears pink
    for s in (1,-1):
        parts.append(rot(place(sphere(0.22,0.16,0.9, fur), -0.1, s*0.42, 3.4), 0,-12,0))
        parts.append(rot(place(sphere(0.12,0.09,0.7, pink), -0.02, s*0.42, 3.45), 0,-12,0))
    # muzzle + nose + eyes + cheeks
    parts.append(place(sphere(0.42,0.5,0.36, fur), 0.95,0,2.25))
    parts.append(place(sphere(0.12,0.14,0.1, pink), 1.32,0,2.32))
    for s in (1,-1):
        parts.append(place(sphere(0.13,0.08,0.16, BLACK), 1.02, s*0.4, 2.62))
        parts.append(place(sphere(0.16,0.05,0.12, pink), 1.0, s*0.62, 2.32))
    # feet + tail
    for s in (1,-1):
        parts.append(place(sphere(0.34,0.28,0.22, fur), 0.55, s*0.45, 0.22))
    parts.append(place(sphere(0.3,0.3,0.3, WHITE), -0.85,0,1.1))
    mats = { (round(fur[0],3),round(fur[1],3),round(fur[2],3)): (0.85,0.0,None),
             (round(BLACK[0],3),round(BLACK[1],3),round(BLACK[2],3)): (0.25,0.0,None) }
    return parts, mats

@builder("ufo_mascot")
def _ufo():
    # OVNI mascotte: chrome saucer + glowing dome with a little green alien face, tri leg pods.
    chrome = C(196,205,214); dome = C(120,225,255); green = C(150,235,150); glow = C(255,225,90)
    parts = []
    # saucer disc (flattened sphere) + rim torus
    parts.append(squash(place(sphere(1.5,1.5,0.55, chrome), 0,0,1.2), 0.6))
    parts.append(place(torus(1.45,0.18, chrome, axis='Z'), 0,0,1.15))
    # glass dome
    parts.append(squash(place(sphere(0.85,0.85,0.95, dome), 0,0,1.55), 1.0))
    # alien head + eyes inside dome
    parts.append(place(sphere(0.4,0.36,0.46, green), 0.05,0,1.95))
    for s in (1,-1):
        parts.append(rot(place(sphere(0.16,0.06,0.22, BLACK), 0.28, s*0.16, 2.0), 0,0,s*18))
    # underside glow lights (3) + landing pods
    for k in range(3):
        a = math.radians(90 + k*120)
        parts.append(place(sphere(0.16,0.16,0.16, glow), math.cos(a)*0.95, math.sin(a)*0.95, 0.85))
        parts.append(place(cone(0.22,0.1,0.5, chrome, axis='Z'), math.cos(a)*1.1, math.sin(a)*1.1, 0.28))
    mats = {
        (round(chrome[0],3),round(chrome[1],3),round(chrome[2],3)): (0.18,0.9,None),
        (round(dome[0],3),round(dome[1],3),round(dome[2],3)): (0.1,0.0,dome),
        (round(glow[0],3),round(glow[1],3),round(glow[2],3)): (0.3,0.0,glow),
        (round(green[0],3),round(green[1],3),round(green[2],3)): (0.5,0.0,None),
    }
    return parts, mats

@builder("bolt_bot")
def _bolt_bot():
    steel = C(150,160,172); dark = C(78,86,98); glow = C(255,150,40)
    parts = []
    # hex-nut body (low-vert cylinder = 6-sided hex), gunmetal steel
    parts.append(rot(place(cyl(1.25, 1.0, steel, axis='Z', verts=6, bevel=0.06), 0,0,0.7), 0,0,30))
    # central bolt-hole ring on the nut (dark accent)
    parts.append(place(torus(0.42, 0.14, dark, axis='Z'), 0,0,1.22))
    # rounded head, steel
    parts.append(place(sphere(0.95,0.9,0.85, steel), 0.05,0,2.05))
    # face plate band, dark gunmetal
    parts.append(place(squash(sphere(0.82,0.82,0.55, dark), 0.7), 0.45,0,2.05))
    # two glowing eyes
    for s in (1,-1):
        parts.append(place(sphere(0.2,0.16,0.2, glow), 0.78, s*0.32, 2.12))
        parts.append(place(sphere(0.09,0.07,0.09, BLACK), 0.92, s*0.32, 2.12))
    # stubby arms, dark
    for s in (1,-1):
        parts.append(rot(place(cyl(0.18,0.7, dark, axis='Y'), 0.1, s*1.15, 1.0), 0,0,0))
        parts.append(place(sphere(0.26,0.26,0.26, steel), 0.1, s*1.5, 1.0))
    # little feet, dark
    for s in (1,-1):
        parts.append(place(box(0.5,0.42,0.3, dark, bevel=0.1), 0.1, s*0.55, 0.18))
    # thin antenna + glowing bulb
    parts.append(place(cyl(0.06, 0.7, steel, axis='Z'), -0.1,0,2.95))
    parts.append(place(sphere(0.22,0.22,0.24, glow), -0.1,0,3.4))
    mats = {
        (round(steel[0],3),round(steel[1],3),round(steel[2],3)): (0.3,0.85,None),
        (round(dark[0],3),round(dark[1],3),round(dark[2],3)): (0.35,0.8,None),
        (round(glow[0],3),round(glow[1],3),round(glow[2],3)): (0.2,0.0,glow),
        (round(BLACK[0],3),round(BLACK[1],3),round(BLACK[2],3)): (0.25,0.0,None),
    }
    return parts, mats

@builder("foam_cube")
def _foam_cube():
    foam  = C(150, 230, 215); cheek = C(255, 175, 190); glow = C(255, 235, 120)
    parts = []
    # squishy rounded cube body
    parts.append(box(1.7, 1.6, 1.6, foam, bevel=0.35, smooth=True))
    parts[-1] = place(parts[-1], 0, 0, 1.25)
    # tiny stubby feet
    for s in (1, -1):
        parts.append(place(sphere(0.34, 0.36, 0.26, foam), 0.35, s*0.5, 0.2))
    # small nub arms
    for s in (1, -1):
        parts.append(rot(place(sphere(0.26, 0.22, 0.4, foam), 0.2, s*0.92, 1.15), 0, 0, 0))
    # happy face: two oval eyes
    for s in (1, -1):
        parts.append(place(sphere(0.16, 0.1, 0.24, BLACK), 0.92, s*0.42, 1.55))
        # tiny eye sparkle
        parts.append(place(sphere(0.05, 0.03, 0.06, WHITE), 0.98, s*0.34, 1.66))
    # little smile (flattened torus piece)
    parts.append(rot(squash(place(torus(0.22, 0.06, BLACK, axis='Z'), 0.9, 0, 1.18), 0.45), 0, 90, 0))
    # rosy cheeks
    for s in (1, -1):
        parts.append(place(sphere(0.14, 0.04, 0.11, cheek), 0.9, s*0.66, 1.3))
    # cute antenna bulb on top
    parts.append(place(cyl(0.04, 0.3, foam, axis='Z'), 0, 0, 2.2))
    parts.append(place(sphere(0.16, 0.16, 0.16, glow), 0, 0, 2.45))
    mats = {
        (round(foam[0],3), round(foam[1],3), round(foam[2],3)): (0.85, 0.0, None),
        (round(BLACK[0],3), round(BLACK[1],3), round(BLACK[2],3)): (0.4, 0.0, None),
        (round(glow[0],3), round(glow[1],3), round(glow[2],3)): (0.2, 0.0, glow),
        (round(cheek[0],3), round(cheek[1],3), round(cheek[2],3)): (0.85, 0.0, None),
    }
    return parts, mats

@builder("windup_duck")
def _windup_duck():
    yellow = C(255,214,72); orange = C(248,150,46); steel = C(196,205,214); cheek = C(255,150,160)
    parts = []
    # chubby body
    parts.append(place(sphere(1.0,0.95,1.0, yellow), 0,0,1.05))
    # round head
    parts.append(place(sphere(0.8,0.78,0.82, yellow), 0.18,0,2.45))
    # flat beak
    parts.append(rot(place(cone(0.42,0.1,0.7, orange, axis='X'), 0.95,0,2.32), 0,8,0))
    parts.append(squash(place(sphere(0.34,0.4,0.16, orange), 0.92,0,2.2), 0.5))
    # black bead eyes + white glint
    for s in (1,-1):
        parts.append(place(sphere(0.12,0.08,0.13, BLACK), 0.62, s*0.3, 2.62))
        parts.append(place(sphere(0.05,0.04,0.05, WHITE), 0.68, s*0.27, 2.68))
    # rosy cheeks
    for s in (1,-1):
        parts.append(place(sphere(0.14,0.05,0.11, cheek), 0.66, s*0.5, 2.35))
    # little wings
    for s in (1,-1):
        parts.append(rot(place(sphere(0.2,0.14,0.5, yellow), -0.05, s*0.92, 1.15), 0,0,s*18))
    # webbed feet
    for s in (1,-1):
        parts.append(squash(place(sphere(0.32,0.26,0.12, orange), 0.42, s*0.4, 0.1), 0.6))
    # wind-up key: shaft + crossed key bow on the back
    parts.append(rot(place(cyl(0.1,0.7, steel, axis='X'), -0.95,0,1.7), 0,0,0))
    parts.append(rot(place(box(0.5,0.16,0.16, steel, bevel=0.03), -1.35,0,1.7), 90,0,0))
    parts.append(place(box(0.16,0.16,0.5, steel, bevel=0.03), -1.35,0,1.7))
    mats = {
        (round(yellow[0],3),round(yellow[1],3),round(yellow[2],3)): (0.85,0.0,None),
        (round(orange[0],3),round(orange[1],3),round(orange[2],3)): (0.6,0.0,None),
        (round(steel[0],3),round(steel[1],3),round(steel[2],3)): (0.3,0.85,None),
        (round(BLACK[0],3),round(BLACK[1],3),round(BLACK[2],3)): (0.25,0.0,None),
    }
    return parts, mats

@builder("neon_kitten")
def _neon_kitten():
    body  = C(38, 28, 58); ears = C(58, 44, 86); neon = C(255, 70, 175); eye = C(120, 250, 255)
    parts = []
    # rounded body
    parts.append(squash(place(sphere(0.95, 0.85, 0.9, body), 0, 0, 0.95), 0.75))
    # big rounded head
    parts.append(place(sphere(1.0, 0.95, 0.95, body), 0.2, 0, 2.0))
    # cheeks
    for s in (1, -1):
        parts.append(place(sphere(0.32, 0.3, 0.28, ears), 0.55, s*0.55, 1.7))
    # triangular cat ears (cones), tilted outward
    for s in (1, -1):
        parts.append(rot(place(cone(0.34, 0.04, 0.7, ears, axis='Z'), 0.1, s*0.5, 2.85), 0, 0, 0))
        parts.append(rot(place(cone(0.18, 0.02, 0.45, neon, axis='Z'), 0.12, s*0.5, 2.92), 0, 0, 0))
    # big glowing eyes
    for s in (1, -1):
        parts.append(place(sphere(0.26, 0.1, 0.3, eye), 1.02, s*0.4, 2.05))
        parts.append(place(sphere(0.1, 0.06, 0.14, BLACK), 1.18, s*0.4, 2.05))
    # little nose
    parts.append(place(sphere(0.1, 0.12, 0.08, neon), 1.18, 0, 1.78))
    # forehead neon stripe
    parts.append(rot(place(box(0.06, 0.5, 0.1, neon, bevel=0.02), 1.0, 0, 2.5), 0, 0, 0))
    # body neon stripe bars
    for z in (1.05, 0.7):
        parts.append(rot(place(box(0.06, 0.7, 0.09, neon, bevel=0.02), 0.85, 0, z), 0, 0, 0))
    # curving tail: stacked small spheres arcing up behind
    import math
    for k in range(5):
        a = math.radians(k * 26)
        tx = -0.85 - math.sin(a) * 0.5
        tz = 0.7 + k * 0.32
        r = 0.22 - k * 0.025
        parts.append(place(sphere(r, r, r, body), tx, 0, tz))
    # tail tip neon
    parts.append(place(sphere(0.13, 0.13, 0.13, neon), -1.05, 0, 2.05))
    # paws
    for s in (1, -1):
        parts.append(place(sphere(0.26, 0.22, 0.18, ears), 0.55, s*0.4, 0.18))
    mats = {
        (round(body[0],3), round(body[1],3), round(body[2],3)): (0.5, 0.0, None),
        (round(ears[0],3), round(ears[1],3), round(ears[2],3)): (0.5, 0.0, None),
        (round(neon[0],3), round(neon[1],3), round(neon[2],3)): (0.2, 0.0, neon),
        (round(eye[0],3), round(eye[1],3), round(eye[2],3)): (0.2, 0.0, eye),
        (round(BLACK[0],3), round(BLACK[1],3), round(BLACK[2],3)): (0.25, 0.0, None),
    }
    return parts, mats

@builder("magnet_drone")
def _magnet_drone():
    steel = C(188,198,210); eye = C(120,235,255); red = C(225,60,55); white = C(245,245,248); glow = C(255,210,90)
    parts = []
    # hovering drone core (rounded steel body) sits high
    parts.append(place(sphere(0.95,0.95,0.85, steel), 0,0,2.15))
    # little face plate / brow
    parts.append(squash(place(sphere(0.55,0.6,0.42, steel), 0.55,0,2.3), 0.7))
    # two glowing scanner eyes
    for s in (1,-1):
        parts.append(place(sphere(0.2,0.12,0.2, eye), 0.85, s*0.28, 2.32))
        parts.append(place(sphere(0.09,0.05,0.09, BLACK), 0.95, s*0.28, 2.34))
    # antenna with glow bulb on top
    parts.append(place(cyl(0.06,0.45, steel, axis='Z'), -0.1,0,2.95))
    parts.append(place(sphere(0.16,0.16,0.16, glow), -0.1,0,3.25))
    # spinning ring around the core (tilted torus)
    parts.append(rot(place(torus(1.15,0.1, steel, axis='Z'), 0,0,2.1), 18,12,0))
    # red-and-white horseshoe magnet mounted underneath
    parts.append(place(box(0.7,1.05,0.3, red, bevel=0.12), 0,0,1.2))
    for s in (1,-1):
        parts.append(place(cyl(0.24,0.85, red, axis='Z'), 0, s*0.4, 0.78))
        parts.append(place(cyl(0.24,0.22, white, axis='Z'), 0, s*0.4, 0.3))
    mats = {
        (round(steel[0],3),round(steel[1],3),round(steel[2],3)): (0.3,0.85,None),
        (round(eye[0],3),round(eye[1],3),round(eye[2],3)): (0.2,0.0,eye),
        (round(glow[0],3),round(glow[1],3),round(glow[2],3)): (0.2,0.0,glow),
        (round(red[0],3),round(red[1],3),round(red[2],3)): (0.85,0.0,None),
        (round(white[0],3),round(white[1],3),round(white[2],3)): (0.5,0.0,None),
    }
    return parts, mats

@builder("golden_teddy")
def _golden_teddy():
    gold  = C(232,178,70); amber = C(200,140,48); muzzle = C(247,214,150); pad = C(243,170,120)
    parts = []
    # round chubby body
    parts.append(place(sphere(1.05,0.95,1.1, gold), 0,0,1.15))
    # round head, big
    parts.append(place(sphere(1.0,0.95,0.92, gold), 0.18,0,2.55))
    # ear discs
    for s in (1,-1):
        parts.append(rot(place(sphere(0.34,0.12,0.36, gold), -0.05, s*0.62, 3.25), 0,0,0))
        parts.append(rot(place(sphere(0.18,0.08,0.2, amber), 0.02, s*0.62, 3.25), 0,0,0))
    # snout: flattened sphere
    parts.append(squash(place(sphere(0.46,0.42,0.34, muzzle), 0.95,0,2.4), 0.7))
    # dark nose
    parts.append(place(sphere(0.16,0.13,0.12, BLACK), 1.32,0,2.52))
    # round eyes
    for s in (1,-1):
        parts.append(place(sphere(0.13,0.07,0.15, BLACK), 1.0, s*0.36, 2.78))
    # cheeks
    for s in (1,-1):
        parts.append(place(sphere(0.18,0.1,0.14, pad), 0.92, s*0.5, 2.4))
    # stubby arms
    for s in (1,-1):
        parts.append(place(sphere(0.34,0.3,0.42, gold), 0.45, s*1.0, 1.4))
    # stubby legs with pads
    for s in (1,-1):
        parts.append(place(sphere(0.42,0.4,0.4, gold), 0.4, s*0.55, 0.32))
        parts.append(place(sphere(0.2,0.14,0.16, pad), 0.78, s*0.55, 0.3))
    # little belly highlight
    parts.append(squash(place(sphere(0.5,0.45,0.5, muzzle), 0.62,0,1.05), 0.85))
    mats = {
        (round(gold[0],3),round(gold[1],3),round(gold[2],3)): (0.4,0.6,None),
        (round(amber[0],3),round(amber[1],3),round(amber[2],3)): (0.4,0.6,None),
        (round(muzzle[0],3),round(muzzle[1],3),round(muzzle[2],3)): (0.55,0.2,None),
        (round(BLACK[0],3),round(BLACK[1],3),round(BLACK[2],3)): (0.3,0.1,None),
    }
    return parts, mats

@builder("mini_clawbot")
def _clawbot():
    import math
    teal  = C(40, 200, 200); dome = C(150, 230, 255); chrome = C(200, 208, 216); glow = C(255, 215, 90)
    parts = []
    # tall boxy arcade-cabinet body (the star of the silhouette)
    parts.append(place(box(1.5, 1.3, 1.95, teal, bevel=0.16, smooth=True), 0, 0, 1.3))
    # big glowing screen/face panel on the front
    parts.append(place(box(0.16, 1.06, 0.92, glow, bevel=0.06), 0.74, 0, 1.55))
    # two cute eyes on the screen + glints
    for s in (1, -1):
        parts.append(place(sphere(0.12, 0.2, 0.24, BLACK), 0.84, s*0.33, 1.68))
        parts.append(place(sphere(0.04, 0.06, 0.07, WHITE), 0.9, s*0.27, 1.78))
    # little smile detail on the screen
    parts.append(place(box(0.1, 0.46, 0.1, BLACK, bevel=0.04), 0.84, 0, 1.28))
    # chrome rim ring + small glass dome on top (smaller than the cabinet now)
    parts.append(place(torus(0.62, 0.09, chrome, axis='Z'), 0, 0, 2.28))
    parts.append(squash(place(sphere(0.58, 0.58, 0.6, dome), 0, 0, 2.34), 0.7))
    parts.append(place(cyl(0.05, 0.3, chrome, axis='Z'), 0, 0, 2.78))
    parts.append(place(sphere(0.15, 0.15, 0.15, glow), 0, 0, 3.0))
    # little chrome legs + teal feet
    for s in (1, -1):
        parts.append(place(cyl(0.2, 0.45, chrome, axis='Z'), -0.05, s*0.52, 0.22))
        parts.append(place(sphere(0.3, 0.3, 0.18, teal), -0.05, s*0.52, 0.06))
    # bold chrome CLAW reaching out in front: shaft + knuckle + 3 fat prongs
    parts.append(place(cyl(0.1, 0.7, chrome, axis='Z'), 1.05, 0, 1.25))
    parts.append(place(sphere(0.26, 0.26, 0.2, chrome), 1.05, 0, 0.86))
    for k in range(3):
        a = math.radians(90 + k*120)
        parts.append(rot(place(cone(0.11, 0.02, 0.55, chrome, axis='Z'),
                               1.05 + math.cos(a)*0.16, math.sin(a)*0.16, 0.62),
                         math.sin(a)*38, 0, -math.cos(a)*38))
    mats = {
        (round(teal[0],3), round(teal[1],3), round(teal[2],3)): (0.5, 0.0, None),
        (round(dome[0],3), round(dome[1],3), round(dome[2],3)): (0.2, 0.0, dome),
        (round(chrome[0],3), round(chrome[1],3), round(chrome[2],3)): (0.3, 0.85, None),
        (round(glow[0],3), round(glow[1],3), round(glow[2],3)): (0.2, 0.0, glow),
        (round(BLACK[0],3), round(BLACK[1],3), round(BLACK[2],3)): (0.25, 0.0, None),
    }
    return parts, mats

@builder("holo_fox")
def _holo_fox():
    body  = C(255,150,40); light = C(255,205,120); glow = C(120,245,255); white = C(245,250,255)
    parts = []
    # slim body, slightly leaning forward
    parts.append(rot(place(sphere(0.62,0.55,0.95, body), 0,0,1.15), 0,18,0))
    # chest / belly lighter front
    parts.append(place(sphere(0.4,0.42,0.6, light), 0.35,0,1.05))
    # glowing chest mark
    parts.append(place(sphere(0.18,0.06,0.28, glow), 0.66,0,1.2))
    # big head
    parts.append(place(sphere(0.78,0.72,0.72, body), 0.2,0,2.45))
    # cheeky lighter face patch
    parts.append(place(sphere(0.46,0.5,0.42, light), 0.55,0,2.32))
    # pointed snout
    parts.append(rot(place(cone(0.3,0.06,0.7, light, axis='X'), 0.95,0,2.3), 0,8,0))
    # nose tip
    parts.append(place(sphere(0.1,0.1,0.09, BLACK), 1.42,0,2.36))
    # big triangular fox ears with glowing tips
    for s in (1,-1):
        parts.append(rot(place(cone(0.28,0.02,0.85, body, axis='Z'), 0.05, s*0.42, 3.2), 0,-8,0))
        parts.append(rot(place(cone(0.12,0.02,0.32, glow, axis='Z'), 0.0, s*0.42, 3.55), 0,-8,0))
    # bright eyes
    for s in (1,-1):
        parts.append(place(sphere(0.13,0.1,0.16, glow), 0.62, s*0.34, 2.6))
        parts.append(place(sphere(0.07,0.06,0.09, BLACK), 0.7, s*0.34, 2.58))
    # legs
    for s in (1,-1):
        parts.append(place(sphere(0.16,0.16,0.34, body), 0.3, s*0.32, 0.32))
        parts.append(place(sphere(0.18,0.18,0.22, body), -0.5, s*0.34, 0.36))
    # big fluffy tail: stacked tapering spheres curving up behind, tip glowing
    parts.append(place(sphere(0.42,0.4,0.42, body), -0.85,0,1.3))
    parts.append(place(sphere(0.36,0.34,0.36, body), -1.25,0,1.7))
    parts.append(place(sphere(0.3,0.28,0.3, light), -1.5,0,2.15))
    parts.append(place(sphere(0.22,0.2,0.22, glow), -1.62,0,2.55))
    mats = {
        (round(body[0],3),round(body[1],3),round(body[2],3)): (0.4,0.0,None),
        (round(light[0],3),round(light[1],3),round(light[2],3)): (0.45,0.0,None),
        (round(glow[0],3),round(glow[1],3),round(glow[2],3)): (0.2,0.0,glow),
        (round(white[0],3),round(white[1],3),round(white[2],3)): (0.5,0.0,None),
        (round(BLACK[0],3),round(BLACK[1],3),round(BLACK[2],3)): (0.25,0.0,None),
    }
    return parts, mats
