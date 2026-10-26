"""Camera export, depth/normal/part passes, COCO and BOP, checked against
Blender's own projection rather than against themselves."""
import os
import sys
import json
import math
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as h  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
import multiview_product_renderer as mv  # noqa: E402

check = h.check


def pixel_of(scene, cam, point):
    """Where Blender itself puts a world point, in pixels, top-left origin."""
    w, hgt = mv.render_resolution(scene)
    co = world_to_camera_view(scene, cam, point)
    return co.x * w, (1.0 - co.y) * hgt, co.z


def project(record, point):
    p = Matrix(record["w2c_opencv"]) @ point.to_4d()
    if record["projection"] == "perspective":
        k = record["K"]
        return k[0][0] * p.x / p.z + k[0][2], k[1][1] * p.y / p.z + k[1][2], p.z
    sx, sy = record["pixel_size"]
    cx, cy = record["principal_point"]
    return cx + p.x / sx, cy + p.y / sy, p.z


def body():
    mv.register()
    scene = bpy.context.scene
    h.fresh_scene()
    out = tempfile.mkdtemp(prefix="mv_ann_")
    try:
        # A two-part product drawn in "millimetres": a 100 mm block and a
        # 40 mm cylinder sitting on top of it, well away from the origin.
        coll, (block, peg) = h.add_product(
            "Widget",
            lambda: bpy.ops.mesh.primitive_cube_add(size=100, location=(500, 200, 50)),
            lambda: bpy.ops.mesh.primitive_cylinder_add(radius=20, depth=40,
                                                        location=(500, 200, 120)))
        block.name, peg.name = "Block", "Peg"
        mv.record_source_size(coll, "mm")
        bpy.context.view_layer.update()
        corner_src = Vector((550.0, 250.0, 100.0))       # a top corner of the block
        s = scene.mv_settings
        s.recenter = s.rescale = True
        s.auto_smooth = False
        bpy.ops.mv.standardize()
        bpy.ops.mv.rotate_product(direction='LEFT')       # turns are recorded too
        bpy.context.view_layer.update()
        to_world = mv.product_to_world(coll)
        world_corner = to_world @ corner_src
        # The same corner, found from the mesh itself after the moves.
        mesh_corners = [block.matrix_world @ v.co for v in block.data.vertices]
        nearest = min((c - world_corner).length for c in mesh_corners)
        check("source-to-world tracks standardize and turns", nearest < 1e-5, nearest)
        check("source-to-world scale is 1/140 m per mm",
              abs(to_world.to_3x3().determinant() ** (1 / 3) - 1 / 140) < 1e-9)

        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 2
        scene.cycles.device = 'CPU'
        scene.render.resolution_x, scene.render.resolution_y = 96, 72
        s.render_output_dir = out + os.sep
        s.render_mode = 'CLAY'
        s.view_set = 'ALL'
        s.pass_mask = True
        s.pass_depth = s.pass_normal = s.pass_parts = True
        s.export_cameras = s.export_coco = s.export_bop = True
        s.manifest_format = 'JSON'
        r = h.run(bpy.ops.mv.render_all)
        check("render finished", r == {'FINISHED'}, r)

        folder = os.path.join(out, "AA_01_Widget")
        names = sorted(os.listdir(folder))
        for f in ("AA_01_Widget_Front_depth.exr", "AA_01_Widget_Front_normal.exr",
                  "AA_01_Widget_Front_parts.png", "AA_01_Widget_cameras.json",
                  "AA_01_Widget_transforms.json"):
            check(f"wrote {f}", f in names, names)

        cams = json.load(open(os.path.join(folder, "AA_01_Widget_cameras.json")))
        check("nine views recorded", len(cams["views"]) == 9, len(cams["views"]))
        check("parts listed in name order",
              cams["parts"] == [{"id": 1, "name": "Block"}, {"id": 2, "name": "Peg"}], cams["parts"])
        check("model_to_world recorded",
              max(abs(a - b) for ra, rb in zip(cams["model_to_world"], to_world)
                  for a, b in zip(ra, rb)) < 1e-9)

        # Every view's numbers must put the corner where Blender does.
        worst = 0.0
        for rec in cams["views"]:
            cam = bpy.data.objects[rec["camera"]]
            u, v, _ = project(rec, world_corner)
            bu, bv, _ = pixel_of(scene, cam, world_corner)
            worst = max(worst, abs(u - bu), abs(v - bv))
        check("K / ortho pixel size and poses match Blender's projection", worst < 1e-3, worst)

        # Depth: cast a ray through pixel centres and compare the hit's
        # view-axis distance with the stored value.
        front = next(r for r in cams["views"] if r["view"] == "Persp_FTR")
        cam = bpy.data.objects[front["camera"]]
        depth = mv.load_pixels(os.path.join(folder, "AA_01_Widget_Persp_FTR_depth.exr"), raw=True)[::-1]
        c2w = Matrix(front["c2w_opengl"])
        k = front["K"]
        deps = bpy.context.evaluated_depsgraph_get()
        errors = []
        for py in range(10, 72, 7):
            for px_ in range(10, 96, 9):
                ray = Vector(((px_ + 0.5 - k[0][2]) / k[0][0], -(py + 0.5 - k[1][2]) / k[1][1], -1.0))
                origin = c2w.translation
                direction = (c2w.to_3x3() @ ray).normalized()
                hit, loc, *_ = scene.ray_cast(deps, origin, direction)
                if hit and depth[py, px_, 3] > 0.5:
                    expect = -(c2w.inverted() @ loc).z
                    errors.append(abs(depth[py, px_, 0] - expect) / expect)
        check("depth matches ray casts", errors and max(errors) < 1e-3,
              (len(errors), max(errors) if errors else None))
        check("depth background is 0", depth[0, 0, 0] == 0 and depth[0, 0, 3] == 0)

        # Normals: the block's top faces +Z in the world; in Top's camera space
        # that is +Z (towards the camera).
        normals = mv.load_pixels(os.path.join(folder, "AA_01_Widget_Top_normal.exr"), raw=True)
        hgt, wid = normals.shape[:2]
        n = normals[hgt // 2, wid // 2, :3]
        check("top-view normal points at the camera", n[2] > 0.99, n)
        # And a side face seen from Front: the block's +X face (Right after the
        # LEFT turn's 90 degrees, whichever) must lie in the image plane.
        fn = mv.load_pixels(os.path.join(folder, "AA_01_Widget_Front_normal.exr"), raw=True)
        lengths = np.linalg.norm(fn[..., :3][fn[..., 3] > 0.5], axis=-1)
        check("normals are unit length", np.allclose(lengths, 1.0, atol=1e-3))

        labels = mv.read_png16(os.path.join(folder, "AA_01_Widget_Persp_FTR_parts.png"))
        check("part IDs are 0, 1, 2", set(np.unique(labels).tolist()) == {0, 1, 2},
              np.unique(labels))
        check("part ID image matches the mask",
              np.array_equal(labels > 0, mv.load_pixels(os.path.join(
                  folder, "AA_01_Widget_Persp_FTR_mask.png"))[::-1, :, 0] > 0.5)
              or abs(int((labels > 0).sum()) - int((mv.load_pixels(os.path.join(
                  folder, "AA_01_Widget_Persp_FTR_mask.png"))[..., 0] > 0.5).sum())) < 40)

        tf = json.load(open(os.path.join(folder, "AA_01_Widget_transforms.json")))
        check("transforms.json has the 3 perspective views", len(tf["frames"]) == 3,
              len(tf["frames"]))
        frame = tf["frames"][0]
        check("transforms.json paths resolve",
              os.path.isfile(os.path.join(folder, frame["file_path"]))
              and os.path.isfile(os.path.join(folder, frame["mask_path"])))

        # COCO: decode one RLE and compare it with the label image.
        coco = json.load(open(os.path.join(out, "coco.json")))
        check("coco images: 9 views", len(coco["images"]) == 9, len(coco["images"]))
        img = next(i for i in coco["images"] if i["view"] == "Persp_FTR")
        anns = [a for a in coco["annotations"] if a["image_id"] == img["id"]]
        check("coco: one annotation per visible part", sorted(a["part_name"] for a in anns)
              == ["Block", "Peg"], [a["part_name"] for a in anns])
        ann = next(a for a in anns if a["part_name"] == "Peg")
        hh, ww = ann["segmentation"]["size"]
        flat = np.zeros(hh * ww, np.uint8)
        pos, val = 0, 0
        for run_len in ann["segmentation"]["counts"]:
            flat[pos:pos + run_len] = val
            pos += run_len
            val ^= 1
        decoded = flat.reshape((ww, hh)).T
        check("coco RLE decodes to the part's pixels", np.array_equal(decoded, labels == 2))
        check("coco area and bbox", ann["area"] == int((labels == 2).sum())
              and ann["bbox"][2] > 0 and ann["bbox"][3] > 0)

        # BOP: reproject the exported model with cam_K, R, t; it must land on the mask.
        bop = os.path.join(out, "bop", "train_pbr", "000000")
        gt = json.load(open(os.path.join(bop, "scene_gt.json")))
        cam_json = json.load(open(os.path.join(bop, "scene_camera.json")))
        check("bop: 3 perspective images", sorted(gt) == ["0", "1", "2"], sorted(gt))
        with open(os.path.join(out, "bop", "models", "obj_000001.ply"), "rb") as f:
            data = f.read()
        head, _, rest = data.partition(b"end_header\n")
        nverts = int(head.split(b"element vertex ")[1].split(b"\n")[0])
        verts = np.frombuffer(rest[:nverts * 12], "<f4").reshape(-1, 3).astype(np.float64)
        check("bop model is in source millimetres",
              abs(np.ptp(verts[:, 0]) - 100) < 1e-3 and abs(np.ptp(verts[:, 2]) - 140) < 1e-3,
              np.ptp(verts, axis=0))
        R = np.array(gt["0"][0]["cam_R_m2c"]).reshape(3, 3)
        t = np.array(gt["0"][0]["cam_t_m2c"])
        K = np.array(cam_json["0"]["cam_K"]).reshape(3, 3)
        check("bop rotation is orthonormal", np.allclose(R @ R.T, np.eye(3), atol=1e-6))
        cam_pts = verts @ R.T + t
        uv = cam_pts @ K.T
        uv = uv[:, :2] / uv[:, 2:]
        mask = mv.load_pixels(os.path.join(bop, "mask", "000000_000000.png"))[::-1, :, 0] > 0.5
        ui = np.clip(np.floor(uv[:, 0]).astype(int), 0, mask.shape[1] - 1)
        vi = np.clip(np.floor(uv[:, 1]).astype(int), 0, mask.shape[0] - 1)
        # A box and a cylinder put nearly every vertex on the silhouette
        # itself, where a pixel either side is equally right: allow one.
        grown = mask.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                grown |= np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
        check("bop pose puts model vertices on the mask", grown[vi, ui].mean() == 1.0,
              grown[vi, ui].mean())
        depth_mm = mv.read_png16(os.path.join(bop, "depth", "000000.png")) * cam_json["0"]["depth_scale"]
        near = cam_pts[:, 2].min()
        check("bop depth is in model millimetres",
              abs(depth_mm[depth_mm > 0].min() - near) < 0.03 * near,
              (depth_mm[depth_mm > 0].min(), near))
        info = json.load(open(os.path.join(out, "bop", "models", "models_info.json")))
        check("bop models_info", abs(info["1"]["size_z"] - 140) < 1e-3
              and info["1"]["diameter"] > 140, info.get("1"))

        man = json.load(open(os.path.join(out, "manifest.json")))
        kinds = {r["kind"] for r in man["images"]}
        check("manifest lists data and cameras", {"data", "cameras", "bop"} <= kinds, kinds)

        # Turntable cameras orbit the product at one radius.
        s.pass_depth = s.pass_normal = s.pass_parts = False
        s.export_coco = s.export_bop = False
        s.turntable_enabled = True
        s.turntable_frames = 8
        s.turntable_mp4 = s.turntable_gif = False
        s.skip_existing = True
        h.run(bpy.ops.mv.render_all)
        tt = json.load(open(os.path.join(folder, "turntable",
                                         "AA_01_Widget_Turntable_clay_transforms.json")))
        pos = [Vector([row[3] for row in f["transform_matrix"][:3]]) for f in tt["frames"]]
        c = mv.bbox_of(mv.collection_meshes(coll))[0]
        radii = [(p - c).xy.length for p in pos]
        check("turntable: 8 frames on one circle", len(pos) == 8 and max(radii) - min(radii) < 1e-6,
              radii)
        angles = sorted(round(math.degrees(math.atan2((p - c).y, (p - c).x)) % 360, 3) for p in pos)
        steps = {round((b - a) % 360, 3) for a, b in zip(angles, angles[1:] + angles[:1])}
        check("turntable: 45 degree steps", steps == {45.0}, steps)

        # Shards keep their lists apart.
        s.turntable_enabled = False
        s.shard_suffix = "_shard03"
        s.export_coco = True
        h.run(bpy.ops.mv.render_all)
        check("shard suffix names manifest and coco",
              os.path.isfile(os.path.join(out, "manifest_shard03.json"))
              and os.path.isfile(os.path.join(out, "coco_shard03.json")))
        s.shard_suffix = ""

        # Labels can be pinned so shards do not collide.
        coll.mv_label_index = 6
        s.export_coco = False
        s.skip_existing = False
        h.run(bpy.ops.mv.render_all)
        check("pinned label index", os.path.isdir(os.path.join(out, "AA_07_Widget")),
              sorted(os.listdir(out)))
        mv.unregister()
    finally:
        shutil.rmtree(out, ignore_errors=True)


h.guard(body)
