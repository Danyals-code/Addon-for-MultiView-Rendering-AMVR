"""View protocols, provenance and Croissant, and seeded randomization."""
import os
import sys
import json
import math
import shutil
import hashlib
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as h  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402
import multiview_product_renderer as mv  # noqa: E402

check = h.check


def rig():
    coll = bpy.data.collections.get(mv.CAMERA_COLL)
    return {o.name: o for o in coll.objects if o.type == 'CAMERA'} if coll else {}


def elevation_azimuth(cam, center):
    d = (cam.matrix_world.translation - center).normalized()
    return math.degrees(math.asin(d.z)), math.degrees(math.atan2(d.x, -d.y)) % 360


def body():
    mv.register()
    scene = bpy.context.scene
    s = scene.mv_settings
    h.fresh_scene()
    out = tempfile.mkdtemp(prefix="mv_prot_")
    try:
        src = os.path.join(out, "widget.stl")
        h.fresh_scene()
        bpy.ops.mesh.primitive_cube_add(size=40)
        bpy.ops.wm.stl_export(filepath=src, export_selected_objects=True)
        h.fresh_scene()
        s.step_files.add().path = src
        bpy.ops.mv.import_all_steps()
        coll = mv.get_products()[0]
        s.front_axis = '-Y'
        center = Vector((0.0, 0.0, 0.0))

        # ---- protocols
        s.view_protocol = 'MVCNN_12'
        bpy.ops.mv.build_cameras()
        cams = rig()
        check("MVCNN: 12 cameras", len(cams) == 12, sorted(cams))
        ea = [elevation_azimuth(c, center) for c in cams.values()]
        check("MVCNN: all at 30 deg elevation", all(abs(e - 30) < 1e-4 for e, _ in ea), ea[:3])
        az = sorted(round(a, 3) % 360 for _, a in ea)
        check("MVCNN: azimuths 30 deg apart", az == [float(30 * i) for i in range(12)], az)
        check("protocol overrides the view set", "MV_Cam_Front" not in cams)

        s.view_protocol = 'ZERO123PP_6'
        bpy.ops.mv.build_cameras()
        cams = rig()
        ea = {n: elevation_azimuth(c, center) for n, c in cams.items()}
        check("Zero123++: elevations alternate 20 / -10",
              [round(ea[f"MV_Cam_Z123PP_{i}"][0], 3) for i in range(6)] == [20, -10, 20, -10, 20, -10],
              ea)
        lens = next(iter(cams.values())).data.lens
        check("Zero123++: 30 deg field of view", abs(math.degrees(2 * math.atan(18 / lens)) - 30) < 1e-4)

        s.view_protocol = 'ZERO123_12'
        s.target_size = 1.0
        s.protocol_seed = 7
        bpy.ops.mv.build_cameras()
        first = {n: c.matrix_world.copy() for n, c in rig().items()}
        dists = [c.matrix_world.translation.length for c in rig().values()]
        check("Zero123: 12 random views at radius 1.5-2.2", len(dists) == 12
              and all(1.5 - 1e-6 <= d <= 2.2 + 1e-6 for d in dists), dists)
        lens = next(iter(rig().values())).data.lens
        check("Zero123: 49.1 deg field of view", abs(math.degrees(2 * math.atan(18 / lens)) - 49.1) < 1e-4)
        bpy.ops.mv.build_cameras()
        same = all(first[n] == c.matrix_world for n, c in rig().items())
        check("same seed, same rig", same)
        s.protocol_seed = 8
        bpy.ops.mv.build_cameras()
        check("other seed, other rig", any(first[n] != c.matrix_world for n, c in rig().items()))
        s.target_size = 2.0
        bpy.ops.mv.build_cameras()
        dists2 = [c.matrix_world.translation.length for c in rig().values()]
        check("radius scales with Target Size", all(3.0 - 1e-6 <= d <= 4.4 + 1e-6 for d in dists2), dists2)
        s.target_size = 1.0

        s.view_protocol = 'TRELLIS_150'
        bpy.ops.mv.build_cameras()
        dists = [c.matrix_world.translation.length for c in rig().values()]
        check("TRELLIS: 150 views at radius 2", len(dists) == 150 and max(abs(d - 2) for d in dists) < 1e-6)
        zs = [c.matrix_world.translation.z for c in rig().values()]
        check("TRELLIS: covers both hemispheres", min(zs) < -1.5 and max(zs) > 1.5, (min(zs), max(zs)))
        s.view_protocol = 'NONE'

        # ---- provenance and Croissant
        scene.render.resolution_x, scene.render.resolution_y = 48, 40
        s.render_output_dir = os.path.join(out, "r") + os.sep
        s.render_mode = 'CLAY'
        s.view_set = 'MIN'
        s.manifest_format = 'JSON'
        s.export_croissant = True
        s.dataset_license = "CC-BY-4.0"
        s.dataset_name = "Test widgets"
        r = h.run(bpy.ops.mv.render_all)
        check("render with croissant", r == {'FINISHED'}, r)
        root = os.path.join(out, "r")
        man = json.load(open(os.path.join(root, "manifest.json")))
        prov = man.get("provenance", {})
        check("provenance: tool and Blender versions",
              prov.get("version") == mv.tool_version() and prov.get("blender") == bpy.app.version_string)
        check("provenance: settings snapshot", prov.get("settings", {}).get("view_set") == "MIN"
              and "random_seed" in prov.get("settings", {}))
        want = hashlib.sha256(open(src, "rb").read()).hexdigest()
        check("manifest rows carry the source hash",
              all(row.get("source_sha256") == want for row in man["images"]), man["images"][0])
        check("croissant forces the CSV manifest", os.path.isfile(os.path.join(root, "manifest.csv")))
        cr = json.load(open(os.path.join(root, "croissant.json")))
        check("croissant: conformsTo 1.0", cr.get("conformsTo") == "http://mlcommons.org/croissant/1.0")
        check("croissant: name and licence", cr.get("name") == "Test widgets" and cr.get("license") == "CC-BY-4.0")
        fields = [f["name"] for f in cr["recordSet"][0]["field"]]
        check("croissant: one field per manifest column", fields == list(mv.MANIFEST_FIELDS), fields)
        csv_sha = hashlib.sha256(open(os.path.join(root, "manifest.csv"), "rb").read()).hexdigest()
        check("croissant: manifest checksum", cr["distribution"][0]["sha256"] == csv_sha)
        check("croissant: png file set", any(d.get("encodingFormat") == "image/png"
                                             for d in cr["distribution"]))
        try:
            import mlcroissant  # noqa: F401
            ds = mlcroissant.Dataset(jsonld=os.path.join(root, "croissant.json"))
            rows = list(ds.records(record_set="outputs"))
            check("croissant validates with mlcroissant", len(rows) == len(man["images"]), len(rows))
        except ImportError:
            print("mlcroissant not installed: skipping its validation")
        s.export_croissant = False

        # ---- randomization
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 4
        scene.cycles.device = 'CPU'
        scene.cycles.use_denoising = False
        scene.render.film_transparent = True
        s.transparent_bg = True
        s.render_mode = 'FULL'
        s.view_set = 'STD'
        s.pass_mask = True
        s.export_cameras = True
        s.manifest_format = 'NONE'
        bpy.ops.mv.apply_scene_setup()
        energies = {o.name: o.data.energy for o in bpy.data.collections[mv.LIGHT_COLL].objects
                    if o.type == 'LIGHT'}
        world = scene.world
        s.random_enabled = True
        s.random_seed = 3
        s.random_hdri = True
        s.random_material = True
        s.random_distractors = 4
        s.random_camera_angle = math.radians(12)

        def render_to(name):
            s.render_output_dir = os.path.join(out, name) + os.sep
            r = h.run(bpy.ops.mv.render_all)
            folder = os.path.join(out, name, "AA_01_widget")
            img = mv.load_pixels(os.path.join(folder, "AA_01_widget_Persp_FTR.png"))
            mask = mv.load_pixels(os.path.join(folder, "AA_01_widget_Persp_FTR_mask.png"))
            cams = json.load(open(os.path.join(folder, "AA_01_widget_cameras.json")))
            return r, img, mask, cams

        r, img_a, mask_a, cams_a = render_to("ra")
        check("randomized render finished", r == {'FINISHED'}, r)
        _, img_b, _, cams_b = render_to("rb")
        check("same seed: identical image", np.abs(img_a - img_b).max() < 1e-6,
              float(np.abs(img_a - img_b).max()))
        s.random_seed = 4
        _, img_c, _, cams_c = render_to("rc")
        check("other seed: different image", np.abs(img_a - img_c).max() > 0.05)

        bpy.ops.mv.build_cameras()
        canon = rig()["MV_Cam_Persp_FTR"].matrix_world
        rec = next(v for v in cams_a["views"] if v["view"] == "Persp_FTR")
        moved = Matrix(rec["c2w_opengl"])
        angle = math.degrees((moved.translation.normalized()).angle(canon.translation.normalized()))
        check("cameras.json records the jittered pose, within 12 deg", 1e-3 < angle <= 12.0 + 1e-6, angle)
        check("cameras.json flags randomized", cams_a.get("randomized") is True)
        # The product centre, projected with the recorded pose, lands on the mask.
        p = Matrix(rec["w2c_opencv"]) @ Vector((0, 0, 0, 1))
        k = rec["K"]
        u, v = k[0][0] * p.x / p.z + k[0][2], k[1][1] * p.y / p.z + k[1][2]
        m = mask_a[::-1, :, 0] > 0.5
        ys, xs = np.nonzero(m)
        check("mask and recorded pose agree", abs(xs.mean() - u) < 2.5 and abs(ys.mean() - v) < 2.5,
              (xs.mean(), u, ys.mean(), v))
        # Distractors: present in the Full render, absent from the mask, never
        # over the product.
        alpha = img_a[::-1, :, 3] > 0.5
        check("distractors appear in the Full render", (alpha & ~m).sum() > 20, int((alpha & ~m).sum()))
        check("distractors never cover the product", (m & ~alpha).sum() == 0)

        check("distractors removed afterwards", bpy.data.collections.get(mv.DISTRACTOR_COLL) is None
              and not any(o.name.startswith("MV_Distractor") for o in bpy.data.objects))
        check("world restored", scene.world == world)
        check("light energies restored", all(abs(bpy.data.objects[n].data.energy - e) < 1e-9
                                             for n, e in energies.items()))
        check("product materials removed", not any(md.name.startswith(mv.MATERIAL_MOD)
                                                   for o in bpy.data.objects for md in o.modifiers))
        mv.unregister()
    finally:
        shutil.rmtree(out, ignore_errors=True)


h.guard(body)
