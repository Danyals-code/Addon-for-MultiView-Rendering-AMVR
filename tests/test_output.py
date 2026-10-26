import sys, os, shutil, tempfile, json, csv, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bpy
import numpy as np
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

mv.register()
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
add_product("Knob", lambda: bpy.ops.mesh.primitive_monkey_add(size=1))
root.children["Widget"].mv_source = "C:/cad/widget.step"
root.children["Widget"].mv_source_size = (120.0, 40.0, 15.5)

scene.render.resolution_x = 96
scene.render.resolution_y = 64
scene.render.film_transparent = True
s = scene.mv_settings
# Camera files are covered by test_annotations; these count image files.
s.export_cameras = False
s.render_mode = 'CLAY'
s.view_set = 'MIN'

out = tempfile.mkdtemp(prefix="mv_out_")
s.render_output_dir = out + os.sep
def files(sub=""):
    found = []
    for d, _, fs in os.walk(os.path.join(out, sub)):
        for f in fs:
            found.append(os.path.relpath(os.path.join(d, f), out).replace("\\", "/"))
    return sorted(found)
def reset():
    shutil.rmtree(out); os.makedirs(out)
def px(path):
    return mv.load_pixels(os.path.join(out, path))

try:
    # ---- naming units
    v = {"label": "AA_01", "prefix": "AA", "number": "01", "product": "Widget", "view": "Front", "mode": ""}
    E = mv.expand_template
    check("tmpl trailing empty", E("{label}_{product}_{view}_{mode}", v) == "AA_01_Widget_Front", E("{label}_{product}_{view}_{mode}", v))
    check("tmpl leading empty", E("{mode}_{label}", v) == "AA_01", E("{mode}_{label}", v))
    check("tmpl middle empty", E("{label}-{mode}-{view}", v) == "AA_01-Front", E("{label}-{mode}-{view}", v))
    check("tmpl unknown kept", E("{label}_{foo}", v) == "AA_01_{foo}")
    check("tmpl prefix/number", E("{prefix}{number}", v) == "AA01")
    s.folder_template = "{mode}/../{label}"
    check("folder nest + no escape", mv.output_folder(s, dict(v, mode="clay")) == os.path.join("clay", "AA_01"), mv.output_folder(s, dict(v, mode="clay")))
    s.folder_template = "{label}_{product}"

    # ---- default naming unchanged from 1.5
    r = run(bpy.ops.mv.render_all)
    f = [x for x in files() if not x.startswith("manifest")]
    check("default names", "AA_01_Widget/AA_01_Widget_Front_clay.png" in f and len(f) == 9, f)

    # ---- flat custom naming
    reset()
    s.folder_template = ""
    s.file_template = "{number}-{product}-{view}"
    run(bpy.ops.mv.render_all)
    f = [x for x in files() if not x.startswith("manifest")]
    check("flat custom names", "01-Widget-Front.png" in f and "03-Knob-Right.png" in f and len(f) == 9, f)

    # ---- clash
    s.file_template = "{label}_{product}"
    r = run(bpy.ops.mv.render_all)
    check("clash cancelled", r == {'CANCELLED'})
    check("clash restored camera/exclusion", all(not mv.find_layer_coll(bpy.context.view_layer.layer_collection, pc.name).exclude for pc in mv.get_products()))
    s.file_template = mv.DEFAULT_FILE_TEMPLATE
    s.folder_template = mv.DEFAULT_FOLDER_TEMPLATE

    # ---- post-processing
    reset()
    s.post_enabled = True
    s.post_trim = True
    s.post_margin = 0.1
    s.post_square = True
    s.post_format = 'JPEG'
    s.post_bg_color = (1, 0, 0)
    s.post_extra_sizes = "32, 2048"
    run(bpy.ops.mv.render_all)
    p = files("processed")
    check("processed mirrors layout", "processed/AA_01_Widget/AA_01_Widget_Front_clay.jpg" in p, p)
    check("extra size file", "processed/AA_01_Widget/AA_01_Widget_Front_clay_32.jpg" in p, p)
    check("upscale size skipped->same size", "processed/AA_01_Widget/AA_01_Widget_Front_clay_2048.jpg" in p)
    main = px("processed/AA_01_Widget/AA_01_Widget_Front_clay.jpg")
    small = px("processed/AA_01_Widget/AA_01_Widget_Front_clay_32.jpg")
    big = px("processed/AA_01_Widget/AA_01_Widget_Front_clay_2048.jpg")
    check("square", main.shape[0] == main.shape[1], main.shape)
    check("trimmed smaller than render", main.shape[0] < 96, main.shape)
    check("thumb 32", max(small.shape[:2]) == 32, small.shape)
    check("no upscale", big.shape == main.shape, (big.shape, main.shape))
    corner = main[0, 0, :3]
    check("flattened on red", corner[0] > 0.9 and corner[1] < 0.15, corner)
    orig = px("AA_01_Widget/AA_01_Widget_Front_clay.png")
    check("original untouched", orig.shape[:2] == (64, 96) and orig[0, 0, 3] < 0.01, orig.shape)

    # trim unit
    a = np.zeros((50, 80, 4), np.float32); a[10:20, 30:60] = 1
    check("content_box", mv.content_box(a, mv.background_of(a)) == (30, 10, 60, 20))
    b = np.ones((50, 80, 4), np.float32); b[5:7, 3:9, :3] = 0
    check("content_box opaque bg", mv.content_box(b, mv.background_of(b)) == (3, 5, 9, 7))
    s.post_trim = s.post_square = False
    s.post_format = 'PNG'
    s.post_extra_sizes = ""

    # ---- contact sheet
    reset()
    s.post_enabled = False
    s.sheet_enabled = True
    s.sheet_cell_width = 128
    run(bpy.ops.mv.render_all)
    f = files()
    check("sheet files", all(f"{lbl}/{lbl}_Sheet_clay.png" in f for lbl in ("AA_01_Widget", "AA_02_Bracket", "AA_03_Knob")), f)
    sheet = px("AA_01_Widget/AA_01_Widget_Sheet_clay.png")
    gap = max(8, 128 // 24)
    check("sheet width", sheet.shape[1] == 2 * 128 + 3 * gap, sheet.shape)
    top = sheet[-20:, :, :3]
    check("sheet title drawn", top.min() < 0.5, float(top.min()))
    shutil.copy(os.path.join(out, "AA_01_Widget/AA_01_Widget_Sheet_clay.png"), KEEP + "_sheet.png")
    s.sheet_enabled = False

    # ---- turntable
    reset()
    s.turntable_enabled = True
    s.turntable_frames = 8
    s.turntable_gif = True
    s.turntable_gif_size = 80
    knob = root.children["Knob"].objects[0]
    before = knob.matrix_world.copy()
    r = run(bpy.ops.mv.render_all)
    f = files()
    tf = [x for x in f if "/turntable/" in x]
    check("turntable frames", len(tf) == 24, len(tf))
    check("mp4 written", "AA_01_Widget/AA_01_Widget_Turntable_clay.mp4" in f and os.path.getsize(os.path.join(out, "AA_01_Widget/AA_01_Widget_Turntable_clay.mp4")) > 1000, f)
    check("gif written", "AA_03_Knob/AA_03_Knob_Turntable_clay.gif" in f)
    check("product restored", all(abs(a - b) < 1e-6 for ra, rb in zip(knob.matrix_world, before) for a, b in zip(ra, rb)))
    check("turntable cam removed", bpy.data.objects.get(mv.TURNTABLE_CAM) is None)
    f1 = px("AA_03_Knob/turntable/AA_03_Knob_Turntable_clay_001.png")
    f3 = px("AA_03_Knob/turntable/AA_03_Knob_Turntable_clay_003.png")
    check("frames differ (spinning)", np.abs(f1 - f3).max() > 0.2)
    check("frame not cropped (transparent border)", f1[0, :, 3].max() < 0.01 and f1[-1, :, 3].max() < 0.01 and f1[:, 0, 3].max() < 0.01 and f1[:, -1, 3].max() < 0.01)
    shutil.copy(os.path.join(out, "AA_03_Knob/AA_03_Knob_Turntable_clay.gif"), KEEP + ".gif")
    shutil.copy(os.path.join(out, "AA_03_Knob/AA_03_Knob_Turntable_clay.mp4"), KEEP + ".mp4")

    # ---- manifest
    m = json.load(open(os.path.join(out, "manifest.json")))
    rows = m["images"]
    kinds = sorted({r["kind"] for r in rows})
    check("manifest kinds", kinds == ["render", "turntable"], kinds)
    check("manifest count", len(rows) == 9 + 6, len(rows))
    w = [r for r in rows if r["product"] == "Widget" and r["kind"] == "render"][0]
    check("manifest source", w["source_file"] == "C:/cad/widget.step" and w["source_size"] == [120.0, 40.0, 15.5], w)
    check("manifest dims", w["width"] == 96 and w["height"] == 64, w)
    mp = [r for r in rows if r["path"].endswith(".mp4")][0]
    check("manifest mp4 dims", mp["width"] == 96 and mp["height"] == 64, mp)
    check("manifest rel path", w["path"] == "AA_01_Widget/AA_01_Widget_Front_clay.png", w["path"])
    c = list(csv.DictReader(open(os.path.join(out, "manifest.csv"))))
    check("csv rows", len(c) == len(rows) and c[0].keys() >= {"label", "path", "source_size"}, len(c))
    check("csv size format", [r for r in c if r["product"] == "Widget"][0]["source_size"] == "120 x 40 x 15.5")

    # merge: render only Bracket (active) without turntable; others kept
    s.turntable_enabled = False
    s.active_product_index = 1
    run(bpy.ops.mv.render_all, only_active=True)
    rows2 = json.load(open(os.path.join(out, "manifest.json")))["images"]
    check("merge keeps others", any(r["product"] == "Widget" and r["kind"] == "turntable" for r in rows2), len(rows2))
    check("merge replaced bracket", not any(r["product"] == "Bracket" and r["kind"] == "turntable" for r in rows2))

    # ---- skip existing with post + sheet: nothing left to do
    reset()
    s.post_enabled = True
    s.sheet_enabled = True
    run(bpy.ops.mv.render_all)
    s.skip_existing = True
    stamp = {p: os.path.getmtime(os.path.join(out, p)) for p in files()}
    run(bpy.ops.mv.render_all)
    changed = [p for p in files() if p not in stamp or os.path.getmtime(os.path.join(out, p)) != stamp[p] and not p.startswith("manifest")]
    check("skip all with post+sheet", changed == [], changed)
    rows3 = json.load(open(os.path.join(out, "manifest.json")))["images"]
    check("manifest after skip complete", len(rows3) == 9 + 9 + 3, len(rows3))
    # delete a processed file -> post-only job, sheet rebuilt for that product
    os.remove(os.path.join(out, "processed/AA_02_Bracket/AA_02_Bracket_Top_clay.png"))
    run(bpy.ops.mv.render_all)
    changed = [p for p in files() if p not in stamp or os.path.getmtime(os.path.join(out, p)) != stamp[p]]
    changed = [p for p in changed if not p.startswith("manifest")]
    check("post-only resume", sorted(changed) == ["AA_02_Bracket/AA_02_Bracket_Sheet_clay.png", "processed/AA_02_Bracket/AA_02_Bracket_Top_clay.png"], changed)
    s.skip_existing = False

    # manifest none
    s.manifest_format = 'NONE'
    reset()
    run(bpy.ops.mv.render_all)
    check("manifest none", not any(x.startswith("manifest") for x in files()))

    # GIF LZW roundtrip using a minimal decoder
    def gif_decode_first(path):
        data = open(path, "rb").read()
        assert data[:6] == b"GIF89a"
        w, h = int.from_bytes(data[6:8], "little"), int.from_bytes(data[8:10], "little")
        pos = 13 + 768
        frames = 0
        first = None
        while data[pos] != 0x3B:
            if data[pos] == 0x21:
                pos += 2
                while data[pos]:
                    pos += data[pos] + 1
                pos += 1
            elif data[pos] == 0x2C:
                pos += 10
                mcs = data[pos]; pos += 1
                raw = bytearray()
                while data[pos]:
                    raw += data[pos + 1:pos + 1 + data[pos]]; pos += data[pos] + 1
                pos += 1
                frames += 1
                if first is None:
                    # LZW decode
                    clear, end = 1 << mcs, (1 << mcs) + 1
                    size = mcs + 1; bitpos = 0; table = None; prev = None; outp = bytearray()
                    bits = int.from_bytes(raw, "little"); nbits = len(raw) * 8
                    while bitpos + size <= nbits:
                        code = (bits >> bitpos) & ((1 << size) - 1); bitpos += size
                        if code == clear:
                            table = [bytes([i]) for i in range(clear)] + [b"", b""]; size = mcs + 1; prev = None; continue
                        if code == end: break
                        if prev is None:
                            entry = table[code]
                        else:
                            entry = table[code] if code < len(table) else table[prev] + table[prev][:1]
                            if len(table) < 4096:
                                table.append(table[prev] + entry[:1])
                        outp += entry; prev = code
                        if len(table) == (1 << size) and size < 12: size += 1
                    first = bytes(outp)
        return w, h, frames, first
    gw, gh, gframes, gfirst = gif_decode_first(KEEP + ".gif")
    check("gif frames", gframes == 8, gframes)
    check("gif decodes full frame", gfirst is not None and len(gfirst) == gw * gh, (len(gfirst or b""), gw * gh))
    # big random data roundtrip stresses table resets
    rnd = np.random.default_rng(1).integers(0, 256, 200000, dtype=np.uint8).tobytes()
    blocks = mv.gif_lzw(rnd)
    raw = bytearray(); i = 0
    while blocks[i]:
        raw += blocks[i + 1:i + 1 + blocks[i]]; i += blocks[i] + 1
    open(KEEP + "_lzw.bin", "wb").write(bytes(raw))
    # decode with the same decoder
    clear, end = 256, 257
    size = 9; bitpos = 0; table = None; prev = None; outp = bytearray()
    bits = int.from_bytes(raw, "little"); nbits = len(raw) * 8
    while bitpos + size <= nbits:
        code = (bits >> bitpos) & ((1 << size) - 1); bitpos += size
        if code == clear:
            table = [bytes([k]) for k in range(256)] + [b"", b""]; size = 9; prev = None; continue
        if code == end: break
        if prev is None: entry = table[code]
        else:
            entry = table[code] if code < len(table) else table[prev] + table[prev][:1]
            if len(table) < 4096: table.append(table[prev] + entry[:1])
        outp += entry; prev = code
        if len(table) == (1 << size) and size < 12: size += 1
    check("lzw roundtrip random 200k", bytes(outp) == rnd, (len(outp), len(rnd)))

    mv.unregister()
except Exception:
    traceback.print_exc()
    check("no exception", False, traceback.format_exc())

print("=" * 60)
for name, ok, detail in results:
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   -> {detail}"))
print("TOTAL", sum(ok for _, ok, _ in results), "/", len(results))
shutil.rmtree(out, ignore_errors=True)
