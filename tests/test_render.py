import sys, os, shutil, tempfile, math, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bpy
import multiview_product_renderer as mv

results = []
def run(op, **kw):
    try:
        return op(**kw)
    except RuntimeError as e:
        print('REPORTED:', e)
        return {'CANCELLED'}
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))

# Blender 4.2+ registers add-ons from a module; register directly.
mv.register()
# Preferences lookup by __name__ is only used by import; not needed here.

scene = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

root = mv.get_products_root()
def add_product(name, op):
    coll = bpy.data.collections.new(name)
    root.children.link(coll)
    op()
    obj = bpy.context.active_object
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return coll

add_product("Widget", lambda: bpy.ops.mesh.primitive_cube_add(size=1))
add_product("Bracket", lambda: bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=1))
add_product("Knob", lambda: bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5))

scene.render.resolution_x = 32
scene.render.resolution_y = 32
scene.render.image_settings.file_format = 'PNG'

out = tempfile.mkdtemp(prefix="mv_test_")
s = scene.mv_settings
# Camera files are covered by test_annotations; these count image files.
s.export_cameras = False
s.render_output_dir = out + os.sep
s.render_mode = 'CLAY'
s.view_set = 'MIN'

def files():
    found = []
    for d, _, fs in os.walk(out):
        for f in fs:
            if not f.startswith("manifest"): found.append(os.path.relpath(os.path.join(d, f), out).replace("\\", "/"))
    return sorted(found)

