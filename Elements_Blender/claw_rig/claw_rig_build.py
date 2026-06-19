# claw_rig_build.py — Procedural Blender build of the UFO-catcher claw rig (scrapyard grapple).
# Run inside Blender (5.x). Produces 9 named, centered meshes (S=1 aspect):
#   Base, Cab, Counterweight, Boom, Stick, Elbow, ClawHub, Jaw, Tip
# Blender Z = up -> Roblox Y (up). X = digging reach. Y(depth) -> Roblox Z.
# The Roblox builder (ReplicatedStorage.Shared.ClawModel) sets each MeshPart.Size explicitly,
# so only ASPECT RATIO + orientation matter here, not absolute scale (meshes are ~half scale).
# Upload: select an object (or call RBX_OT_upload.upload directly per object) -> MODEL asset;
# the asset id is written to obj["Roblox Package ID"] (as a STRING). Ids in asset_ids.json.
# To UPDATE an existing asset, set obj["Roblox Package ID"]=str(id) before upload (new version).
# This file reflects the ENRICHED final geometry (cab wedge, treaded base, capped arm, scoop jaw).

import bpy, bmesh, math

def reset():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)

def bbox(name, sx, sy, sz, bevel=0.06, segs=2):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    o = bpy.context.active_object; o.name = name
    o.scale = (sx/2, sy/2, sz/2); bpy.ops.object.transform_apply(scale=True)
    if bevel > 0:
        m = o.modifiers.new("bev", 'BEVEL'); m.width = bevel; m.segments = segs; m.limit_method = 'ANGLE'
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o

def cyl(name, r, h, axis='Z', verts=16):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts)
    o = bpy.context.active_object; o.name = name
    if axis == 'X': o.rotation_euler = (0, math.radians(90), 0)
    elif axis == 'Y': o.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.transform_apply(rotation=True); return o

def subdiv_box(name, sx, sy, sz, cuts=8):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    o = bpy.context.active_object; o.name = name
    o.scale = (sx/2, sy/2, sz/2); bpy.ops.object.transform_apply(scale=True)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    bm.to_mesh(o.data); bm.free(); return o

def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join(); objs[0].name = name; return objs[0]

