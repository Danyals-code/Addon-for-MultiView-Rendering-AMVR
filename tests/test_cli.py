"""The command line, driven the way a user or CI would: separate Blender
processes, job files, shards and a merge."""
import os
import sys
import json
import shutil
import subprocess
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as h  # noqa: E402

import bpy  # noqa: E402

check = h.check
CLI = os.path.join(h.REPO, "multiview_product_renderer", "cli.py")


def blender(*args, timeout=600):
    cmd = [bpy.app.binary_path, "-b", "--factory-startup", "--python", CLI, "--", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout + proc.stderr


def files_under(root):
    return sorted(os.path.relpath(os.path.join(d, f), root).replace("\\", "/")
                  for d, _, fs in os.walk(root) for f in fs)


def body():
    work = tempfile.mkdtemp(prefix="mv_cli_")
    try:
        inputs = os.path.join(work, "in")
        os.makedirs(inputs)
        for name, size in (("anvil", 40), ("bolt", 10), ("cog", 25)):
            h.fresh_scene()
            bpy.ops.mesh.primitive_cube_add(size=size)
            bpy.ops.wm.stl_export(filepath=os.path.join(inputs, name + ".stl"),
                                  export_selected_objects=True)
        settings = {"render_mode": "CLAY", "view_set": "MIN", "export_cameras": True,
                    "manifest_format": "JSON", "turntable_elevation": 30}
        job = {"inputs": ["in"], "output": "out", "settings": settings,
               "render": {"resolution": [48, 32]}}
        with open(os.path.join(work, "job.json"), "w") as f:
            json.dump(job, f)

        code, log = blender("--config", os.path.join(work, "job.json"))
        out = os.path.join(work, "out")
        made = files_under(out) if os.path.isdir(out) else []
        check("full job exits 0", code == 0, (code, log[-800:]))
        check("full job renders 3 products x 3 views",
              sum(f.endswith("_clay.png") for f in made) == 9, made)
        summary = next((json.loads(line.split(" ", 1)[1]) for line in log.splitlines()
                        if line.startswith("MULTIVIEW_SUMMARY ")), {})
        check("summary line", summary.get("images") == 9 and summary.get("finished"), summary)
        check("labels follow file order", {f.split("/")[0] for f in made if "/" in f}
              == {"AA_01_anvil", "AA_02_bolt", "AA_03_cog"}, made)

        # Two shards into one folder, then merge: same files, same labels.
        sharded = os.path.join(work, "sharded")
        codes = [blender("--config", os.path.join(work, "job.json"), "--output", sharded,
                         "--shard", f"{i}/2")[0] for i in range(2)]
        check("both shards exit 0", codes == [0, 0], codes)
        made2 = files_under(sharded)
        check("shards write the same images as one run",
              sorted(f for f in made2 if f.endswith(".png"))
              == sorted(f for f in made if f.endswith(".png")), made2)
        check("shards keep separate manifests",
              "manifest_shard00.json" in made2 and "manifest_shard01.json" in made2)
        code, log = blender("--merge", sharded)
        check("merge exits 0", code == 0, log[-400:])
        merged = json.load(open(os.path.join(sharded, "manifest.json")))["images"]
        single = json.load(open(os.path.join(out, "manifest.json")))["images"]
        check("merged manifest matches one run",
              sorted(r["path"] for r in merged) == sorted(r["path"] for r in single),
              (len(merged), len(single)))

        # TOML works too.
        toml = os.path.join(work, "job.toml")
        with open(toml, "w") as f:
            f.write('inputs = ["in/bolt.stl"]\noutput = "out_toml"\n[settings]\n'
                    'render_mode = "CLAY"\nview_set = "MIN"\n[render]\nresolution = [32, 32]\n')
        code, log = blender("--config", toml)
        check("toml job", code == 0 and os.path.isdir(os.path.join(work, "out_toml", "AA_01_bolt")),
              (code, log[-400:]))

        # Mistakes come back as exit 2 with a message, not a traceback.
        with open(os.path.join(work, "bad.json"), "w") as f:
            json.dump({"inputs": ["in"], "settings": {"view_sett": "MIN"}}, f)
        code, log = blender("--config", os.path.join(work, "bad.json"))
        check("unknown setting -> exit 2", code == 2 and "unknown setting 'view_sett'" in log,
              (code, log[-400:]))
        with open(os.path.join(work, "missing.json"), "w") as f:
            json.dump({"inputs": ["nowhere"]}, f)
        code, log = blender("--config", os.path.join(work, "missing.json"))
        check("missing input -> exit 2", code == 2 and "input not found" in log, (code, log[-300:]))

        code, log = blender("--config", os.path.join(work, "job.json"), "--output",
                            os.path.join(work, "checked"), "--check")
        check("--check runs pre-flight only", code == 0 and "pre-flight" in log
              and not os.path.isdir(os.path.join(work, "checked", "AA_01_anvil")), (code, log[-400:]))

        code, log = blender("--list-settings")
        check("--list-settings", code == 0 and "render_mode" in log and "degrees" in log)
    finally:
        shutil.rmtree(work, ignore_errors=True)


h.guard(body)
