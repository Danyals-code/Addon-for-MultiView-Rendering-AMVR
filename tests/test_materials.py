"""Material pool: scanning texture folders, box-projected PBR materials,
rendered patches and seeded product variants."""
import os
import sys
import json
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as h  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
import multiview_product_renderer as mv  # noqa: E402

check = h.check


def checker(colour, size=64, squares=4):
    """A two-tone checker in colour, so the texture shows up as variance."""
    yy, xx = np.mgrid[0:size, 0:size] // (size // squares)
    dark = ((yy + xx) % 2)[..., None].astype(np.float32)
    rgb = np.array(colour, dtype=np.float32) * (1.0 - 0.6 * dark)
    return np.concatenate([rgb, np.ones((size, size, 1), np.float32)], axis=2)


def grey(value, size=16):
    px = np.full((size, size, 4), value, np.float32)
    px[..., 3] = 1.0
    return px


def make_pool(root):
    """Texture sets named the way the big free libraries name them."""
    sets = {
        # ambientCG
        "Bricks_A": {"Bricks_A_1K-PNG_Color.png": checker((0.9, 0.1, 0.1)),
                     "Bricks_A_1K-PNG_Roughness.png": grey(0.8),
                     "Bricks_A_1K-PNG_NormalGL.png": grey(0.5),
                     "Bricks_A_1K-PNG_Displacement.png": grey(0.5)},
        # Poly Haven
        "oak_veneer": {"oak_veneer_diff_1k.png": checker((0.1, 0.8, 0.1)),
                       "oak_veneer_rough_1k.png": grey(0.6),
                       "oak_veneer_arm_1k.png": grey(0.3),
                       "oak_veneer_nor_gl_1k.png": grey(0.5)},
        # "metal" in the name must not read as a metallic map.
        "Metal_Plate": {"Metal_Plate_Color.jpg": checker((0.1, 0.2, 0.9)),
                        "Metal_Plate_Metalness.png": grey(1.0)},
        # Not materials: no colour map, or no images at all.
        "loose_maps": {"thing_rough.png": grey(0.5)},
    }
    for folder, files in sets.items():
        os.makedirs(os.path.join(root, folder))
        for name, px in files.items():
            fmt = 'JPEG' if name.endswith(".jpg") else 'PNG'
            mv.save_pixels(px, os.path.join(root, folder, name), fmt)
    os.makedirs(os.path.join(root, "notes"))
    with open(os.path.join(root, "notes", "readme.txt"), "w") as f:
        f.write("not a texture")


def manifest_rows(root):
    return json.load(open(os.path.join(root, "manifest.json")))["images"]


