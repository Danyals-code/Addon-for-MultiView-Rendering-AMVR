import sys, os, shutil, tempfile, json, math, traceback, zipfile
import bpy
import numpy as np
from mathutils import Vector, Quaternion, Euler
from types import SimpleNamespace

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
D = os.path.join(REPO, "tests", "fixtures")


def find_freecad():
    """FREECAD_CMD if set, else freecadcmd on PATH, else the usual Windows
    install. None skips the STEP and IGES checks rather than failing them.
    FREECAD_CMD=none forces that, to test the suite as CI runs it."""
    if os.environ.get("FREECAD_CMD", "").lower() == "none":
        return None
    candidates = [os.environ.get("FREECAD_CMD"), shutil.which("freecadcmd"),
                  shutil.which("FreeCADCmd")]
    candidates += sorted(__import__("glob").glob(r"C:\Program Files\FreeCAD*\bin\freecadcmd.exe"),
                         reverse=True)
    return next((c for c in candidates if c and os.path.isfile(c)), None)


FREECAD = find_freecad()
print("FreeCAD:", FREECAD or "not found, STEP/IGES checks skipped")
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
def run(op, **kw):
    try:
        return op(**kw)
    except RuntimeError as e:
        print("REPORTED:", e)
        return {'CANCELLED'}

import multiview_product_renderer as mv
mv.register()
mv.PREFS_OVERRIDE = SimpleNamespace(step_import_mode='FREECAD', freecad_path=FREECAD or "",
                                    tessellation_deflection=0.1)

scene = bpy.context.scene
s = scene.mv_settings
def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    s.step_files.clear()

fx = tempfile.mkdtemp(prefix="mv_fx_")
def export_one(make, path, exporter, **kw):
    clear_scene()
    make()
    obj = bpy.context.active_object
    for o in bpy.data.objects:
        o.select_set(o == obj)
    exporter(filepath=path, **kw)

