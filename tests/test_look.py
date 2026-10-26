import sys, os, shutil, tempfile, json, math, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bpy
import numpy as np
from mathutils import Vector
import multiview_product_renderer as mv

KEEP = os.path.join(tempfile.mkdtemp(prefix="mv_keep_"), "keep_")
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
def run(op, **kw):
    try:
        return op(**kw)
    except RuntimeError as e:
        print("REPORTED:", e)
        return {'CANCELLED'}

# Never touch the real user presets folder.
preset_dir = tempfile.mkdtemp(prefix="mv_presets_")
mv.user_preset_dir = lambda create=False: preset_dir

mv.register()
scene = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
root = mv.get_products_root()
def add_product(name, op, smooth=False):
    coll = bpy.data.collections.new(name)
    root.children.link(coll)
    op()
    obj = bpy.context.active_object
    if smooth:
        bpy.ops.object.shade_smooth()
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return coll
add_product("Widget", lambda: bpy.ops.mesh.primitive_cube_add(size=1))
add_product("Ball", lambda: bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, segments=64, ring_count=32), smooth=True)
add_product("Ring", lambda: bpy.ops.mesh.primitive_torus_add(major_radius=0.4, minor_radius=0.15), smooth=True)

scene.render.resolution_x = 120
scene.render.resolution_y = 90
scene.render.engine = 'CYCLES'
scene.cycles.samples = 4
scene.cycles.device = 'CPU'
scene.cycles.use_denoising = False
s = scene.mv_settings
s.render_mode = 'FULL'
s.view_set = 'CUSTOM'
s.views_enabled = [i in (0, 1, 2, 3, 6) for i in range(len(mv.VIEWS_ALL))]   # Front Back Top Bottom Persp_FTR
s.bg_color = (0.2, 0.3, 0.4, 1.0)
out = tempfile.mkdtemp(prefix="mv_look_")
s.render_output_dir = out + os.sep
s.manifest_format = 'NONE'

def px(rel):
    return mv.load_pixels(os.path.join(out, rel))
def reset():
    shutil.rmtree(out); os.makedirs(out)