def body():
    mv.register()
    scene = bpy.context.scene
    s = scene.mv_settings
    h.fresh_scene()
    out = tempfile.mkdtemp(prefix="mv_pool_")
    try:
        pool_dir = os.path.join(out, "textures")
        make_pool(pool_dir)

        # ---- scanning and map classification
        found = dict(mv.scan_pool(pool_dir))
        check("scan finds the three texture sets", sorted(found) == ["Bricks_A", "Metal_Plate",
                                                                     "oak_veneer"], sorted(found))
        bricks, oak, metal = found["Bricks_A"], found["oak_veneer"], found["Metal_Plate"]
        check("ambientCG: colour, roughness, normal, height",
              {k: os.path.basename(v) for k, v in bricks.items()} == {
                  "color": "Bricks_A_1K-PNG_Color.png",
                  "roughness": "Bricks_A_1K-PNG_Roughness.png",
                  "normal": "Bricks_A_1K-PNG_NormalGL.png",
                  "height": "Bricks_A_1K-PNG_Displacement.png"}, bricks)
        check("Poly Haven: diff, rough, arm, nor_gl",
              {k: os.path.basename(v) for k, v in oak.items()} == {
                  "color": "oak_veneer_diff_1k.png", "roughness": "oak_veneer_rough_1k.png",
                  "arm": "oak_veneer_arm_1k.png", "normal": "oak_veneer_nor_gl_1k.png"}, oak)
        check("a material named Metal keeps its colour map",
              os.path.basename(metal.get("color", "")) == "Metal_Plate_Color.jpg"
              and os.path.basename(metal.get("metallic", "")) == "Metal_Plate_Metalness.png", metal)
        check("DirectX normals stand in for OpenGL ones",
              mv.classify_maps(["x_Color.png", "x_NormalDX.png"]).get("normal") == "x_NormalDX.png")
        # Names whose shared start runs into the map words.
        check("diff + disp: prefix stops at the separator",
              mv.classify_maps(["rock_diff_1k.png", "rock_disp_1k.png"])
              == {"color": "rock_diff_1k.png", "height": "rock_disp_1k.png"})
        check("albedo + ao", mv.classify_maps(["albedo.png", "ao.png"]).get("color") == "albedo.png")
        check("basecolor + bump",
              mv.classify_maps(["basecolor.png", "bump.png"]).get("color") == "basecolor.png")
        check("a lone image is the colour, even one called Metal",
              mv.classify_maps(["Brushed_Metal.jpg"]) == {"color": "Brushed_Metal.jpg"})
        check("one unnamed image beside named maps is the colour",
              mv.classify_maps(["oak.jpg", "oak_rough.jpg"]).get("color") == "oak.jpg")
        check("a lone metalness map is not a colour",
              mv.classify_maps(["Metal032_1K-JPG_Metalness.jpg"])
              == {"metallic": "Metal032_1K-JPG_Metalness.jpg"})

        # Names: packing folders take their parent's name, and duplicates are
        # told apart by their path.
        naming = os.path.join(out, "naming")
        for rel in ("a/Oak/x_Color.png", "b/Oak/y_Color.png",
                    "rock_wall/textures/rock_wall_diff_1k.png",
                    "rock_wall/textures/rock_wall_disp_1k.png",
                    "lib2/rock_wall/textures/rock_wall_diff_1k.png", "plain/oak.jpg"):
            path = os.path.join(naming, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            mv.save_pixels(grey(0.5), path, 'JPEG' if rel.endswith(".jpg") else 'PNG')
        names = sorted(n for n, _ in mv.scan_pool(naming))
        check("unique names from the folders",
              names == ["a_Oak", "b_Oak", "lib2_rock_wall", "plain", "rock_wall"], names)

        # A material keeps its name, and its tick, when a namesake turns up.
        grow = os.path.join(out, "grow")
        os.makedirs(os.path.join(grow, "Oak"))
        mv.save_pixels(grey(0.5), os.path.join(grow, "Oak", "Oak_Color.png"), 'PNG')
        s.pool_folder = grow
        mv.scan_pool_into(s)
        s.material_pool["Oak"].enabled = False
        os.makedirs(os.path.join(grow, "more", "Oak"))
        mv.save_pixels(grey(0.5), os.path.join(grow, "more", "Oak", "Oak_Color.png"), 'PNG')
        mv.scan_pool_into(s)
        kept = {m.name: (m.enabled, m.key) for m in s.material_pool}
        check("rescan keeps the old name and tick; the newcomer gets its path",
              kept == {"Oak": (False, mv.pool_key(grow, os.path.join(grow, "Oak", "Oak_Color.png"))),
                       "more_Oak": (True, mv.pool_key(grow, os.path.join(grow, "more", "Oak",
                                                                         "Oak_Color.png")))}, kept)
        s.material_pool.clear()

        s.pool_folder = pool_dir
        r = h.run(bpy.ops.mv.scan_pool)
        check("Scan Folder fills the pool", r == {'FINISHED'} and len(s.material_pool) == 3, r)
        s.material_pool["Metal_Plate"].enabled = False
        bpy.ops.mv.scan_pool()
        check("rescanning keeps the ticks", not s.material_pool["Metal_Plate"].enabled
              and s.material_pool["oak_veneer"].enabled)
        check("only ticked materials are used",
              [n for n, _ in mv.pool_entries(s)] == ["Bricks_A", "oak_veneer"])
        bpy.ops.mv.set_pool(state=True)
        check("tick all", all(m.enabled for m in s.material_pool))
        s.pool_folder = os.path.join(out, "nowhere")
        check("scan of a missing folder cancels", h.run(bpy.ops.mv.scan_pool) == {'CANCELLED'})
        s.pool_folder = pool_dir

        # ---- the material
        mat = mv.pool_material("oak_veneer", oak)
        nodes = mat.node_tree.nodes
        images = [n for n in nodes if n.type == 'TEX_IMAGE']
        check("one image node per used map", len(images) == 3, [n.image.name for n in images])
        check("every texture is box projected", all(n.projection == 'BOX' for n in images))
        spaces = {os.path.basename(n.image.filepath): n.image.colorspace_settings.name
                  for n in images}
        check("colour in sRGB, data maps Non-Color",
              spaces.get("oak_veneer_diff_1k.png") == "sRGB"
              and spaces.get("oak_veneer_rough_1k.png") == "Non-Color"
              and spaces.get("oak_veneer_arm_1k.png") == "Non-Color", spaces)
        bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
        metal_src = bsdf.inputs["Metallic"].links[0].from_node if bsdf.inputs["Metallic"].links else None
        check("packed ARM drives metallic", metal_src is not None and metal_src.type == 'SEPARATE_COLOR')
        check("roughness map wins over the packed one",
              bsdf.inputs["Roughness"].links[0].from_node.type == 'TEX_IMAGE')
        attr = next(n for n in nodes if n.type == 'ATTRIBUTE')
        check("scale read from the object", attr.attribute_type == 'OBJECT'
              and attr.attribute_name == mv.TILE_KEY)
        bmat = mv.pool_material("Bricks_A", bricks)
        check("height map becomes a bump", any(n.type == 'BUMP' for n in bmat.node_tree.nodes))
        omat = mv.pool_material("Holey", dict(bricks, opacity=bricks["roughness"]))
        obsdf = next(n for n in omat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        check("opacity maps are not used", not obsdf.inputs["Alpha"].is_linked)
        mv.save_pixels(grey(0.5), os.path.join(out, "lonely_Color.png"), 'PNG')
        extra = s.material_pool.add()
        extra.name = "lonely"
        extra.maps = json.dumps({"color": os.path.join(out, "lonely_Color.png"),
                                 "normal": os.path.join(out, "gone_Normal.png")})
        check("a missing normal map does not count as missing", mv.pool_missing(s) == [],
              mv.pool_missing(s))
        extra.maps = json.dumps({"color": os.path.join(out, "gone_Color.png")})
        check("a missing colour map does", mv.pool_missing(s) == ["lonely"], mv.pool_missing(s))
        s.material_pool.remove(len(s.material_pool) - 1)
        first_node = mat.node_tree.nodes[0].as_pointer()
        check("the same material is reused, not rebuilt",
              mv.pool_material("oak_veneer", oak) == mat
              and mat.node_tree.nodes[0].as_pointer() == first_node)

        # ---- patches
        scene.render.engine = 'BLENDER_WORKBENCH'
        scenes, objects = len(bpy.data.scenes), len(bpy.data.objects)
        # Labels off, so the grid has no title or row gutter and every tile
        # sits at an offset the test can work out for itself.
        s.patch_labels = False
        patch = os.path.join(out, "patch.png")
        w, hgt = mv.render_patch(bpy.context, "Bricks_A", bricks, patch, 96)
        check("patch written", os.path.isfile(patch))
        px = mv.load_pixels(patch)
        gap = max(6, 96 // 32)
        check("default patch is two tiles across and one lighting down",
              px.shape[1] == w and px.shape[0] == hgt
              and w == 2 * 96 + 3 * gap and hgt == 96 + 2 * gap,
              (px.shape, w, hgt))
        check("patch scene and objects cleaned up", len(bpy.data.scenes) == scenes
              and len(bpy.data.objects) == objects and scene.render.engine == 'BLENDER_WORKBENCH')

        def tile(image, col):
            """One tile of the top row, rows running top-down."""
            top = image[::-1]
            x = gap + col * (96 + gap)
            return top[gap:gap + 96, x:x + 96, :3]

        flat, ball = tile(px, 0), tile(px, 1)
        flat_red = flat[..., 0] - flat[..., 2]
        check("flat swatch shows the red checker", (flat_red > 0.1).mean() > 0.95,
              float((flat_red > 0.1).mean()))
        check("flat swatch shows both checker tones",
              np.percentile(flat[..., 0], 90) - np.percentile(flat[..., 0], 10) > 0.15)
        # The sphere is rendered on transparent film and composited onto the
        # grid's white background, so the tile is a red ball surrounded by white.
        subject = ball.min(axis=2) < 0.85
        check("the sphere tile holds a red sphere on white",
              0.3 < subject.mean() < 0.85
              and float((ball[..., 0] - ball[..., 2])[subject].mean()) > 0.1,
              (float(subject.mean()),
               float((ball[..., 0] - ball[..., 2])[subject].mean())))
        # The scene's colour management carries over to the patch.
        scene.view_settings.exposure = -1.5
        mv.render_patch(bpy.context, "Bricks_A", bricks, os.path.join(out, "dark.png"), 96)
        scene.view_settings.exposure = 0.0
        dark_flat = tile(mv.load_pixels(os.path.join(out, "dark.png")), 0)
        check("patch follows the scene's exposure",
              dark_flat[..., 0].mean() < flat[..., 0].mean() - 0.1,
              (float(dark_flat[..., 0].mean()), float(flat[..., 0].mean())))
        s.patch_labels = True

        # ---- a two-part product
        coll, (block, peg) = h.add_product(
            "Widget",
            lambda: bpy.ops.mesh.primitive_cube_add(size=100, location=(0, 0, 50)),
            lambda: bpy.ops.mesh.primitive_cylinder_add(radius=20, depth=40, location=(0, 0, 120)))
        block.name, peg.name = "Block", "Peg"
        mv.record_source_size(coll, "mm")
        bpy.context.view_layer.update()
        s.recenter = s.rescale = True
        s.auto_smooth = False
        bpy.ops.mv.standardize()
        bpy.context.view_layer.update()
        # One repeat covers Tile Size of the real part.
        s.pool_tile_mm = 50.0
        world_per_mm = mv.product_to_world(coll).to_3x3().determinant() ** (1 / 3)
        obj_scale = sum(block.matrix_world.to_3x3().to_scale()) / 3
        repeat_obj = 50.0 * world_per_mm / obj_scale
        check("tile scale: one repeat per 50 mm",
              abs(mv.tile_scale(block, coll, 50.0) * repeat_obj - 1.0) < 1e-6)
        loose, (lcube,) = h.add_product("Loose",
                                        lambda: bpy.ops.mesh.primitive_cube_add(size=0.3))
        check("hand-built, never standardized: metres",
              loose.mv_source_units == "" and abs(mv.tile_scale(lcube, loose, 100.0) - 10.0) < 1e-6,
              mv.tile_scale(lcube, loose, 100.0))
        bpy.data.objects.remove(lcube)
        bpy.data.collections.remove(loose)

        # {variant} in the folder template puts variants in folders instead.
        values = mv.name_values(s, 0, "Widget", "Front", "", "v02")
        check("variant appended to a file name without it",
              mv.output_basename(s, values).endswith("_v02"), mv.output_basename(s, values))
        s.folder_template = "{label}_{product}/{variant}"
        check("variant folder: file name left alone",
              not mv.output_basename(s, values).endswith("v02")
              and mv.output_folder(s, values).replace("\\", "/").endswith("/v02"),
              (mv.output_folder(s, values), mv.output_basename(s, values)))
        s.folder_template = ""

        # ---- variant draws
        s.pool_seed = 5
        s.pool_variants = 4
        s.pool_per_part = True
        entries = mv.pool_entries(s)
        a = mv.variant_assignments(s, "AA_01", ["Block", "Peg"], entries)
        check("four variants named v01..v04", [n for n, _ in a] == ["v01", "v02", "v03", "v04"])
        check("every part gets a pool material", all(set(x) == {"Block", "Peg"}
                                                    and set(x.values()) <= dict(entries).keys()
                                                    for _, x in a))
        check("same seed, same draws", a == mv.variant_assignments(s, "AA_01", ["Block", "Peg"],
                                                                   entries))
        s.pool_variants = 6
        check("more variants keep the first ones",
              mv.variant_assignments(s, "AA_01", ["Block", "Peg"], entries)[:4] == a)
        s.pool_seed = 6
        check("other seed, other draws",
              mv.variant_assignments(s, "AA_01", ["Block", "Peg"], entries)[:4] != a)
        s.pool_per_part = False
        whole = mv.variant_assignments(s, "AA_01", ["Block", "Peg"], entries)
        check("whole-product mode: one material per variant",
              all(len(set(x.values())) == 1 for _, x in whole))
        check("materials text", mv.materials_text({"Peg": "Oak", "Block": "Steel"})
              == "Block=Steel; Peg=Oak")

        # Changing the pool moves only the draws that material won or held.
        s.pool_per_part = True
        s.pool_variants = 40
        parts = ["Block", "Peg", "Lid"]
        before = mv.variant_assignments(s, "AA_01", parts, entries)
        s.material_pool["oak_veneer"].enabled = False
        after = mv.variant_assignments(s, "AA_01", parts, mv.pool_entries(s))
        moved = [(b[p], a[p]) for (_, b), (_, a) in zip(before, after) for p in parts
                 if b[p] != a[p]]
        check("unticking moves only that material's draws",
              moved and all(old == "oak_veneer" for old, _ in moved), moved[:4])
        s.material_pool["oak_veneer"].enabled = True
        counts = {}
        for _, x in before:
            for m in x.values():
                counts[m] = counts.get(m, 0) + 1
        check("draws spread over the pool", len(counts) == 3 and min(counts.values()) >= 20,
              counts)

        # ---- render all with variants and patches
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 4
        scene.cycles.device = 'CPU'
        scene.cycles.use_denoising = False
        scene.render.resolution_x, scene.render.resolution_y = 64, 48
        s.render_output_dir = os.path.join(out, "r") + os.sep
        s.render_mode = 'BOTH'
        s.view_set = 'MIN'
        s.manifest_format = 'JSON'
        s.export_cameras = False
        s.pool_seed = 5
        s.pool_variants = 3
        s.pool_per_part = True
        s.pool_patches = True
        s.patch_size = 64
        s.pass_mask = True
        r = h.run(bpy.ops.mv.render_all)
        check("render with variants finished", r == {'FINISHED'}, r)
        root = os.path.join(out, "r")
        rows = manifest_rows(root)
        full = [x for x in rows if x["kind"] == "render" and x["mode"] == "render"]
        clay = [x for x in rows if x["kind"] == "render" and x["mode"] == "clay"]
        check("clay rendered once per view", clay and all(x["variant"] == "" for x in clay),
              [(x["mode"], x["variant"]) for x in rows])
        check("three Full variants per view", len(full) == 3 * len(clay)
              and {x["variant"] for x in full} == {"v01", "v02", "v03"}, len(full))
        check("variant files carry the suffix", all(x["path"].endswith(f"_{x['variant']}.png")
                                                    for x in full), full[0]["path"])
        check("all variant files exist", all(os.path.isfile(os.path.join(root, x["path"]))
                                             for x in full + clay))
        want = mv.variant_assignments(s, full[0]["label"], ["Block", "Peg"], mv.pool_entries(s))
        check("manifest lists each variant's materials",
              {x["variant"]: x["materials"] for x in full}
              == {n: mv.materials_text(m) for n, m in want}, full[0]["materials"])
        patches = sorted(os.listdir(os.path.join(root, "materials")))
        check("one patch per pool material", patches == ["Bricks_A_patch.png", "Metal_Plate_patch.png",
                                                         "oak_veneer_patch.png"], patches)
        check("patches in the manifest", sum(x["kind"] == "patch" for x in rows) == 3)
        sheets = [x for x in rows if x["kind"] == "sheet"]
        check("one contact sheet per variant and for clay",
              not sheets or len(sheets) == 4, [x["path"] for x in sheets])

        # The texture is what changed: a variant drawn all-red and one drawn
        # all-blue look red and blue.
        by_mat = {}
        for x in full:
            mats = set(m.split("=")[1] for m in x["materials"].split("; "))
            if len(mats) == 1:
                by_mat.setdefault(mats.pop(), x)
        img = {m: mv.load_pixels(os.path.join(root, x["path"])) for m, x in by_mat.items()}

        def redness(px):
            sel = px[..., 3] > 0.5 if s.transparent_bg else np.ones(px.shape[:2], bool)
            return float((px[..., 0] - px[..., 2])[sel].mean())
        if "Bricks_A" in img and "Metal_Plate" in img:
            check("red pool material renders red, blue renders blue",
                  redness(img["Bricks_A"]) > redness(img["Metal_Plate"]) + 0.1,
                  (redness(img["Bricks_A"]), redness(img["Metal_Plate"])))
        else:
            imgs = [mv.load_pixels(os.path.join(root, x["path"])) for x in full
                    if x["view"] == full[0]["view"]]
            check("variants look different", max(np.abs(imgs[0] - i).max() for i in imgs[1:]) > 0.1)

        check("modifiers and tile scales removed afterwards",
              not any(md.name.startswith(mv.MATERIAL_MOD) for o in bpy.data.objects
                      for md in o.modifiers)
              and not any(mv.TILE_KEY in o for o in bpy.data.objects))
        check("user materials untouched", not block.data.materials
              or not block.data.materials[0].name.startswith("MV_Pool_"))
        check("pool materials and their textures deleted afterwards",
              not any(m.name.startswith("MV_Pool_") for m in bpy.data.materials)
              and not any(pool_dir in bpy.path.abspath(i.filepath) for i in bpy.data.images),
              [m.name for m in bpy.data.materials])
        check("every manifest row has variant and materials",
              all("variant" in x and "materials" in x and x["variant"] is not None for x in rows)
              and any("mask" in f"{x['kind']} {x['mode']}" for x in rows),
              sorted({(x["kind"], x["mode"]) for x in rows}))
        prov = json.load(open(os.path.join(root, "manifest.json")))["provenance"]["settings"]
        check("provenance records the pool",
              [m["name"] for m in prov.get("material_pool", [])]
              == ["Bricks_A", "Metal_Plate", "oak_veneer"]
              and prov["material_pool"][0]["maps"]["color"] == "Bricks_A_1K-PNG_Color.png",
              prov.get("material_pool"))

        # A second run with the same seed reproduces the same images.
        first = {x["path"]: mv.load_pixels(os.path.join(root, x["path"])) for x in full}
        s.render_output_dir = os.path.join(out, "r2") + os.sep
        h.run(bpy.ops.mv.render_all)
        same = all(np.abs(px - mv.load_pixels(os.path.join(out, "r2", p))).max() < 1e-6
                   for p, px in first.items())
        check("same seed, same variant images", same)

        # Keep Own products render once, in their own materials.
        coll.mv_material = 'KEEP'
        s.render_output_dir = os.path.join(out, "keep") + os.sep
        h.run(bpy.ops.mv.render_all)
        keep_rows = manifest_rows(os.path.join(out, "keep"))
        keep_full = [x for x in keep_rows if x["kind"] == "render" and x["mode"] == "render"]
        check("Keep Own: no variants", keep_full and len(keep_full) == len(clay)
              and all(x["variant"] == "" for x in keep_full), len(keep_full))
        coll.mv_material = 'DEFAULT'

        # Rendering only the active product leaves the patches alone.
        s.render_output_dir = os.path.join(out, "active") + os.sep
        r = h.run(bpy.ops.mv.render_all, only_active=True)
        check("Render Active Product skips patches", r == {'FINISHED'}
              and not os.path.isdir(os.path.join(out, "active", "materials")), r)

        # ---- shards: only the first makes the patches
        s.pass_mask = False
        s.render_mode = 'CLAY'
        s.shard_suffix = "_shard01"
        s.render_output_dir = os.path.join(out, "s1") + os.sep
        h.run(bpy.ops.mv.render_all)
        check("later shards leave patches alone",
              not os.path.isdir(os.path.join(out, "s1", "materials")))
        s.shard_suffix = "_shard00"
        s.render_output_dir = os.path.join(out, "s0") + os.sep
        h.run(bpy.ops.mv.render_all)
        check("the first shard makes them", len(os.listdir(os.path.join(out, "s0", "materials"))) == 3)
        s.shard_suffix = ""

        # ---- a moved texture library
        moved = os.path.join(out, "moved_textures")
        shutil.copytree(pool_dir, moved)
        s.pool_folder = moved
        shutil.rmtree(pool_dir)
        issues = [i["message"] for i in mv.preflight(bpy.context) if i["severity"] == 'ERROR']
        check("moved library: rescanned, no pre-flight error",
              not any("pool" in m.lower() for m in issues)
              and all(p.startswith(moved) for _, maps in mv.pool_entries(s) for p in maps.values()),
              issues)
        shutil.copytree(moved, os.path.join(out, "gone"))
        s.pool_folder = os.path.join(out, "gone")
        bpy.ops.mv.scan_pool()
        shutil.rmtree(os.path.join(out, "gone"))
        issues = [i["message"] for i in mv.preflight(bpy.context) if i["severity"] == 'ERROR']
        check("missing textures stop the batch", any("missing" in m for m in issues), issues)

        # ---- pre-flight
        s.material_pool.clear()
        s.pool_folder = os.path.join(out, "nowhere")
        issues = [i["message"] for i in mv.preflight(bpy.context) if i["severity"] == 'ERROR']
        check("pre-flight: empty pool is an error", any("pool" in m.lower() for m in issues),
              issues)
        s.pool_variants = 0
        s.pool_patches = False
        mv.unregister()
    finally:
        shutil.rmtree(out, ignore_errors=True)


h.guard(body)
