"""Engineering drawings: visible and hidden lines, true scale, sheet layout."""
import os
import re
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as h  # noqa: E402

import bpy  # noqa: E402
import multiview_product_renderer as mv  # noqa: E402

check = h.check


def paths(svg, cls):
    """Every line segment of the paths with this class."""
    segs = []
    for m in re.finditer(r'<path class="%s" d="([^"]*)"' % cls, svg):
        nums = [float(v) for v in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", m.group(1))]
        segs += [nums[i:i + 4] for i in range(0, len(nums), 4)]
    return segs


def extent(segs):
    xs = [v for s in segs for v in (s[0], s[2])]
    ys = [v for s in segs for v in (s[1], s[3])]
    return min(xs), min(ys), max(xs), max(ys)


def body():
    mv.register()
    scene = bpy.context.scene
    s = scene.mv_settings
    h.fresh_scene()
    out = tempfile.mkdtemp(prefix="mv_draw_")
    try:
        # A 100 x 60 x 40 mm block, and a 20 mm cube hidden behind it as seen
        # from the front (Front Axis +X: the front camera looks along -X).
        coll, (block, cube) = h.add_product(
            "Stepped",
            lambda: bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0)),
            lambda: bpy.ops.mesh.primitive_cube_add(size=20, location=(-70, 0, 0)))
        block.scale = (100, 60, 40)
        bpy.context.view_layer.objects.active = block
        bpy.ops.object.transform_apply(scale=True)
        mv.record_source_size(coll, "mm")
        ball, (sphere,) = h.add_product(
            "Ball", lambda: bpy.ops.mesh.primitive_uv_sphere_add(radius=25, segments=48,
                                                                 ring_count=24, location=(0, 0, 0)))
        bpy.ops.object.shade_smooth()
        mv.record_source_size(ball, "mm")

        s.render_output_dir = out + os.sep
        s.render_mode = 'CLAY'
        s.view_set = 'MIN'
        s.export_cameras = False
        s.manifest_format = 'NONE'
        s.reframe_on_render = True
        scene.render.resolution_x = scene.render.resolution_y = 32
        s.export_drawings = True
        s.drawing_resolution = 1024
        r = h.run(bpy.ops.mv.render_all)
        check("render finished", r == {'FINISHED'}, r)
        folder = os.path.join(out, "AA_01_Stepped")
        names = sorted(os.listdir(folder))
        for f in ("AA_01_Stepped_Front_drawing.svg", "AA_01_Stepped_Top_drawing.svg",
                  "AA_01_Stepped_Right_drawing.svg", "AA_01_Stepped_Drawing.svg"):
            check(f"wrote {f}", f in names, names)

        front = open(os.path.join(folder, "AA_01_Stepped_Front_drawing.svg")).read()
        vis, hid = paths(front, "visible"), paths(front, "hidden")
        x0, y0, x1, y1 = extent(vis)
        check("front: 60 x 40 mm at 1:1", abs((x1 - x0) - 60) < 0.2 and abs((y1 - y0) - 40) < 0.2,
              (x1 - x0, y1 - y0))
        check("front: units are mm", 'width="' in front and 'mm"' in front)
        # The hidden cube's edges: a 20 mm square, dashed, inside the block.
        hx0, hy0, hx1, hy1 = extent(hid) if hid else (0, 0, 0, 0)
        inner = [sg for sg in hid if max(abs(sg[0] - (x0 + x1) / 2), abs(sg[2] - (x0 + x1) / 2)) <= 10.2
                 and max(abs(sg[1] - (y0 + y1) / 2), abs(sg[3] - (y0 + y1) / 2)) <= 10.2]
        check("front: hidden cube drawn dashed", len(inner) >= 4, len(inner))
        inner_vis = [sg for sg in vis if max(abs(sg[0] - (x0 + x1) / 2), abs(sg[2] - (x0 + x1) / 2)) < 9
                     and max(abs(sg[1] - (y0 + y1) / 2), abs(sg[3] - (y0 + y1) / 2)) < 9]
        check("front: no visible line inside the block face", not inner_vis, inner_vis[:3])
        check("front: overall dimensions printed", ">60.00<" in front and ">40.00<" in front)

        top = open(os.path.join(folder, "AA_01_Stepped_Top_drawing.svg")).read()
        tx0, ty0, tx1, ty1 = extent(paths(top, "visible"))
        check("top: 60 wide (aligned with front), 130 deep", abs((tx1 - tx0) - 60) < 0.2
              and abs((ty1 - ty0) - 130) < 0.3, (tx1 - tx0, ty1 - ty0))
        right = open(os.path.join(folder, "AA_01_Stepped_Right_drawing.svg")).read()
        rx0, ry0, rx1, ry1 = extent(paths(right, "visible"))
        check("right: 130 wide, 40 high", abs((rx1 - rx0) - 130) < 0.3 and abs((ry1 - ry0) - 40) < 0.2,
              (rx1 - rx0, ry1 - ry0))

        # Third angle: plan above the front, right view to the right.
        sheet = open(os.path.join(folder, "AA_01_Stepped_Drawing.svg")).read()
        groups = re.findall(r'<path class="visible" d="([^"]*)"', sheet)
        check("sheet has three views", len(groups) == 3, len(groups))
        boxes = []
        for g in groups:
            nums = [float(v) for v in re.findall(r"-?\d+\.?\d*", g)]
            boxes.append((min(nums[0::2]), min(nums[1::2]), max(nums[0::2]), max(nums[1::2])))
        fb, tb, rb = boxes
        check("third angle: plan above front", tb[3] < fb[1], (tb, fb))
        check("third angle: right view right of front", rb[0] > fb[2], (rb, fb))
        check("plan and front share x", abs(tb[0] - fb[0]) < 0.3 and abs(tb[2] - fb[2]) < 0.3)

        s.drawing_projection = 'FIRST'
        h.run(bpy.ops.mv.render_all)
        sheet = open(os.path.join(folder, "AA_01_Stepped_Drawing.svg")).read()
        groups = re.findall(r'<path class="visible" d="([^"]*)"', sheet)
        boxes = []
        for g in groups:
            nums = [float(v) for v in re.findall(r"-?\d+\.?\d*", g)]
            boxes.append((min(nums[0::2]), min(nums[1::2]), max(nums[0::2]), max(nums[1::2])))
        fb, tb, rb = boxes
        check("first angle: plan below, right view on the left", tb[1] > fb[3] and rb[2] < fb[0],
              (fb, tb, rb))

        # A smooth sphere has no creases: only its outline, a 50 mm circle.
        ball_front = open(os.path.join(out, "AA_02_Ball", "AA_02_Ball_Front_drawing.svg")).read()
        bv = paths(ball_front, "visible")
        bx0, by0, bx1, by1 = extent(bv)
        check("sphere: outline 50 mm across", abs((bx1 - bx0) - 50) < 0.5, bx1 - bx0)
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
        radii = [((sg[0] - cx) ** 2 + (sg[1] - cy) ** 2) ** 0.5 for sg in bv]
        check("sphere: only the silhouette, no inner lines", min(radii) > 23.5, min(radii))

        s.drawing_hidden = False
        h.run(bpy.ops.mv.render_all)
        front = open(os.path.join(folder, "AA_01_Stepped_Front_drawing.svg")).read()
        check("hidden lines can be turned off", 'class="hidden"' not in front)
        check("ground and staging stay out of drawings", not mv.staging_objects()
              or all(not o.hide_render for o in mv.staging_objects()))
        mv.unregister()
    finally:
        shutil.rmtree(out, ignore_errors=True)


h.guard(body)
