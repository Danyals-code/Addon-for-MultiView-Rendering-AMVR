"""Run MultiView Product Renderer without opening Blender's window.

    blender -b --factory-startup --python multiview_product_renderer/cli.py -- --config job.json
    blender -b --factory-startup --python multiview_product_renderer/cli.py -- --config job.json --shard 2/8
    blender -b --factory-startup --python multiview_product_renderer/cli.py -- --config job.json --check
    blender -b --factory-startup --python multiview_product_renderer/cli.py -- --merge renders/
    blender -b --factory-startup --python multiview_product_renderer/cli.py -- --list-settings

The add-on does not need to be installed: this file loads it from the folder
it sits in. A job is a JSON or TOML file; relative paths in it are relative
to the job file. See README "Command line" for every key.

Exit codes: 0 everything rendered, 1 rendered with some failures, 2 the job
could not run (bad config, nothing imported, pre-flight errors).
"""
import argparse
import csv
import glob
import json
import os
import sys
from types import SimpleNamespace

EXIT_OK, EXIT_PARTIAL, EXIT_FAILED = 0, 1, 2


class JobError(Exception):
    """A problem with the job itself, reported without a traceback."""


def say(text):
    print(f"[MultiView CLI] {text}", flush=True)


def load_addon():
    here = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(here)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    import bpy
    import multiview_product_renderer as mv
    if not hasattr(bpy.types.Scene, "mv_settings"):
        mv.register()
    return mv


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="multiview cli", description=__doc__.split("\n")[0])
    parser.add_argument("--config", help="job file (.json or .toml)")
    parser.add_argument("--output", help="override the job's output folder")
    parser.add_argument("--shard", help="render only part of the job: INDEX/COUNT, e.g. 0/4")
    parser.add_argument("--check", action="store_true",
                        help="import and set up, run the pre-flight check, render nothing")
    parser.add_argument("--merge", metavar="DIR",
                        help="combine the manifests, COCO files and BOP model info "
                             "written by shards in DIR")
    parser.add_argument("--list-settings", action="store_true",
                        help="print every setting a job's \"settings\" table accepts")
    return parser.parse_args(argv)


def read_job(path):
    with open(path, "rb") as f:
        data = f.read()
    if path.lower().endswith(".toml"):
        import tomllib
        return tomllib.loads(data.decode("utf-8"))
    return json.loads(data.decode("utf-8"))


def resolve(base, path):
    path = os.path.expanduser(str(path))
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(base, path))


def collect_inputs(mv, entries, base, recursive):
    """Every supported file the job names, folders expanded, in a fixed order
    so every shard agrees on which file is which."""
    found = {}
    for entry in entries:
        path = resolve(base, entry)
        if os.path.isdir(path):
            for folder, dirs, files in os.walk(path):
                dirs.sort()
                for name in sorted(files):
                    if mv.file_ext(name) in mv.SUPPORTED_EXTENSIONS:
                        full = os.path.join(folder, name)
                        found.setdefault(os.path.normcase(full), full)
                if not recursive:
                    break
        elif os.path.isfile(path):
            found.setdefault(os.path.normcase(path), path)
        else:
            raise JobError(f"input not found: {path}")
    return [found[k] for k in sorted(found)]


def apply_settings(owner, values, where):
    """Set RNA properties by name, with the errors a job author can act on.
    Angles are given in degrees."""
    import math
    props = owner.bl_rna.properties
    for key, value in values.items():
        prop = props.get(key)
        if prop is None or key == "rna_type" or prop.type in {'COLLECTION', 'POINTER'}:
            raise JobError(f"{where}: unknown setting '{key}' (try --list-settings)")
        if prop.subtype == 'ANGLE' and isinstance(value, (int, float)):
            value = math.radians(value)
        try:
            setattr(owner, key, value)
        except (TypeError, ValueError, AttributeError) as exc:
            raise JobError(f"{where}.{key}: {exc}") from exc