try:
    # view_set update copies the preset into the checkboxes
    check("MIN syncs toggles", list(s.views_enabled) == [True, False, True, False, True, False, False, False, False], list(s.views_enabled))

    # 1. Render all, reframe builds cameras even though none exist yet
    check("no cameras before", bpy.data.collections.get(mv.CAMERA_COLL) is None)
    r = run(bpy.ops.mv.render_all)
    f = files()
    check("render all FINISHED", r == {'FINISHED'}, r)
    check("9 images", len(f) == 9, f)
    check("names", "AA_01_Widget/AA_01_Widget_Front_clay.png" in f and "AA_03_Knob/AA_03_Knob_Right_clay.png" in f, f)

    # exclusion and camera restored
    lcs = [mv.find_layer_coll(bpy.context.view_layer.layer_collection, pc.name) for pc in mv.get_products()]
    check("exclusion restored", all(not lc.exclude for lc in lcs))
    check("camera restored (was None)", scene.camera is None, scene.camera)

    # 2. Untick Bracket: labels unchanged
    shutil.rmtree(out); os.makedirs(out)
    root.children["Bracket"].mv_render = False
    r = run(bpy.ops.mv.render_all)
    f = files()
    check("unticked: 6 images", len(f) == 6, f)
    check("unticked: Knob keeps AA_03", any(x.startswith("AA_03_Knob/") for x in f) and not any("Bracket" in x for x in f), f)

    # 3. skip existing: nothing to do
    s.skip_existing = True
    r = run(bpy.ops.mv.render_all)
    check("skip all -> FINISHED, nothing new", r == {'FINISHED'} and len(files()) == 6, (r, files()))

    # 4. delete one, resume renders just it
    victim = os.path.join(out, "AA_03_Knob", "AA_03_Knob_Top_clay.png")
    before = {p: os.path.getmtime(os.path.join(out, p)) for p in files()}
    os.remove(victim)
    r = run(bpy.ops.mv.render_all)
    after = {p: os.path.getmtime(os.path.join(out, p)) for p in files()}
    changed = [p for p in after if p not in before or after[p] != before[p]]
    check("resume rendered only missing", changed == ["AA_03_Knob/AA_03_Knob_Top_clay.png"], changed)

    # zero-byte file counts as missing
    open(victim, "w").close()
    bpy.ops.mv.render_all()
    check("zero-byte re-rendered", os.path.getsize(victim) > 0)
    s.skip_existing = False

    # 5. only_active renders an unticked product with its own label
    s.active_product_index = 1
    shutil.rmtree(out); os.makedirs(out)
    r = bpy.ops.mv.render_all(only_active=True)
    f = files()
    check("active only: Bracket AA_02 x3", len(f) == 3 and all(x.startswith("AA_02_Bracket/") for x in f), f)

    # 6. Custom view selection + disabled custom view
    s.view_set = 'CUSTOM'
    s.views_enabled = [i in (0, 6) for i in range(len(mv.VIEWS_ALL))]
    cv = s.custom_views.add(); cv.name = "Iso"; cv.dir_x, cv.dir_y, cv.dir_z = 1, 1, 1
    cv2 = s.custom_views.add(); cv2.name = "Off"; cv2.enabled = False
    names = [v[0] for v in mv.planned_views(s)]
    check("planned views", names == ["Front", "Persp_FTR", "Iso"], names)
    bpy.ops.mv.build_cameras()
    cams = sorted(o.name for o in bpy.data.collections[mv.CAMERA_COLL].objects)
    check("build cameras custom", cams == ["MV_Cam_Front", "MV_Cam_Iso", "MV_Cam_Persp_FTR"], cams)

    # switching back to a preset ignores toggles; preset is copied in
    s.view_set = 'STD'
    check("STD planned", [v[0] for v in mv.planned_views(s)] == ["Front", "Top", "Right", "Persp_FTR", "Iso"], [v[0] for v in mv.planned_views(s)])
    check("STD syncs toggles", list(s.views_enabled) == [True, False, True, False, True, False, True, False, False])

    # no views at all
    s.view_set = 'CUSTOM'
    s.views_enabled = [False] * len(mv.VIEWS_ALL)
    cv.enabled = False
    r = run(bpy.ops.mv.build_cameras)
    check("no views -> build cancelled", r == {'CANCELLED'}, r)
    r = run(bpy.ops.mv.render_all)
    check("no views -> render cancelled", r == {'CANCELLED'}, r)
    s.view_set = 'MIN'
    cv.enabled = True

    # 7. reframe picks up a rotated product; camera restored by name
    bpy.ops.mv.build_cameras()
    scene.camera = bpy.data.objects["MV_Cam_Front"]
    ortho_before = bpy.data.objects["MV_Cam_Front"].data.ortho_scale
    widget = root.children["Widget"].objects[0]
    widget.scale = (3, 1, 1)
    bpy.context.view_layer.update()
    shutil.rmtree(out); os.makedirs(out)
    root.children["Bracket"].mv_render = True
    r = run(bpy.ops.mv.render_all)
    ortho_after = bpy.data.objects["MV_Cam_Front"].data.ortho_scale
    check("reframe grew framing", ortho_after > ortho_before * 1.5, (ortho_before, ortho_after))
    check("camera restored by name", scene.camera is not None and scene.camera.name == "MV_Cam_Front", scene.camera)

    # reframe off keeps hand-placed cameras
    s.reframe_on_render = False
    cam = bpy.data.objects["MV_Cam_Front"]
    cam.data.ortho_scale = 123.0
    bpy.ops.mv.render_all()
    check("reframe off keeps cameras", bpy.data.objects["MV_Cam_Front"].data.ortho_scale == 123.0)
    s.reframe_on_render = True

    # isolation state restored (exclude one product beforehand)
    lc = mv.find_layer_coll(bpy.context.view_layer.layer_collection, "Knob")
    lc.exclude = True
    bpy.ops.mv.render_all()
    lc = mv.find_layer_coll(bpy.context.view_layer.layer_collection, "Knob")
    check("pre-existing exclusion restored", lc.exclude is True)
    lc.exclude = False

    # nothing ticked
    bpy.ops.mv.set_products_render(state=False)
    r = run(bpy.ops.mv.render_all)
    check("none ticked -> cancelled", r == {'CANCELLED'})
    bpy.ops.mv.set_products_render(state=True)
    check("all ticked again", all(pc.mv_render for pc in mv.get_products()))

    # active_product_index update isolates when isolate_active
    s.isolate_active = True
    s.active_product_index = 2
    ex = {pc.name: mv.find_layer_coll(bpy.context.view_layer.layer_collection, pc.name).exclude for pc in mv.get_products()}
    check("list click isolates", ex == {"Widget": True, "Bracket": True, "Knob": False}, ex)
    s.isolate_active = False

    # unwritable output -> aborts with ERROR, scene restored
    bad = os.path.join(out, "blocker")
    open(bad, "w").close()
    s.render_output_dir = bad + os.sep + "sub" + os.sep
    r = run(bpy.ops.mv.render_all)
    check("bad output dir cancelled", r == {'CANCELLED'}, r)

    # helpers
    check("format_duration", (mv.format_duration(5), mv.format_duration(125), mv.format_duration(3725)) == ("5s", "2m 05s", "1h 02m"))

    mv.unregister()
    check("unregister ok", not hasattr(bpy.types.Collection, "mv_render"))
except Exception:
    traceback.print_exc()
    check("no exception", False, traceback.format_exc())

print("=" * 60)
for name, ok, detail in results:
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   -> {detail}"))
print("TOTAL", sum(ok for _, ok, _ in results), "/", len(results))
shutil.rmtree(out, ignore_errors=True)
