"""Shared plumbing for the tests, which run inside Blender:

    blender -b --factory-startup --python tests/test_something.py

Each test records named checks and ends with finish(), which prints one line
per check and a TOTAL line that tests/run_tests.py reads.
"""
import os
import sys
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO, "tests", "fixtures")
if REPO not in sys.path:
    sys.path.insert(0, REPO)

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def run(op, **kw):
    """Call an operator; an ERROR report raises in Blender, so turn it back
    into the CANCELLED the operator returned."""
    try:
        return op(**kw)
    except RuntimeError as exc:
        print("REPORTED:", exc)
        return {'CANCELLED'}


def guard(body):
    try:
        body()
    except Exception:
        traceback.print_exc()
        check("no exception", False, traceback.format_exc())
    finish()


def finish():
    print("=" * 60)
    for name, ok, detail in results:
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   -> {detail}"))
    print("TOTAL", sum(ok for _, ok, _ in results), "/", len(results))


def fresh_scene():
    import bpy
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)


def add_product(name, *makers):
    """A product collection holding one object per maker, each made by a
    bpy.ops primitive call and linked only into the product."""
    import bpy
    import multiview_product_renderer as mv
    coll = bpy.data.collections.new(name)
    mv.get_products_root().children.link(coll)
    objs = []
    for make in makers:
        make()
        obj = bpy.context.active_object
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        coll.objects.link(obj)
        objs.append(obj)
    return coll, objs