def center(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS'); o.location = (0, 0, 0)

def build_base():
    # crawler deck + treaded tracks + tread lugs + fenders + front dozer-blade lip
    parts = []
    deck = bbox("deck", 6.5, 6.0, 1.0, bevel=0.10); deck.location = (0, 0, 1.85); parts.append(deck)
    bm = bmesh.new(); bm.from_mesh(deck.data)
    for v in bm.verts:
        if v.co.x > 2.0 and v.co.z > 0: v.co.z -= 0.25
    bm.to_mesh(deck.data); bm.free()
    for s in (-1, 1):
        trk = bbox("trk", 7.5, 1.7, 1.7, bevel=0.30, segs=3); trk.location = (0, s*2.15, 0.85); parts.append(trk)
        for wx in (-1, -0.33, 0.33, 1):
            w = cyl("wh", 0.62, 1.74, axis='Y', verts=14); w.location = (wx*2.6, s*2.15, 0.75); parts.append(w)
        for k in range(10):  # tread lugs around the track
            a = (2*math.pi/10)*k
            lug = bbox("lug", 0.5, 1.8, 0.28, bevel=0.02)
            lug.location = (math.cos(a)*3.4, s*2.15, 0.85 + math.sin(a)*1.0); lug.rotation_euler = (0, -a, 0)
            bpy.ops.object.transform_apply(rotation=True); parts.append(lug)
        fen = bbox("fen", 6.6, 2.1, 0.3, bevel=0.05); fen.location = (0.2, s*2.15, 1.75); parts.append(fen)
    blade = bbox("blade", 0.5, 6.2, 1.4, bevel=0.08); blade.location = (4.0, 0, 0.7); parts.append(blade)
    center(join(parts, "Base"))

def build_cab():
    # clean sloped wedge cabin (single solid). Colored windshield = separate CabGlass part (Roblox builder).
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cab = bpy.context.active_object; cab.name = "Cab"
    cab.scale = (3.9/2, 4.68/2, 4.0/2); bpy.ops.object.transform_apply(scale=True)
    bm = bmesh.new(); bm.from_mesh(cab.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    for v in bm.verts:
        if v.co.x > 0 and v.co.z > 0.0: v.co.z -= 1.15*(v.co.x/1.95)
    for v in bm.verts:
        if v.co.z < -1.6: v.co.x *= 0.9; v.co.y *= 0.92
    bm.to_mesh(cab.data); bm.free()
    b = cab.modifiers.new("b", 'BEVEL'); b.width = 0.08; b.segments = 2; b.limit_method = 'ANGLE'; b.angle_limit = math.radians(30)
    bpy.ops.object.modifier_apply(modifier="b")
    center(cab)
    cw = bbox("Counterweight", 1.5, 4.92, 3.28, bevel=0.16)
    for k in (-1.1, 0, 1.1):
        rib = bbox("rib", 1.6, 4.0, 0.42, bevel=0.04); rib.location = (0, 0, k); cw = join([cw, rib], "Counterweight")
    center(cw)

def _ibeam(name, sx, sec, notch_w, notch_d):
    # I-beam = box with side flange notches. NO end caps: the notch only REMOVES material, so the
    # bbox stays exactly (sx, sec, sec). This is critical -- the Roblox builder sets MeshPart.Size to
    # the segment length, so any geometry protruding past the ends would shrink the beam and the arm
    # would no longer reach the shoulder pivot / grapple (it would float disconnected).
    beam = bbox(name, sx, sec, sec, bevel=0.12)
    for s in (-1, 1):
        notch = bbox("ntch", sx*0.66, notch_w, notch_d, bevel=0); notch.location = (0, s*sec*0.42, 0)
        mod = beam.modifiers.new("bo", 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.object = notch; mod.solver = 'EXACT'
        bpy.context.view_layer.objects.active = beam; bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(notch, do_unlink=True)
    center(beam)

def build_arm():
    _ibeam("Boom", 5.93, 1.35, 0.55, 0.66)
    _ibeam("Stick", 5.95, 1.107, 0.45, 0.54)
    center(cyl("Elbow", 0.95, 1.65, axis='Y', verts=22))

def build_grapple():
    # ClawHub = rounded swivel drum + shallow domed top + lower knuckle dome (mostly capped by the
    # Roblox builder's Rotator drum, but reads cleanly where visible).
    drum = cyl("drum", 1.15, 1.4, axis='Z', verts=32)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.12, segments=24, ring_count=12)
    dome = bpy.context.active_object
    bm = bmesh.new(); bm.from_mesh(dome.data)
    for v in list(bm.verts):
        if v.co.z < 0: v.co.z *= 0.18
    bm.to_mesh(dome.data); bm.free(); dome.location = (0, 0, 0.7)
    kn = cyl("kn", 0.72, 0.7, axis='Z', verts=20); kn.location = (0, 0, -0.85)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.7, segments=18, ring_count=9)
    knd = bpy.context.active_object; knd.location = (0, 0, -1.1); knd.scale = (1, 1, 0.6); bpy.ops.object.transform_apply(scale=True)
    hub = join([drum, dome, kn, knd], "ClawHub")
    b = hub.modifiers.new("b", 'BEVEL'); b.width = 0.04; b.segments = 2; b.limit_method = 'ANGLE'; b.angle_limit = math.radians(35)
    bpy.ops.object.modifier_apply(modifier="b"); center(hub)
    # orange-peel tine v2: smooth inward curl + deep concave inner scoop + dorsal spine + hook + hinge boss
    jaw = subdiv_box("Jaw", 0.95, 1.05, 2.4, cuts=12)
    bm = bmesh.new(); bm.from_mesh(jaw.data)
    for v in bm.verts:
        t = max(0.0, min(1.0, (1.2 - v.co.z)/2.4))
        v.co.x -= 1.1*(t**1.55); v.co.y *= (1.0 - 0.5*(t**1.25))
        if v.co.x < -0.04 and 0.12 < t < 0.97: v.co.x += 0.22*math.sin(t*math.pi)   # concave inner scoop
        if v.co.x > 0.30 and 0.1 < t < 0.9: v.co.x += 0.10*math.sin(t*math.pi)       # dorsal spine ridge
    bm.to_mesh(jaw.data); bm.free()
    bm = bmesh.new(); bm.from_mesh(jaw.data)
    for v in bm.verts:
        t = max(0.0, min(1.0, (1.2 - v.co.z)/2.4))
        if t > 0.6: v.co.x = v.co.x*(1.0 - 0.35*((t-0.6)/0.4)); v.co.y *= (1.0 - 0.2*((t-0.6)/0.4))
    bm.to_mesh(jaw.data); bm.free()
    bpy.ops.mesh.primitive_cylinder_add(radius=0.37, depth=1.1, vertices=18)
    boss = bpy.context.active_object; boss.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.transform_apply(rotation=True); boss.location = (0.08, 0, 1.05)
    join([jaw, boss], "Jaw"); jaw = bpy.data.objects["Jaw"]
    b = jaw.modifiers.new("b", 'BEVEL'); b.width = 0.022; b.segments = 2; b.limit_method = 'ANGLE'
    bpy.ops.object.modifier_apply(modifier="b"); center(jaw)
    bpy.ops.mesh.primitive_cone_add(radius1=0.42, radius2=0.10, depth=0.95, vertices=10)
    tip = bpy.context.active_object; tip.name = "Tip"; center(tip)

if __name__ == "__main__":
    reset(); build_base(); build_cab(); build_arm(); build_grapple()
    print("claw rig built:", sorted(o.name for o in bpy.data.objects if o.type == 'MESH'))