def apply_render(scene, values):
    r = scene.render
    simple = {"engine": (r, "engine"), "percentage": (r, "resolution_percentage"),
              "file_format": (r.image_settings, "file_format")}
    for key, value in values.items():
        if key == "resolution":
            r.resolution_x, r.resolution_y = int(value[0]), int(value[1])
        elif key == "samples":
            if r.engine == 'CYCLES':
                scene.cycles.samples = int(value)
            else:
                scene.eevee.taa_render_samples = int(value)
        elif key == "device":
            scene.cycles.device = value
        elif key in simple:
            owner, attr = simple[key]
            try:
                setattr(owner, attr, value)
            except (TypeError, ValueError) as exc:
                raise JobError(f"render.{key}: {exc}") from exc
        else:
            raise JobError(f"render: unknown key '{key}' "
                           "(engine, samples, device, resolution, percentage, file_format)")


def list_settings(mv):
    import bpy
    for prop in mv.MV_Settings.bl_rna.properties:
        if prop.identifier == "rna_type" or prop.type in {'COLLECTION', 'POINTER'} \
                or prop.is_hidden:
            continue
        kind = prop.type.lower()
        if prop.type == 'ENUM':
            items = [i.identifier for i in prop.enum_items] or ["(dynamic)"]
            kind = "one of " + ", ".join(items)
        elif getattr(prop, "array_length", 0):
            kind += f"[{prop.array_length}]"
        if prop.subtype == 'ANGLE':
            kind += ", degrees"
        print(f"{prop.identifier:24} {kind}\n{'':24} {prop.description}")


def run_job(mv, args):
    import bpy
    if not args.config:
        raise JobError("--config is required (or --merge / --list-settings)")
    job_path = os.path.abspath(args.config)
    job = read_job(job_path)
    base = os.path.dirname(job_path)
    known = {"blend", "inputs", "recursive", "output", "freecad", "step_import_mode",
             "deflection", "standardize", "auto_orient", "scene_setup", "settings",
             "render", "save_blend"}
    unknown = set(job) - known
    if unknown:
        raise JobError(f"unknown job keys: {', '.join(sorted(unknown))}")

    if job.get("blend"):
        bpy.ops.wm.open_mainfile(filepath=resolve(base, job["blend"]))
        mv = load_addon()
    context = bpy.context
    scene = context.scene
    s = scene.mv_settings

    prefs = mv.addon_prefs(context)
    mv.PREFS_OVERRIDE = SimpleNamespace(
        step_import_mode=job.get("step_import_mode", prefs.step_import_mode),
        freecad_path=resolve(base, job["freecad"]) if job.get("freecad") else prefs.freecad_path,
        tessellation_deflection=float(job.get("deflection", prefs.tessellation_deflection)))

    apply_render(scene, job.get("render", {}))
    apply_settings(s, job.get("settings", {}), "settings")
    output = args.output or job.get("output")
    if output:
        s.render_output_dir = resolve(os.getcwd() if args.output else base, output) + os.sep

    index, count = 0, 1
    if args.shard:
        try:
            index, count = (int(v) for v in args.shard.split("/"))
            assert count >= 1 and 0 <= index < count
        except (ValueError, AssertionError):
            raise JobError(f"--shard wants INDEX/COUNT with 0 <= INDEX < COUNT, got {args.shard}")
        s.shard_suffix = f"_shard{index:02d}" if count > 1 else ""

    files = collect_inputs(mv, job.get("inputs", []), base, job.get("recursive", True))
    if files:
        mine = files[index::count]
        position = {os.path.normcase(os.path.abspath(f)): i for i, f in enumerate(files)}
        say(f"importing {len(mine)} of {len(files)} file(s)")
        s.step_files.clear()
        for path in mine:
            s.step_files.add().path = path
        if mine:
            try:
                bpy.ops.mv.import_all_steps()
            except RuntimeError as exc:
                raise JobError(f"import: {exc}") from exc
        # Labels count through the whole job, not this shard, so shards never
        # write the same AA_01.
        for pc in mv.get_products():
            key = os.path.normcase(os.path.abspath(bpy.path.abspath(pc.mv_source or "")))
            if key in position:
                pc.mv_label_index = position[key]
    elif count > 1:
        # Shard the products already in the .blend instead.
        for i, pc in enumerate(mv.get_products()):
            pc.mv_label_index = i
            pc.mv_render = pc.mv_render and i % count == index
    if not mv.get_products():
        raise JobError("no products to render")

    if job.get("standardize"):
        bpy.ops.mv.standardize()
    if job.get("auto_orient"):
        method = job["auto_orient"]
        if isinstance(method, str):
            s.orient_method = method.upper()
        bpy.ops.mv.auto_orient(all_products=True)
    if job.get("scene_setup", True):
        bpy.ops.mv.apply_scene_setup()

    issues = mv.preflight(context)
    for issue in issues:
        where = f"{issue['product']}: " if issue["product"] else ""
        say(f"pre-flight {issue['severity'].lower()}: {where}{issue['message']}")
    errors = [i for i in issues if i["severity"] == 'ERROR']
    if args.check:
        say("pre-flight: " + ("all clear" if not issues else
                              f"{len(errors)} error(s), {len(issues) - len(errors)} warning(s)"))
        return EXIT_FAILED if errors else EXIT_OK
    if errors:
        raise JobError("pre-flight errors, nothing rendered")

    mv.LAST_RENDER.clear()
    try:
        bpy.ops.mv.render_all(skip_preflight=True)
    except RuntimeError as exc:
        say(f"render: {exc}")
    summary = dict(mv.LAST_RENDER)
    print("MULTIVIEW_SUMMARY " + json.dumps(summary), flush=True)
    if job.get("save_blend"):
        bpy.ops.wm.save_as_mainfile(filepath=resolve(base, job["save_blend"]), copy=True)
    if not summary.get("finished") or summary.get("aborted"):
        return EXIT_FAILED
    return EXIT_PARTIAL if summary.get("failures") else EXIT_OK


