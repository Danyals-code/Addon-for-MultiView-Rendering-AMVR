"""The three parts: the Part switcher's write-through, which panels each part
shows, and rendering the material patches on their own -- with no product, no
camera and no stage in the scene at all."""
import os
import sys
import json
import shutil
import subprocess
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as h  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
import multiview_product_renderer as mv  # noqa: E402

check = h.check
CLI = os.path.join(h.REPO, "multiview_product_renderer", "cli.py")


def make_pool(root):
    """Two minimal texture sets: a colour map each is all a material needs."""
    for folder, colour in (("Bricks_A", (0.9, 0.2, 0.2)), ("oak_veneer", (0.2, 0.7, 0.3))):
        os.makedirs(os.path.join(root, folder))
        px = np.zeros((8, 8, 4), np.float32)
        px[..., :3] = colour
        px[..., 3] = 1.0
        mv.save_pixels(px, os.path.join(root, folder, folder + "_Color.png"), 'PNG')


class Shim:
    """Stands in for a UILayout: every call returns another one and every
    attribute set is accepted, so draw() runs to completion off-screen."""

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self

    def __call__(self, *args, **kwargs):
        return Shim()

    def __setattr__(self, name, value):
        pass


class FakeSelf:
    """A Panel subclass cannot be built from Python, so draw() is called
    unbound with this as self: a layout shim, falling back to the class for
    anything else the method reaches for."""

    def __init__(self, cls):
        object.__setattr__(self, "_cls", cls)
        object.__setattr__(self, "layout", Shim())

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_cls"), name)


def panels():
    return [c for c in mv.classes if issubclass(c, bpy.types.Panel)]


def draw_all(part):
    """Poll and draw every panel for one part. (shown, failures)."""
    bpy.context.scene.mv_settings.part = part
    shown, failed = [], []
    for cls in panels():
        try:
            if hasattr(cls, "poll") and not cls.poll(bpy.context):
                continue
        except Exception:
            failed.append(f"{cls.__name__}.poll: {traceback.format_exc(0)}")
            continue
        shown.append(cls.__name__)
        for method in ("draw_header", "draw"):
            fn = cls.__dict__.get(method)
            if fn is None:
                continue
            try:
                fn(FakeSelf(cls), bpy.context)
            except Exception:
                failed.append(f"{cls.__name__}.{method}: {traceback.format_exc(0)}")
    return shown, failed