try:
    # ---------------- scene setup builds rig, world, ground
    s.ground_mode = 'NONE'
    r = run(bpy.ops.mv.apply_scene_setup)
    rig = bpy.data.objects.get(mv.LIGHT_RIG)
    lights = [o for o in bpy.data.collections[mv.LIGHT_COLL].objects if o.type == 'LIGHT']
    check("rig built", rig is not None and len(lights) == 3 and all(l.parent == rig for l in lights))

    # ---------------- 12: orient rig
    bpy.ops.mv.build_cameras()
    key = bpy.data.objects["MV_Light_Key"]
    bpy.context.view_layer.update()
    k0 = key.matrix_world.translation.copy()
    mv.orient_light_rig(bpy.context, bpy.data.objects["MV_Cam_Front"])
    bpy.context.view_layer.update()
    k_front = key.matrix_world.translation.copy()
    check("front orientation is identity", (k_front - k0).length < 1e-4, (k0, k_front))
    mv.orient_light_rig(bpy.context, bpy.data.objects["MV_Cam_Back"])
    bpy.context.view_layer.update()
    k_back = key.matrix_world.translation.copy()
    c = rig.matrix_world.translation
    check("back = rig turned 180 about Z", abs((k_back - c).x + (k0 - c).x) < 1e-4 and abs((k_back - c).y + (k0 - c).y) < 1e-4 and abs(k_back.z - k0.z) < 1e-4, (k0, k_back))
    mv.reset_light_rig()

    # follow vs fixed: Back view brightness
    reset()
    s.lights_follow_camera = False
    json.dump({'lights': [{'name': 'Key', 'pos': [0.0, -2.0, 0.6], 'size': 2.0, 'energy': 300, 'color': [1, 1, 1]}]}, open(os.path.join(preset_dir, 'OneKey.json'), 'w')); s.lighting_preset = 'USER:OneKey'; bpy.ops.mv.build_lighting(); rig = bpy.data.objects[mv.LIGHT_RIG]; key = bpy.data.objects['MV_Light_Key']; lights = [o for o in bpy.data.collections[mv.LIGHT_COLL].objects if o.type == 'LIGHT']; bpy.context.view_layer.update(); k0 = key.matrix_world.translation.copy()
    run(bpy.ops.mv.render_all)
    fixed = px("AA_01_Widget/AA_01_Widget_Back.png")
    reset()
    s.lights_follow_camera = True
    run(bpy.ops.mv.render_all)
    follow = px("AA_01_Widget/AA_01_Widget_Back.png")
    front = px("AA_01_Widget/AA_01_Widget_Front.png")
    def product_mean(img):
        bg = img[0, 0, :3]
        m = np.abs(img[..., :3] - bg).max(-1) > 0.05
        return img[..., :3][m].mean()
    d_follow = abs(product_mean(follow) - product_mean(front)); d_fixed = abs(product_mean(fixed) - product_mean(front))
    check("following: Back matches Front on a symmetric cube", d_follow < 0.02 and d_fixed > 3 * d_follow, (d_follow, d_fixed))
    mv.save_pixels(np.concatenate([front, fixed, follow], axis=1), KEEP + "follow.png", "PNG")
    bpy.context.view_layer.update()
    check("rig reset after render", abs(rig.matrix_world.to_3x3().to_euler().z) < 1e-6 and (key.matrix_world.translation - k0).length < 1e-4)

    os.remove(os.path.join(preset_dir, 'OneKey.json')); s.lighting_preset = 'STUDIO_SOFT'; bpy.ops.mv.build_lighting(); rig = bpy.data.objects[mv.LIGHT_RIG]; key = bpy.data.objects['MV_Light_Key']; lights = [o for o in bpy.data.collections[mv.LIGHT_COLL].objects if o.type == 'LIGHT']
    # ---------------- 17: save / load preset roundtrip
    key.location.x += 0.3
    key.data.energy = 1234.0
    bpy.context.view_layer.update()
    want = {o.name: o.matrix_world.copy() for o in lights}
    r = bpy.ops.mv.save_lighting_preset(name="My Rig")
    files = os.listdir(preset_dir)
    check("preset file written", files == ["My Rig.json"], files)
    items = [i[0] for i in mv.lighting_preset_items(s, bpy.context)]
    check("preset in enum", "USER:My Rig" in items and items[:5] == ["STUDIO_SOFT", "STUDIO_HARD", "DRAMATIC", "HIGH_KEY", "NONE"], items)
    check("preset selected", s.lighting_preset == "USER:My Rig", s.lighting_preset)
    bpy.ops.mv.build_lighting()
    bpy.context.view_layer.update()
    got = {o.name: o.matrix_world.copy() for o in bpy.data.collections[mv.LIGHT_COLL].objects if o.type == 'LIGHT'}
    same = all(name in got and max(abs(a - b) for ra, rb in zip(got[name], m) for a, b in zip(ra, rb)) < 1e-3 for name, m in want.items())
    check("preset roundtrip matrices", same)
    check("preset roundtrip energy", abs(bpy.data.objects["MV_Light_Key"].data.energy - 1234.0) < 0.1, bpy.data.objects["MV_Light_Key"].data.energy)
    # front axis change rotates the saved rig with it
    s.front_axis = '-Y'
    bpy.ops.mv.build_lighting()
    bpy.context.view_layer.update()
    kk = bpy.data.objects["MV_Light_Key"].matrix_world.translation
    check("preset follows front axis", (kk - want["MV_Light_Key"].translation).length > 0.1)
    s.front_axis = '+X'
    r = bpy.ops.mv.delete_lighting_preset('EXEC_DEFAULT')
    check("preset deleted", os.listdir(preset_dir) == [] and s.lighting_preset == "STUDIO_SOFT")
    s.lighting_preset = 'NONE'
    bpy.ops.mv.build_lighting()
    check("NONE preset empty rig", not [o for o in bpy.data.collections[mv.LIGHT_COLL].objects if o.type == 'LIGHT'])
    s.lighting_preset = 'STUDIO_SOFT'
    bpy.ops.mv.build_lighting()

    # ---------------- 13: ground
    s.ground_mode = 'SHADOW'
    reset()
    run(bpy.ops.mv.render_all)
    ground = bpy.data.objects.get(mv.GROUND_NAME)
    check("ground built", ground is not None and ground.is_shadow_catcher)
    check("ground not a stray", ground not in mv.stray_render_objects(bpy.context))
    check("ground restored visible", ground.hide_render is False)
    shadow = px("AA_01_Widget/AA_01_Widget_Persp_FTR.png")
    bottom = px("AA_01_Widget/AA_01_Widget_Bottom.png")
    bg = bottom[0, 0, :3]
    check("bottom view still shows product", (np.abs(bottom[..., :3] - bg).max(-1) > 0.05).sum() > 100)
    shadow_persp = shadow
    s.ground_mode = 'NONE'
    reset()
    run(bpy.ops.mv.render_all)
    noground = px("AA_01_Widget/AA_01_Widget_Persp_FTR.png")
    check("ground removed when None", bpy.data.objects.get(mv.GROUND_NAME) is None)
    diff = np.abs(shadow_persp[..., :3] - noground[..., :3]).max(-1)
    check("shadow catcher changes image", (diff > 0.05).sum() > 50, int((diff > 0.05).sum()))
    darker = (shadow_persp[..., :3].mean(-1) < noground[..., :3].mean(-1) - 0.05).sum()
    check("shadow is darker", darker > 50, int(darker))
    shutil.copy(os.path.join(out, "AA_01_Widget/AA_01_Widget_Persp_FTR.png"), KEEP + "noground.png")
    mv.save_pixels(shadow_persp, KEEP + "shadow.png", 'PNG')

    s.ground_mode = 'FLOOR'
    s.ground_color = (0.9, 0.1, 0.1)
    s.render_mode = 'BOTH'
    reset()
    run(bpy.ops.mv.render_all)
    top = px("AA_01_Widget/AA_01_Widget_Top_render.png")
    check("floor fills Top background", top[2, 2, 0] > top[2, 2, 2] + 0.2, top[2, 2])
    clay_top = px("AA_01_Widget/AA_01_Widget_Top_clay.png")
    check("clay ignores floor", abs(clay_top[2, 2, 0] - clay_top[2, 2, 2]) < 0.05, clay_top[2, 2])
    s.ground_mode = 'NONE'
    s.render_mode = 'FULL'

    # ---------------- 14: HDRI
    hdri_dir = bpy.utils.system_resource('DATAFILES', path=os.path.join("studiolights", "world"))
    hdri = os.path.join(hdri_dir, sorted(f for f in os.listdir(hdri_dir) if f.endswith(".exr"))[0])
    s.world_mode = 'HDRI'
    s.hdri_path = "C:/nope/missing.hdr"
    r = run(bpy.ops.mv.apply_world)
    check("missing hdri reported", r == {'CANCELLED'})
    s.hdri_path = hdri
    s.hdri_visible = False
    s.lighting_preset = 'NONE'
    bpy.ops.mv.apply_scene_setup()
    nodes = scene.world.node_tree.nodes
    check("hdri nodes", any(n.bl_idname == "ShaderNodeTexEnvironment" for n in nodes) and any(n.bl_idname == "ShaderNodeLightPath" for n in nodes))
    reset()
    run(bpy.ops.mv.render_all)
    hid = px("AA_01_Widget/AA_01_Widget_Persp_FTR.png")
    s.hdri_visible = True
    bpy.ops.mv.apply_world()
    reset()
    run(bpy.ops.mv.render_all)
    vis = px("AA_01_Widget/AA_01_Widget_Persp_FTR.png")
    check("hidden hdri: corner is flat bg", np.abs(hid[2, 2, :3] - hid[2, -3, :3]).max() < 0.02 and np.abs(hid[2, 2, :3] - hid[-3, 2, :3]).max() < 0.02)
    check("visible hdri: background varies", np.abs(vis[..., :3] - hid[..., :3]).max() > 0.1)
    check("hdri lights product (no lamps)", product_mean(hid) > 0.05, product_mean(hid))
    s.world_mode = 'COLOR'
    s.lighting_preset = 'STUDIO_SOFT'
    bpy.ops.mv.apply_scene_setup()

    # ---------------- 15: passes
    s.render_mode = 'CLAY'
    s.pass_lines = s.pass_mask = s.pass_ao = True
    s.ao_samples = 8
    reset()
    r = run(bpy.ops.mv.render_all)
    f = sorted(os.listdir(os.path.join(out, "AA_01_Widget")))
    check("pass files", {"AA_01_Widget_Front_lines.png", "AA_01_Widget_Front_mask.png", "AA_01_Widget_Front_ao.png", "AA_01_Widget_Front_clay.png"} <= set(f), f)
    lines = px("AA_01_Widget/AA_01_Widget_Persp_FTR_lines.png")
    dark = lines[..., :3].mean(-1) < 0.5
    check("lines: white page with dark lines", (lines[..., :3].mean(-1) > 0.9).mean() > 0.8 and dark.sum() > 50, (float((lines[..., :3].mean(-1) > 0.9).mean()), int(dark.sum())))
    mask = px("AA_01_Widget/AA_01_Widget_Persp_FTR_mask.png")
    inner = mask[..., 0] > 0.5
    ys, xs = np.nonzero(inner)
    cy, cx = int(ys.mean()), int(xs.mean())
    check("cube creases drawn inside silhouette", dark[cy - 12:cy + 12, cx - 12:cx + 12].any())
    ball_lines = px("AA_02_Ball/AA_02_Ball_Persp_FTR_lines.png")
    ball_mask = px("AA_02_Ball/AA_02_Ball_Persp_FTR_mask.png")[..., 0] > 0.5
    bdark = ball_lines[..., :3].mean(-1) < 0.5
    yy, xx = np.nonzero(ball_mask)
    by, bx = int(yy.mean()), int(xx.mean())
    rad = int(np.sqrt(ball_mask.sum() / math.pi))
    core = bdark[by - rad // 2:by + rad // 2, bx - rad // 2:bx + rad // 2]
    check("smooth sphere: no interior lines", core.sum() == 0, int(core.sum()))
    check("smooth sphere: outline drawn", bdark.sum() > 2 * math.pi * rad, (int(bdark.sum()), rad))
    check("mask binary-ish", ((mask[..., 0] < 0.02) | (mask[..., 0] > 0.98)).mean() > 0.95 and mask[2, 2, 0] < 0.02)
    ao = px("AA_01_Widget/AA_01_Widget_Persp_FTR_ao.png")
    check("ao background white", ao[2, 2, :3].min() > 0.95, ao[2, 2])
    ring_ao = px("AA_03_Ring/AA_03_Ring_Persp_FTR_ao.png"); ring_in = px("AA_03_Ring/AA_03_Ring_Persp_FTR_mask.png")[..., 0] > 0.5
    check("ao darkens the torus", ring_ao[..., :3][ring_in].min() < 0.88, float(ring_ao[..., :3][ring_in].min()))
    check("ao convex cube stays white", ao[..., :3][inner].min() > 0.9)
    shutil.copy(os.path.join(out, "AA_03_Ring/AA_03_Ring_Persp_FTR_ao.png"), KEEP + "ring_ao.png")
    shutil.copy(os.path.join(out, "AA_03_Ring/AA_03_Ring_Persp_FTR_lines.png"), KEEP + "ring_lines.png")
    check("engine restored after ao", scene.render.engine == 'CYCLES' and bpy.context.view_layer.material_override is None)
    check("workbench settings restored", scene.display.shading.light != 'MATCAP' and not scene.display.shading.show_object_outline)
    for nm in ("lines", "mask", "ao"):
        shutil.copy(os.path.join(out, f"AA_01_Widget/AA_01_Widget_Persp_FTR_{nm}.png"), KEEP + nm + ".png")
    shutil.copy(os.path.join(out, "AA_02_Ball/AA_02_Ball_Persp_FTR_lines.png"), KEEP + "ball_lines.png")
    s.lines_fill = 'CLAY'
    s.pass_mask = s.pass_ao = False
    reset()
    run(bpy.ops.mv.render_all)
    cl = px("AA_01_Widget/AA_01_Widget_Persp_FTR_lines.png")
    clay = px("AA_01_Widget/AA_01_Widget_Persp_FTR_clay.png")
    check("lines over clay", np.abs(cl[..., :3] - clay[..., :3])[~dark].mean() < 0.05 and dark.sum() > 0)
    shutil.copy(os.path.join(out, "AA_01_Widget/AA_01_Widget_Persp_FTR_lines.png"), KEEP + "lines_clay.png")
    s.pass_lines = False

    # ---------------- 16: materials
    s.render_mode = 'FULL'
    widget = root.children["Widget"].objects[0]
    slots_before = [sl.material for sl in widget.material_slots]
    reset()
    run(bpy.ops.mv.render_all)
    keep_img = px("AA_01_Widget/AA_01_Widget_Persp_FTR.png")
    s.material_preset = 'BRUSHED_METAL'
    s.material_color = (0.2, 0.6, 0.9)
    root.children["Ball"].mv_material = 'GLASS'
    root.children["Ball"].mv_material_color = (1, 0, 0)
    reset()
    run(bpy.ops.mv.render_all)
    metal = px("AA_01_Widget/AA_01_Widget_Persp_FTR.png")
    check("material changes render", np.abs(metal - keep_img).max() > 0.1)
    check("modifiers removed", not any(m.name.startswith(mv.MATERIAL_MOD) for o in bpy.data.objects for m in o.modifiers))
    check("slots untouched", [sl.material for sl in widget.material_slots] == slots_before)
    mw = bpy.data.materials.get("MV_Material_Widget")
    check("widget metal", mw is not None and mw.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value == 1.0)
    mb = bpy.data.materials.get("MV_Material_Ball")
    check("ball glass red", mb is not None and mb.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value == 1.0 and tuple(mb.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value)[:3] == (1.0, 0.0, 0.0))
    root.children["Ball"].mv_material = 'KEEP'
    check("keep override", mv.product_material_choice(s, root.children["Ball"]) is None)
    mv.save_pixels(metal, KEEP + "metal.png", 'PNG')

    mv.unregister()
except Exception:
    traceback.print_exc()
    check("no exception", False, traceback.format_exc())

print("=" * 60)
for name, ok, detail in results:
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   -> {detail}"))
print("TOTAL", sum(ok for _, ok, _ in results), "/", len(results))
shutil.rmtree(out, ignore_errors=True)
shutil.rmtree(preset_dir, ignore_errors=True)
