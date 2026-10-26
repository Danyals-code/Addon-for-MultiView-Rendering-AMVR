"""Run every tests/test_*.py in its own background Blender and summarize.

    python tests/run_tests.py                      # finds Blender itself
    python tests/run_tests.py --blender /path/to/blender
    python tests/run_tests.py -k cli -k annotations

Blender is looked for in --blender, then $BLENDER, then PATH, then the usual
Windows install folder. FreeCAD is optional: set $FREECAD_CMD or put
freecadcmd on PATH to include the STEP and IGES checks.

Exit code 0 when every check in every file passed.
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOTAL = re.compile(r"^TOTAL (\d+) / (\d+)", re.M)


def find_blender(given):
    candidates = [given, os.environ.get("BLENDER"), shutil.which("blender")]
    candidates += sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe"),
                         reverse=True)
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    sys.exit("Blender not found: pass --blender or set BLENDER")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--blender")
    parser.add_argument("-k", action="append", default=[],
                        help="only run test files whose name contains this")
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    blender = find_blender(args.blender)
    files = sorted(glob.glob(os.path.join(HERE, "test_*.py")))
    if args.k:
        files = [f for f in files if any(k in os.path.basename(f) for k in args.k)]
    print(f"Blender: {blender}")

    failed = []
    for path in files:
        name = os.path.basename(path)
        started = time.monotonic()
        try:
            proc = subprocess.run([blender, "-b", "--factory-startup", "--python", path],
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=args.timeout)
            output = proc.stdout + proc.stderr
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or "") + f"\nTIMED OUT after {args.timeout}s"
            if isinstance(output, bytes):
                output = output.decode("utf-8", "replace")
        took = time.monotonic() - started
        match = TOTAL.search(output)
        fails = [line for line in output.splitlines() if line.startswith("FAIL ")]
        ok = bool(match) and match.group(1) == match.group(2) and not fails
        summary = f"{match.group(1)}/{match.group(2)}" if match else "no result"
        print(f"{'ok  ' if ok else 'FAIL'}  {name:28} {summary:>9}  {took:6.1f}s")
        if not ok:
            failed.append(name)
            for line in fails or output.splitlines()[-40:]:
                print("      " + line)
    print(f"\n{len(files) - len(failed)} of {len(files)} test files passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