def blender(*args, timeout=600):
    cmd = [bpy.app.binary_path, "-b", "--factory-startup", "--python", CLI, "--", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout + proc.stderr


def body():
    mv.register()
    out = tempfile.mkdtemp(prefix="mv_parts_")
    try:
        scene = bpy.context.scene
        s = scene.mv_settings
        h.fresh_scene()

        # ---- the switcher writes through to what the renderer reads
        check("default part is Clay", s.part == 'CLAY', s.part)
        s.pool_variants = 7
        s.part = 'VARIANTS'
        check("Variants forces a Full render", s.render_mode == 'FULL', s.render_mode)
        check("Variants keeps a count already asked for", s.pool_variants == 7, s.pool_variants)
        s.part = 'CLAY'
        check("Clay clears variants and patches",
              s.render_mode == 'CLAY' and s.pool_variants == 0 and not s.pool_patches,
              (s.render_mode, s.pool_variants, s.pool_patches))
        s.part = 'VARIANTS'
        check("Variants fills in a default count", s.pool_variants == mv.DEFAULT_VARIANTS,
              s.pool_variants)
        s.part = 'PATCHES'
        check("Patches turns patches on and variants off",
              s.pool_patches and s.pool_variants == 0, (s.pool_patches, s.pool_variants))

        # Changing a part is a starting point, not a lock.
        s.part = 'CLAY'
        s.render_mode = 'BOTH'
        check("Clay can still be switched to Both", s.render_mode == 'BOTH')

        # ---- lighting follows the render mode, not the part
        check("Clay + Both is lit", mv.needs_lighting(s))
        s.render_mode = 'CLAY'
        check("plain clay is not lit", not mv.needs_lighting(s))
        s.turntable_enabled = True
        s.turntable_style = 'FULL'
        check("a Full turntable is lit", mv.needs_lighting(s))
        s.turntable_enabled = False

        # ---- panels: every part draws, and each hides what it cannot use
        pool_dir = os.path.join(out, "textures")
        make_pool(pool_dir)
        s.pool_folder = pool_dir
        bpy.ops.mv.scan_pool()
        check("pool scanned", len(s.material_pool) == 2, len(s.material_pool))

        coll, _ = h.add_product("Widget", lambda: bpy.ops.mesh.primitive_cube_add(size=2))
        shown, failed = {}, []
        for part in ('CLAY', 'PATCHES', 'VARIANTS'):
            shown[part], bad = draw_all(part)
            failed += bad
        check("every panel draws in every part", not failed, failed[:3])
        check("Patches hides products, views and stage",
              not {"MV_PT_Products", "MV_PT_Standardize", "MV_PT_Views", "MV_PT_ViewsOrient",
                   "MV_PT_Stage"} & set(shown['PATCHES']), shown['PATCHES'])
        check("Clay hides the pool, patch and variants panels",
              not {"MV_PT_Pool", "MV_PT_Patch", "MV_PT_Variants"} & set(shown['CLAY']),
              shown['CLAY'])
        check("Variants shows both halves",
              {"MV_PT_Products", "MV_PT_Views", "MV_PT_Pool", "MV_PT_Variants"}
              <= set(shown['VARIANTS']), shown['VARIANTS'])
        check("Patches is the shortest screen, Variants the longest",
              len(shown['PATCHES']) < len(shown['CLAY']) < len(shown['VARIANTS']),
              {k: len(v) for k, v in shown.items()})
        check("every sub-panel's parent is registered before it",
              all(order.index(c.bl_parent_id) < order.index(c.__name__)
                  for order in [[p.__name__ for p in panels()]]
                  for c in panels() if getattr(c, "bl_parent_id", "")))
        check("one sidebar tab", {c.bl_category for c in panels()} == {"CADshot"},
              {c.bl_category for c in panels()})

        # Stage drops lighting and ground when nothing in the run is lit.
        s.part = 'CLAY'
        s.render_mode = 'CLAY'
        check("Base Material is hidden for plain clay",
              not mv.MV_PT_StageMaterial.poll(bpy.context))
        s.render_mode = 'FULL'
        check("Base Material returns for a Full render",
              mv.MV_PT_StageMaterial.poll(bpy.context))
        s.render_mode = 'CLAY'

        # ---- pre-flight knows what each part needs
        s.part = 'PATCHES'
        s.render_output_dir = os.path.join(out, "patches") + os.sep
        messages = [i["message"] for i in mv.preflight(bpy.context)]
        check("Patches pre-flight asks for no cameras or views",
              not [m for m in messages if "camera" in m.lower() or "view" in m.lower()],
              messages)
        for item in s.material_pool:
            item.enabled = False
        errors = [i["message"] for i in mv.preflight(bpy.context) if i["severity"] == 'ERROR']
        check("Patches pre-flight still wants a pool",
              any("pool" in m.lower() for m in errors), errors)
        for item in s.material_pool:
            item.enabled = True

        # ---- patches render on their own, through the one job queue
        scene.render.resolution_x = scene.render.resolution_y = 32
        s.patch_size = 64
        r = h.run(bpy.ops.mv.render_all)
        root = os.path.join(out, "patches")
        made = sorted(os.listdir(os.path.join(root, "materials")))
        check("Patches part renders every ticked material",
              r == {'FINISHED'} and made == ["Bricks_A_patch.png", "oak_veneer_patch.png"],
              (r, made))
        check("it writes nothing else", sorted(os.listdir(root))
              == ["manifest.csv", "manifest.json", "materials"], sorted(os.listdir(root)))
        rows = json.load(open(os.path.join(root, "manifest.json")))["images"]
        check("patches reach the manifest",
              len(rows) == 2 and {x["kind"] for x in rows} == {"patch"}
              and all(x["width"] and x["height"] for x in rows), rows)
        check("the scene is left as it was",
              not any(m.name.startswith("MV_Pool_") for m in bpy.data.materials)
              and not any(sc.name.startswith("MV_Patch") for sc in bpy.data.scenes)
              and len(mv.get_products()) == 1,
              [m.name for m in bpy.data.materials])

        # Skip Existing covers them like any other output.
        s.skip_existing = True
        before = {n: os.path.getmtime(os.path.join(root, "materials", n)) for n in made}
        r = h.run(bpy.ops.mv.render_all)
        after = {n: os.path.getmtime(os.path.join(root, "materials", n)) for n in made}
        check("Skip Existing leaves finished patches alone", before == after, r)
        s.skip_existing = False

        # A product in the scene makes no difference: patches ignore it.
        check("a product in the scene is not rendered by the Patches part",
              not any(d.startswith("AA_") for d in os.listdir(root)), os.listdir(root))

        # ---- and with no product in the scene at all
        bpy.data.collections.remove(coll)
        s.render_output_dir = os.path.join(out, "bare") + os.sep
        r = h.run(bpy.ops.mv.render_all)
        check("Patches needs no product at all",
              r == {'FINISHED'}
              and len(os.listdir(os.path.join(out, "bare", "materials"))) == 2, r)

        # Clay with no product is still an error.
        s.part = 'CLAY'
        r = h.run(bpy.ops.mv.render_all)
        check("Clay with no product is still refused", r == {'CANCELLED'}, r)

        # ---- a patches-only job file, with no inputs
        job = os.path.join(out, "patches.json")
        with open(job, "w") as f:
            json.dump({"output": "cli_out",
                       "settings": {"part": "PATCHES", "pool_folder": pool_dir,
                                    "patch_size": 64, "manifest_format": "JSON"},
                       "render": {"resolution": [32, 32]}}, f)
        code, log = blender("--config", job)
        cli_out = os.path.join(out, "cli_out", "materials")
        check("a job with no inputs renders the pool",
              code == 0 and os.path.isdir(cli_out) and len(os.listdir(cli_out)) == 2,
              (code, log[-500:]))

        mv.unregister()
    finally:
        shutil.rmtree(out, ignore_errors=True)


h.guard(body)
