import sys, os, shutil, tempfile, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bpy, bmesh
import multiview_product_renderer as mv

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
def run(op, **kw):
    try:
        return op(**kw)
    except RuntimeError as e:
        print("REPORTED:", e)
        return {'CANCELLED'}

mv.register()
scene = bpy.context.scene
s = scene.mv_settings
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
    return coll, obj
w, wobj = add_product("Widget", lambda: bpy.ops.mesh.primitive_cube_add(size=1))
k, kobj = add_product("Knob", lambda: bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5))
scene.render.resolution_x, scene.render.resolution_y = 64, 48
out = tempfile.mkdtemp(prefix="mv_pf_")
s.render_output_dir = out + os.sep
s.render_mode = 'CLAY'
s.view_set = 'MIN'
s.manifest_format = 'NONE'

def issues():
    return mv.preflight(bpy.context)
def msgs():
    return [(i["severity"], i["product"], i["message"], i["fix"]) for i in issues()]
def has(text, sev=None):
    return any(text in m and (sev is None or sv == sev) for sv, _, m, _ in msgs())

try:
    check("clean batch: all clear", issues() == [], msgs())

    # empty product: warned, then skipped by the render
    e = bpy.data.collections.new("Hollow"); root.children.link(e)
    check("empty product warned", any(p == "Hollow" and "Empty" in m for _, p, m, _ in msgs()), msgs())
    r = run(bpy.ops.mv.render_all)
    made = sorted(os.listdir(out))
    check("empty product skipped, others render", r == {'FINISHED'} and made == ["AA_01_Widget", "AA_02_Knob"], made)
    bpy.data.collections.remove(e)

    # flipped normals: one face, then the whole mesh
    bm = bmesh.new(); bm.from_mesh(wobj.data)
    bm.faces.ensure_lookup_table(); bm.faces[0].normal_flip(); bm.to_mesh(wobj.data); bm.free()
    check("one flipped face found", any(p == "Widget" and "flipped" in m and f == 'NORMALS' for _, p, m, f in msgs()), msgs())
    bpy.ops.mv.preflight_fix(fix='NORMALS', product="Widget")
    check("fix normals clears it", not has("flipped"), msgs())
    bm = bmesh.new(); bm.from_mesh(wobj.data)
    for f in bm.faces: f.normal_flip()
    bm.to_mesh(wobj.data); bm.free()
    check("inside-out mesh found", any(p == "Widget" and "inside out" in m for _, p, m, _ in msgs()), msgs())
    bpy.ops.mv.preflight_fix(fix='NORMALS', product="Widget")
    check("fix inside-out", not has("inside out"), msgs())
    check("smooth sphere not flagged", not any(p == "Knob" for _, p, _, _ in msgs()))

    # output folder problems
    s.render_output_dir = "//renders/"
    check("relative path on unsaved file", has("Unsaved", 'WARNING'), msgs())
    check("relative path is not called unwritable", not has("cannot be written"), msgs())
    blocker = os.path.join(out, "afile")
    open(blocker, "w").close()
    s.render_output_dir = blocker
    check("output is a file -> error", has("is a file", 'ERROR'), msgs())
    r = run(bpy.ops.mv.render_all)
    check("render refuses on error", r == {'CANCELLED'})
    s.render_output_dir = os.path.join(out, "new", "deeper") + os.sep
    check("missing folder warned with fix", any("does not exist" in m and f == 'FOLDER' for _, _, m, f in msgs()))
    bpy.ops.mv.preflight_fix(fix='FOLDER')
    check("folder fix creates it", os.path.isdir(os.path.join(out, "new", "deeper")))
    s.render_output_dir = out + os.sep

    # video output format
    im = scene.render.image_settings
    if hasattr(im, "media_type"):
        im.media_type = 'VIDEO'
    im.file_format = 'FFMPEG'
    check("video format -> error", has("video", 'ERROR'), msgs())
    if hasattr(im, "media_type"):
        im.media_type = 'IMAGE'
    im.file_format = 'PNG'

    # stale / missing cameras with reframe off
    s.reframe_on_render = False
    for c in list(bpy.data.collections):
        if c.name == mv.CAMERA_COLL:
            mv.clear_collection_objects(c)
    check("no cameras -> error", has("No cameras", 'ERROR'), msgs())
    bpy.ops.mv.build_cameras()
    check("fresh cameras are fine", not has("Cameras"), msgs())
    wobj.scale = (3, 1, 1)
    bpy.context.view_layer.update()
    check("stale cameras warned", any("out of date" in m and f == 'CAMERAS' for _, _, m, f in msgs()), msgs())
    bpy.ops.mv.preflight_fix(fix='CAMERAS')
    check("camera fix clears it", not has("out of date"), msgs())
    scene.render.resolution_x = 100
    check("resolution change makes cameras stale", has("out of date"))
    s.reframe_on_render = True
    check("reframe on: never stale", not has("out of date"))
    scene.render.resolution_x = 64
    wobj.scale = (1, 1, 1)

    # name clash
    s.file_template = "{label}_{product}"
    check("name clash -> error", has("two images one name", 'ERROR'), msgs())
    r = run(bpy.ops.mv.render_all)
    check("render refuses on clash", r == {'CANCELLED'})
    s.file_template = mv.DEFAULT_FILE_TEMPLATE

    # spread out products
    kobj.location = (10, 0, 0)
    bpy.context.view_layer.update()
    check("not centred warned", any("not centred" in m and f == 'RECENTER' for _, _, m, f in msgs()), msgs())
    bpy.ops.mv.preflight_fix(fix='RECENTER')
    check("recenter fix", not has("not centred"), msgs())

    # strays
    bpy.ops.mesh.primitive_cube_add(size=2)
    stray = bpy.context.active_object
    check("stray warned", has("stray"))
    bpy.ops.mv.preflight_fix(fix='STRAYS')
    check("stray fix hides from render", stray.hide_render and not has("stray"))

    # full render: lights, shadow catcher, hdri
    s.render_mode = 'FULL'
    check("full with no lights warned", any("No lights" in m and f == 'LIGHTING' for _, _, m, f in msgs()), msgs())
    bpy.ops.mv.preflight_fix(fix='LIGHTING')
    check("lighting fix", not has("No lights"), msgs())
    scene.render.engine = 'BLENDER_EEVEE'
    s.ground_mode = 'SHADOW'
    check("shadow catcher on eevee warned", has("Shadow Catcher"))
    s.ground_mode = 'NONE'
    s.world_mode = 'HDRI'
    s.hdri_path = "C:/missing.hdr"
    check("missing hdri warned", has("HDRI"))
    s.world_mode = 'COLOR'
    s.render_mode = 'CLAY'

    # warnings never block a scripted render; Check Batch stores results
    kobj.location = (10, 0, 0)
    bpy.context.view_layer.update()
    r = run(bpy.ops.mv.render_all)
    check("warnings don't block execute", r == {'FINISHED'})
    bpy.ops.mv.preflight()
    check("results stored for the panel", len(s.preflight_issues) >= 1 and s.preflight_time)
    s.preflight_on_render = False
    s.file_template = "{label}_{product}"
    r = run(bpy.ops.mv.render_all)
    check("pre-flight can be switched off (setup still catches clash)", r == {'CANCELLED'})
    s.file_template = mv.DEFAULT_FILE_TEMPLATE
    s.preflight_on_render = True

    mv.unregister()
except Exception:
    traceback.print_exc()
    check("no exception", False, traceback.format_exc())

print("=" * 60)
for name, ok, detail in results:
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   -> {detail}"))
print("TOTAL", sum(ok for _, ok, _ in results), "/", len(results))
shutil.rmtree(out, ignore_errors=True)