def merge(mv, folder):
    """Fold every shard's lists into the single files a whole run writes."""
    folder = os.path.abspath(folder)
    merged = []

    shards = sorted(glob.glob(os.path.join(folder, "manifest_shard*.json")))
    if shards:
        rows = []
        for path in shards:
            with open(path, encoding="utf-8") as f:
                rows.extend(json.load(f).get("images", []))
        rows.sort(key=lambda r: (str(r.get("label")), str(r.get("kind")), str(r.get("path"))))
        with open(os.path.join(folder, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"images": rows}, f, indent=2)
        with open(os.path.join(folder, "manifest.csv"), "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=mv.MANIFEST_FIELDS, extrasaction='ignore')
            writer.writeheader()
            for row in rows:
                size = row.get("source_size")
                if isinstance(size, list):
                    row = dict(row, source_size=" x ".join(f"{v:g}" for v in size))
                writer.writerow(row)
        merged.append(f"manifest ({len(shards)} shards, {len(rows)} rows)")

    shards = sorted(glob.glob(os.path.join(folder, "coco_shard*.json")))
    if shards:
        images, annotations, categories = [], [], {}
        for path in shards:
            with open(path, encoding="utf-8") as f:
                part = json.load(f)
            remap = {}
            for image in part.get("images", []):
                remap[image["id"]] = len(images) + 1
                images.append(dict(image, id=remap[image["id"]]))
            for ann in part.get("annotations", []):
                annotations.append(dict(ann, id=len(annotations) + 1,
                                        image_id=remap[ann["image_id"]]))
            for cat in part.get("categories", []):
                categories.setdefault(cat["id"], cat)
        with open(os.path.join(folder, "coco.json"), "w", encoding="utf-8") as f:
            json.dump({"images": images, "annotations": annotations,
                       "categories": sorted(categories.values(), key=lambda c: c["id"])},
                      f, indent=2)
        merged.append(f"COCO ({len(images)} images, {len(annotations)} instances)")

    models = os.path.join(folder, "bop", "models")
    shards = sorted(glob.glob(os.path.join(models, "models_info_shard*.json")))
    if shards:
        info = {}
        for path in shards:
            with open(path, encoding="utf-8") as f:
                info.update(json.load(f))
        with open(os.path.join(models, "models_info.json"), "w", encoding="utf-8") as f:
            json.dump(dict(sorted(info.items(), key=lambda kv: int(kv[0]))), f, indent=2)
        merged.append(f"BOP models_info ({len(info)} objects)")

    if not merged:
        raise JobError(f"no shard files in {folder}")
    for line in merged:
        say(f"merged {line}")
    return EXIT_OK


def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parse_args(argv)
    mv = load_addon()
    try:
        if args.list_settings:
            list_settings(mv)
            return EXIT_OK
        if args.merge:
            return merge(mv, args.merge)
        return run_job(mv, args)
    except JobError as exc:
        say(f"error: {exc}")
        return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
