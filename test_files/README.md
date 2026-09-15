# Test files

Scratch folder for CAD files used to exercise the add-on by hand. **Everything in here is
gitignored except this README**, so you can drop real CAD parts in without them ending up in
the repo or a release.

Drop `.step` / `.stp` / `.stl` files straight in, or group them in subfolders. Subfolders
are ignored too.

## Using them

1. `3D Viewport → Sidebar (N) → MultiView → Import Products`
2. `+` on the file list, select the files from this folder
3. **Import CAD Files**

Each file becomes its own collection under `MV_Products`. With **Fit on Import** on (the
default) each one is scaled into a `Target Size` cube and centred on the world origin as it
lands.

Renders default to `//renders/`, which is gitignored separately, so they will not appear here.

## Worth having on hand

- a **single-solid** part (simplest path)
- a **multi-part assembly**, which is what catches origin and scale bugs, since the parts
  have to keep their positions relative to each other
- something **large**, a few hundred mm across, to check unit handling
- a **broken or truncated** file, to confirm one bad file is skipped with the real error
  rather than stopping the batch
- an **`.stl`**, which takes the direct route: no FreeCAD, no STEPper, no `(converting)` in
  the status bar, but the same product collection and fit as a STEP file
- a **`.stl` that is not really an STL** (rename any file), to confirm it is reported rather
  than landing as an empty product that renders as blank frames

If an import misbehaves, `Window → Toggle System Console` shows the per-file report.