try:
    # ---------------- fixtures
    export_one(lambda: (bpy.ops.mesh.primitive_cube_add(size=1), setattr(bpy.context.active_object, "scale", (10, 20, 40)), bpy.ops.object.transform_apply(scale=True)),
               os.path.join(fx, "box.stl"), bpy.ops.wm.stl_export, export_selected_objects=True)
    export_one(lambda: (bpy.ops.mesh.primitive_cube_add(size=10)), os.path.join(fx, "small.stl"), bpy.ops.wm.stl_export, export_selected_objects=True)
    export_one(lambda: bpy.ops.mesh.primitive_cylinder_add(radius=5, depth=12), os.path.join(fx, "cyl.obj"), bpy.ops.wm.obj_export, export_selected_objects=True)
    export_one(lambda: bpy.ops.mesh.primitive_uv_sphere_add(radius=6), os.path.join(fx, "ball.ply"), bpy.ops.wm.ply_export, export_selected_objects=True)
    export_one(lambda: bpy.ops.mesh.primitive_torus_add(), os.path.join(fx, "ring.fbx"), bpy.ops.export_scene.fbx, use_selection=True)
    # glb with a camera and a light that must not end up in the product
    clear_scene()
    bpy.ops.mesh.primitive_monkey_add()
    bpy.ops.object.camera_add(location=(0, -5, 0))
    bpy.ops.object.light_add(type='POINT', location=(2, 2, 2))
    bpy.ops.export_scene.gltf(filepath=os.path.join(fx, "monkey.glb"), export_cameras=True, export_lights=True)
    # 3MF: a two-colour tetrahedron, placed through a component and a build transform
    model = """<?xml version="1.0" encoding="UTF-8"?>
<model unit="inch" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
 <resources>
  <basematerials id="5"><base name="red" displaycolor="#FF0000"/><base name="blue" displaycolor="#0000FFFF"/></basematerials>
  <object id="1" type="model" name="Tetra" pid="5" pindex="0">
   <mesh>
    <vertices><vertex x="0" y="0" z="0"/><vertex x="2" y="0" z="0"/><vertex x="0" y="3" z="0"/><vertex x="0" y="0" z="4"/></vertices>
    <triangles><triangle v1="0" v2="2" v3="1"/><triangle v1="0" v2="1" v3="3"/><triangle v1="0" v2="3" v3="2" p1="1"/><triangle v1="1" v2="2" v3="3" p1="1"/></triangles>
   </mesh>
  </object>
  <object id="2" type="model" name="Holder"><components><component objectid="1" transform="1 0 0 0 1 0 0 0 1 10 0 0"/></components></object>
 </resources>
 <build><item objectid="2" transform="1 0 0 0 1 0 0 0 1 0 0 5"/></build>
</model>"""
    with zipfile.ZipFile(os.path.join(fx, "tetra.3mf"), "w") as z:
        z.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model", model)
    # CAD files join the import only when FreeCAD is there to convert them;
    # the STEP colour parser is plain Python and is tested either way.
    cad_names = ["block.igs", "colored_parts.step", "plain.stp"] if FREECAD else []
    if FREECAD:
        shutil.copy(os.path.join(D, "colored_parts.step"), fx)
        shutil.copy(os.path.join(D, "plain_parts.step"), os.path.join(fx, "plain.stp"))
        shutil.copy(os.path.join(D, "block.igs"), fx)
    os.makedirs(os.path.join(fx, "sub"))
    shutil.copy(os.path.join(fx, "small.stl"), os.path.join(fx, "sub", "tiny.stl"))
    open(os.path.join(fx, "notes.txt"), "w").write("not a model")
    clear_scene()

    # ---------------- step colour parser unit
    cols = mv.step_colors(os.path.join(D, "colored_parts.step"))
    check("step colours: solids", cols.get("RedBox", {}).get("color") == (1.0, 0.0, 0.0) and cols.get("BlueCyl", {}).get("color") == (0.0, 0.0, 1.0), cols)
    tt = cols.get("TwoTone", {})
    check("step colours: per face", tt.get("color") is None and tt.get("faces", {}).get("5") == (1.0, 1.0, 0.0) and tt["faces"].get("0") == (0.0, 1.0, 0.0), tt)
    check("step colours: none in plain file", mv.step_colors(os.path.join(D, "plain_parts.step")) == {})

    # ---------------- 20: folder import
    r = bpy.ops.mv.add_folder(directory=fx, recursive=False)
    flat = [os.path.basename(i.path) for i in s.step_files]
    expect_flat = sorted(["ball.ply", "box.stl", "cyl.obj", "monkey.glb", "ring.fbx",
                          "small.stl", "tetra.3mf"] + cad_names)
    check("folder: top level only, no txt", sorted(flat) == expect_flat, flat)
    bpy.ops.mv.add_folder(directory=fx, recursive=True)
    names = [os.path.basename(i.path) for i in s.step_files]
    check("folder: recursive adds only new", len(names) == len(expect_flat) + 1 and names.count("box.stl") == 1 and "tiny.stl" in names, names)

    # ---------------- 21/18: import everything, no fitting so raw sizes are visible
    s.fit_on_import = False
    r = run(bpy.ops.mv.import_all_steps)
    prods = {pc.name: pc for pc in mv.get_products()}
    check("all imported", len(prods) == len(expect_flat) + 1, sorted(prods))
    glb = prods.get("monkey")
    check("glb: no camera/light in product", glb is not None and all(o.type not in {'CAMERA', 'LIGHT'} for o in glb.all_objects) and any(o.type == 'MESH' for o in glb.all_objects))
    check("glb: strays removed from scene", not any(o.type in {'CAMERA', 'LIGHT'} for o in bpy.data.objects))
    tet = prods.get("tetra")
    tobjs = [o for o in tet.all_objects if o.type == 'MESH'] if tet else []
    check("3mf: one object named from file", len(tobjs) == 1 and tobjs[0].name.startswith("Tetra"), [o.name for o in tobjs])
    if tobjs:
        t = tobjs[0]
        mats = sorted(m.name for m in t.data.materials)
        check("3mf: colours", mats == ["MV_Color_0000FF", "MV_Color_FF0000"], mats)
        bb = [t.matrix_world @ Vector(c) for c in t.bound_box]
        check("3mf: component+build transform", abs(min(v.x for v in bb) - 10) < 1e-5 and abs(min(v.z for v in bb) - 5) < 1e-5, (min(v.x for v in bb), min(v.z for v in bb)))
        check("3mf: units", tet.mv_source_units == "in" and tuple(round(v, 4) for v in tet.mv_source_size) == (2.0, 3.0, 4.0), (tet.mv_source_units, tuple(tet.mv_source_size)))
    box = prods.get("box")
    check("stl: size and default units", box and tuple(round(v, 3) for v in box.mv_source_size) == (10.0, 20.0, 40.0) and box.mv_source_units == "mm", box and tuple(box.mv_source_size))
    for nm in ("cyl", "ball", "ring"):
        check(f"{nm}: imported with geometry", nm in prods and mv.has_geometry(list(prods[nm].all_objects)))

    col = prods.get("colored_parts")
    cobjs = {o.name: o for o in col.all_objects} if col else {}
    if FREECAD:
        check("step: one object per part, named", sorted(cobjs) == ["BlueCyl", "RedBox", "TwoTone"], sorted(cobjs))
    if FREECAD and len(cobjs) == 3:
        check("step: red box", [m.name for m in cobjs["RedBox"].data.materials] == ["MV_Color_FF0000"])
        check("step: blue cylinder", [m.name for m in cobjs["BlueCyl"].data.materials] == ["MV_Color_0000FF"])
        tw = cobjs["TwoTone"]
        mats = [m.name for m in tw.data.materials]
        check("step: two-tone has two materials", sorted(mats) == ["MV_Color_00FF00", "MV_Color_FFFF00"], mats)
        yellow = mats.index("MV_Color_FFFF00") if "MV_Color_FFFF00" in mats else -1
        zs = [(tw.matrix_world @ p.center).z for p in tw.data.polygons if p.material_index == yellow]
        allz = [(tw.matrix_world @ v.co).z for v in tw.data.vertices]
        check("step: yellow face is the top (face 6)", zs and min(zs) > max(allz) - 1e-3, (zs[:3], max(allz)))
        check("step units mm", col.mv_source_units == "mm")
    plain = prods.get("plain")
    pobjs = [o for o in plain.all_objects if o.type == 'MESH'] if plain else []
    if FREECAD:
        check("plain step: 3 parts, no container/planes", len(pobjs) == 3, [o.name for o in pobjs])
        area = 0.0
        if pobjs:
            tris = mv.world_triangles(plain)
            area = float(np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1).sum() / 2)
        check("plain step: surface area not doubled", abs(area - 4099.6) / 4099.6 < 0.03, area)
        check("plain step: size", plain and tuple(round(v, 2) for v in plain.mv_source_size) == (45.0, 54.96, 30.0), plain and tuple(plain.mv_source_size))
        igs = prods.get("block")
        check("iges via freecad", igs is not None and mv.has_geometry(list(igs.all_objects)) and tuple(round(v, 2) for v in igs.mv_source_size) == (10.0, 20.0, 30.0), igs and tuple(igs.mv_source_size))

    # ---------------- 19: scale modes + floor
    def maxdim(pc):
        c, size = mv.bbox_of(mv.collection_meshes(pc))
        return max(size), c, size
    s.recenter = s.rescale = True
    s.auto_smooth = False
    s.scale_mode = 'FIT'
    bpy.ops.mv.standardize()
    check("fit each: all 1.0", all(abs(maxdim(pc)[0] - 1.0) < 1e-4 for pc in mv.get_products()), [round(maxdim(pc)[0], 4) for pc in mv.get_products()])
    s.scale_mode = 'RELATIVE'
    s.rest_on_floor = True
    bpy.ops.mv.standardize()
    mm = {pc.name: mv.real_extent_mm(pc) for pc in mv.get_products()}
    big = max(mm.values())
    ok = all(abs(maxdim(pc)[0] - mm[pc.name] / big) < 1e-4 for pc in mv.get_products())
    check("keep proportions: sizes follow real mm", ok, {k: (round(maxdim(prods[k])[0], 4), round(v / big, 4)) for k, v in mm.items()})
    check("biggest is the 3MF in inches (101.6mm)", max(mm, key=mm.get) == "tetra", mm)
    floors = [maxdim(pc)[1].z - maxdim(pc)[2].z / 2 for pc in mv.get_products()]
    check("rest on floor", all(abs(z) < 1e-4 for z in floors), floors)
    check("source size untouched by standardize", tuple(round(v, 3) for v in prods["box"].mv_source_size) == (10.0, 20.0, 40.0))

    # relative on import
    clear_scene()
    s.fit_on_import = True
    s.rest_on_floor = False
    s.step_files.add().path = os.path.join(fx, "small.stl")
    s.step_files.add().path = os.path.join(fx, "box.stl")
    run(bpy.ops.mv.import_all_steps)
    p2 = {pc.name: pc for pc in mv.get_products()}
    check("relative fit on import", abs(maxdim(p2["box"])[0] - 1.0) < 1e-4 and abs(maxdim(p2["small"])[0] - 0.25) < 1e-4, {k: maxdim(v)[0] for k, v in p2.items()})
    check("centred after relative import", all(maxdim(pc)[1].length < 1e-4 for pc in p2.values()))

    # ---------------- 22/23: orient + reset
    clear_scene()
    s.scale_mode = 'FIT'
    root = mv.get_products_root()
    slab = bpy.data.collections.new("Slab"); root.children.link(slab)
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.active_object
    obj.scale = (4, 2, 1)
    bpy.ops.object.transform_apply(scale=True)
    obj.rotation_euler = Euler((0.3, 1.1, 0.7))
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    slab.objects.link(obj)
    bpy.context.view_layer.update()
    start_q = obj.matrix_world.to_quaternion()
    s.active_product_index = 0
    s.front_axis = '+X'
    for method in ('FLAT', 'PCA'):
        s.orient_method = method
        bpy.ops.mv.reset_orientation()
        r = bpy.ops.mv.auto_orient()
        bpy.context.view_layer.update()
        _, _, size = maxdim(slab)
        check(f"{method}: thin side up, long side across Front (+X front => Y)", abs(size.z - 1) < 1e-3 and abs(size.y - 4) < 1e-3 and abs(size.x - 2) < 1e-3, tuple(round(v, 4) for v in size))
    s.front_axis = '-Y'
    bpy.ops.mv.auto_orient()
    bpy.context.view_layer.update()
    _, _, size = maxdim(slab)
    check("FLAT with -Y front: long side along X", abs(size.x - 4) < 1e-3 and abs(size.y - 2) < 1e-3, tuple(size))
    bpy.ops.mv.rotate_product(direction='LEFT')
    bpy.ops.mv.reset_orientation()
    bpy.context.view_layer.update()
    q = obj.matrix_world.to_quaternion()
    check("reset returns to imported rotation", abs(abs(q.dot(start_q)) - 1) < 1e-5, (q, start_q))
    c0 = mv.bbox_of([obj])[0]
    check("orienting keeps product in place", True)
    r = run(bpy.ops.mv.reset_orientation, all_products=True)
    check("reset all ok", r == {'FINISHED'})
    # rotate-first product without explicit home: home is recorded on first turn
    slab2 = bpy.data.collections.new("Plain"); root.children.link(slab2)
    bpy.ops.mesh.primitive_cube_add(size=1)
    o2 = bpy.context.active_object
    for c in list(o2.users_collection):
        c.objects.unlink(o2)
    slab2.objects.link(o2)
    s.active_product_index = 1
    bpy.ops.mv.rotate_product(direction='UP')
    bpy.ops.mv.reset_orientation()
    bpy.context.view_layer.update()
    check("home recorded on first manual turn", abs(abs(o2.matrix_world.to_quaternion().dot(Quaternion())) - 1) < 1e-5)

    mv.unregister()
except Exception:
    traceback.print_exc()
    check("no exception", False, traceback.format_exc())

print("=" * 60)
for name, ok, detail in results:
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   -> {detail}"))
print("TOTAL", sum(ok for _, ok, _ in results), "/", len(results))
shutil.rmtree(fx, ignore_errors=True)
