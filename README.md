# MultiView Product Renderer

A Blender add-on for turning CAD products into consistent, batch-rendered image sets.

Import STEP, IGES and mesh files, standardize them at the world origin, build a rig of
orthographic and perspective cameras plus studio lighting, then render every product across
every view in one click, with predictable file names like `AA_01_Widget_Front_clay.png`.

- **Blender:** 4.0 and newer
- **Panel location:** `3D Viewport → Sidebar (N key) → MultiView`
- **Version:** 1.9.0

---

## Install

### Option A: download the release zip (recommended)

1. Go to the [**Releases**](../../releases/latest) page and download
   **`multiview_product_renderer.zip`**.
2. In Blender: `Edit → Preferences → Add-ons`.
   - Blender **4.2+**: `Install from Disk...` (in the top-right dropdown menu)
   - Blender **4.0 / 4.1**: `Install...`
3. Pick the zip you downloaded. **Do not unzip it first.**
4. Tick the checkbox next to **MultiView Product Renderer** to enable it.
5. Press `N` in the 3D viewport and open the **MultiView** tab.

### Option B: clone the repo

```bash
git clone https://github.com/Danyals-code/Addon-for-MultiView-Rendering-AMVR.git
```

Copy the `multiview_product_renderer` folder into your Blender add-ons directory:

| OS | Path |
| --- | --- |
| Windows | `%APPDATA%\Blender Foundation\Blender\4.x\scripts\addons\` |
| macOS | `~/Library/Application Support/Blender/4.x/scripts/addons/` |
| Linux | `~/.config/blender/4.x/scripts/addons/` |

Restart Blender and enable the add-on as in step 4 above.

---

## STEP / IGES import setup (optional)

You only need this if you want to import `.step` / `.stp` or `.iges` / `.igs` files
directly. If you already have meshes in your scene, skip it. The add-on works with any
geometry.

**Mesh files need none of this.** STL, OBJ, PLY, glTF/GLB, FBX and 3MF already hold a mesh,
so they are imported straight through Blender and never touch FreeCAD or STEPper, whatever
the STEP Import Mode is set to. From the moment one lands it is treated exactly like a
converted STEP file: same product collection, same Fit on Import, same standardizing, same
batch render and file naming.

| Format | Imported by | Notes |
| --- | --- | --- |
| STEP (`.step`, `.stp`) | FreeCAD or STEPper | Parts keep their names and colours (FreeCAD route) |
| IGES (`.iges`, `.igs`) | FreeCAD | |
| STL, PLY | Blender | Read as Z-up, which is what CAD writes |
| OBJ, glTF / GLB, FBX | Blender | Up axis converted the way the format defines it. Cameras and lights in the file are dropped |
| 3MF | MultiView's own reader | Meshes, components, build transforms and base-material colours. Blender has no 3MF importer |

Open `Edit → Preferences → Add-ons → MultiView Product Renderer` and expand the
preferences:

| Setting | What it does |
| --- | --- |
| **STEP Import Mode** | `Auto` tries the STEPper add-on first, then falls back to FreeCAD. Or force one. STEP only: IGES always uses FreeCAD, and mesh files ignore it. |
| **FreeCAD Executable** | Path to `freecadcmd.exe` (Windows) or `freecadcmd` (macOS/Linux). STEP and IGES. |
| **Tessellation Deflection** | FreeCAD mode only. Lower = finer mesh, bigger files. Default `0.1`. |

**FreeCAD route**: install [FreeCAD](https://www.freecad.org/) and point the preference at
its console binary, typically:

```
C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe
```

The add-on shells out to FreeCAD, tessellates each part into a mesh, writes temporary OBJs,
and imports those. Nothing is left behind in your FreeCAD install, and the scratch
directory is removed even if you cancel. FreeCAD is run with its standard input closed, so
a build that stops to ask a question fails immediately instead of stalling the import.
Any single conversion is given 15 minutes before it is stopped.

**Parts and colours.** Each part of a STEP assembly comes in as its own object, named the
way the CAD file names it (`Housing`, `Lid`, `Screw`...), all inside the one product
collection. Colours set in the CAD file become materials (`MV_Color_RRGGBB`), including
faces coloured differently from the rest of their part, and show in Full renders unless a
material preset replaces them. FreeCAD's console mode cannot read STEP colours itself, so
MultiView reads them from the file and passes them along. It understands the usual ways CAD
programs write colour; a file that colours parts some other way imports in grey, never
fails.

**STEPper route**: if you own the STEPper add-on, install and enable it; MultiView detects
and uses its import operator automatically.

---

## Workflow

The sidebar is laid out in the order you should use it.

### 1. Scene Setup

Pick a lighting preset, a background and a ground, then **Apply Scene Setup**. This builds
an `MV_Lighting` collection, an `MV_Stage` collection for the ground, and switches the scene
to the add-on's own `MV_World`.

Your existing world is left intact. It is only deselected, not edited, so an HDRI setup
you built yourself survives and can be picked again from World properties.

| Lighting preset | Look |
| --- | --- |
| **Studio Soft** | Large soft area lights, even fill. Default. |
| **Studio Hard** | Smaller lights, crisper shadows and highlights. |
| **Dramatic** | Strong key, deep falloff, minimal fill. |
| **High Key** | Bright, near-shadowless, white-on-white product look. |
| **No Lights (HDRI only)** | No lamps at all; the HDRI does the lighting. |

**Intensity** multiplies the preset's light energies. **Lighting Only** and **Background
Only** re-run either half on its own.

#### Lights Follow Camera

On by default. The rig is laid out for the Front view, and with this off the lights stay
where they are while the cameras go round, so Back is lit mostly by the rim light and Bottom
barely at all. With it on, the whole rig turns with each camera during a render, so every
view is lit the way Front is: key from the same side, fill from the other, rim behind. The
lights go back to their Front position when the batch finishes.

The rig hangs off an empty called `MV_LightRig` at the centre of the batch. A file whose
lighting was built before 1.7 has no rig yet: press **Lighting Only** once.

#### Your own lighting presets

Move the lights, change their colour or strength, or add your own lights to `MV_Lighting`,
then press **+** next to the preset list and give the setup a name. It is saved in
Blender's user presets folder (`scripts/presets/multiview_lighting/`), so it is available in
every file, and appears in the list after the built-in presets. **−** deletes the selected
saved preset; built-in ones cannot be deleted.

Presets are saved relative to the product: positions and sizes as multiples of its size,
laid out against the Front view. Loaded onto a product of a different size, or with a
different **Front Axis**, the rig scales and turns to match.

#### Background

- **Color**: a flat background in **Background Color**.
- **HDRI**: pick an `.hdr` or `.exr` environment. It lights the product and shows in its
  reflections. **Strength** and **Rotation** adjust it. With **Show HDRI** off (the default)
  the camera still sees the flat Background Color, which is usually what a product shot
  wants; tick it to see the environment itself.

**Transparent Background** renders alpha instead of either.

#### Ground

Something for the product to stand on, in Full renders only. Clay and the extra passes
are about the product's shape, so the ground is left out of them.

- **Shadow Catcher**: an invisible floor that only shows the product's shadow, on the
  background colour or on transparency. Cycles only; EEVEE renders it as a plain floor,
  and the panel warns.
- **Floor**: a visible floor in **Floor Color**. Lower **Roughness** makes it reflect the
  product.

The ground is moved under each product as it is rendered, so short and tall products all
stand on it. It is hidden for any view looking up from below it, so **Bottom** still shows
the product.

#### Materials

The **Materials** sub-panel replaces the products' materials in Full renders with one of:
Matte Plastic, Glossy Plastic, Rubber, Brushed Metal, Polished Metal or Glass, in a colour
you pick. **Keep Own** (the default) leaves materials alone.

Set it for the whole batch, or select a product in **Products to render** and give it its
own preset and colour. **Batch Default** follows the batch setting; **Keep Own** keeps that
product's materials even when the batch has a preset.

The products' own materials are never edited. The preset is applied by a temporary
Geometry Nodes modifier, `MV_Material`, added while the product renders and removed
afterwards, so it also works on STL imports, which arrive with no materials at all.

### 2. Import Products

Add files to the list with **+**, or a whole folder with the folder button, then click
**Import Files**. **Add Folder** picks up every supported file in the folder (tick **Include
Subfolders** in the file browser's sidebar to go deeper, on by default) and skips files that
are already in the list. Each file becomes its own collection under `MV_Products`. That
grouping is what the batch renderer iterates over. You can mix formats freely in one list;
each file is routed by its extension, and a file that fails does not stop the ones after it.

Import runs in the background: the status bar shows `MultiView: 3/12 housing.step
(converting)`, Blender stays responsive, and **Esc** cancels after the file in flight.
Files that fail are skipped rather than stopping the batch, and FreeCAD's own error
message is reported instead of a generic failure -- run `Window > Toggle System Console`
to see the full list.

Mesh files skip the conversion step entirely, so they land immediately rather than showing
`(converting)`. A file that Blender cannot read is reported and skipped rather than
becoming an empty product collection that would render as blank frames.

**Mesh Units** says what unit the numbers in STL, OBJ, PLY, glTF and FBX files are in
(millimetres by default, which is what CAD exports almost always use). It does not change
the geometry; it is only used to report each product's real size and to scale products
against each other with **Keep Proportions**. STEP and IGES come out of FreeCAD in
millimetres, and 3MF files state their own unit.

You can also click **Add Empty Product Collection** and drag existing meshes into it, which
is how you use MultiView with geometry that didn't come from a CAD file.

### 3. Standardize

Everything that makes products comparable to each other lives in this panel.

**Fit on Import** (on by default) does it automatically: as each file lands, the
product is uniformly scaled so its largest dimension equals **Target Size** (default
`1.0 m`, i.e. it fits inside a 1x1x1 m cube) and its bounding box is centred on the world
origin. Turn it off if you want to place and scale products yourself.

**Standardize Products** applies the same fit to everything already under `MV_Products`,
which is what you want after dragging in your own meshes or importing with the option off:

- **Recenter**: moves each product's bounding box centre onto the world origin. With
  **Rest on Floor**, the bottom of the box goes on the origin instead, so the product stands
  on the ground rather than straddling it.
- **Rescale**: uniformly scales each product, one of two ways:
  - **Fit Each** (default): every product's largest dimension becomes **Target Size**. This
    is what makes a tiny screw and a large housing frame read identically in the final
    images.
  - **Keep Proportions**: the biggest product in the batch becomes Target Size and the rest
    keep their real size relative to it, so a 10 mm screw next to a 400 mm housing renders
    at a fortieth of its size. Uses the real sizes recorded at import, converted through
    each file's units.

Each product's real size, measured before anything rescaled it, is shown under the
Standardize button for the active product (`120 x 40 x 15.5 mm`) and written to the
manifest. Products assembled by hand are measured the first time Standardize runs on them,
in metres.

- **Auto Smooth**: fixes the faceted look a tessellated CAD import arrives with. FreeCAD
  writes per-face normals that Blender keeps as custom split normals, and some Blender
  versions also mark most edges sharp on import; either one pins the flat shading no matter
  what you set. This clears both, then re-derives hard edges from the angle between faces
  (**Smooth Angle**, default 30 degrees -- raise it to keep fewer hard edges, lower it to
  keep more).

Both operate on the product as one rigid assembly, so multi-part STEP files keep their
parts in the right places relative to each other.

Sharpness is baked into the mesh rather than left to a *Smooth by Angle* modifier, so a
large batch costs nothing extra at render time. Running Standardize again is safe -- it is
idempotent.

Afterwards the transform is baked down: scale values read `1.0` and every object origin sits
on the world origin, so the product rotates about its own centre and the N panel is clean.
Geometry does not move during that step. Objects on multi-user or linked data cannot be
edited by Blender, so those keep their transform and are counted in the status message.

### 4. Cameras / Views

Choose a view set and click **Build Cameras**. Cameras land in `MV_Cameras`, named
`MV_Cam_<View>`.

| View set | Cameras |
| --- | --- |
| **All** | Front, Back, Top, Bottom, Right, Left + 3 perspectives (9) |
| **Orthographic** | Front, Back, Top, Bottom, Right, Left (6) |
| **Standard** | Front, Top, Right, Perspective (4) |
| **Minimal** | Front, Top, Right (3) |
| **Custom** | Whichever of the nine you tick |

Under the dropdown is a checkbox for each of the nine views. With a preset selected they are
greyed out and show what the preset includes. Pick **Custom** and they become editable,
starting from the preset you had selected, so going from Standard to "Standard plus Back"
takes one tick.

**Front Axis** tells the add-on which world axis points out of the front of your product.
CAD exports usually land on `+X` (the default); Blender's own convention is `-Y`. Getting
this right is what makes the "Front" render actually the front.

**Framing Padding** is the margin around the product in frame. `1.4` leaves 40% headroom
on the tightest axis; `1.0` fits the product exactly to the frame edge. Framing accounts for
your output resolution's aspect ratio, so a 16:9 or portrait render is not cropped.

All orthographic views share one framing, and all perspective views share another, so a
product reads at the same scale across the whole sheet rather than being re-fitted per view.

Need an angle that isn't in the presets? Add a **Custom View** with an X/Y/Z direction
vector and an ortho/perspective toggle, and it gets built alongside the rest. The checkbox at
the start of its row switches it off without deleting it.

#### Orient Products

**Front Axis** fixes the whole batch at once, which only helps when every product was
modelled the same way. In practice a few arrive facing the wrong way, and this is where you
turn them by hand.

**Isolate Active Product** (on by default) means you only ever see the one you are working
on. Rotating or stepping hides the others, so a product is never obscured by the rest of the
batch while you are trying to orient it. The checkbox applies the moment you tick it, and
unticking it brings everything back.

That is the same isolation **Render All** uses, so what you see is what that product's
render will contain. It is viewport state only: a batch render saves it, isolates each
product in turn, and puts it back afterwards, so leaving it switched on never changes what
gets rendered.

**Previous** and **Next** step through the batch one product at a time. The list wraps, so
you can keep pressing **Next** all the way round. **Show All** reveals every product and
switches the checkbox off, so the next rotation does not immediately hide them again.

**Left**, **Right**, **Up** and **Down** turn the product that is currently showing:

| Button | What it does |
| --- | --- |
| **Left** / **Right** | Spins the product about the vertical axis. This is the turntable move that swings a sideways product round to face front. |
| **Up** / **Down** | Tips the product about whatever axis is horizontal on your screen, for something lying on its back or standing on its nose. |

Up and Down follow the camera, so they mean the same thing whichever view you are looking
through. Rotation is about the product's own centre, so it never drifts out of frame, and a
multi-part assembly turns as one rigid piece. **Rotate Step** sets how far one press turns
it, 90 degrees by default, so four presses of the same button return to where you started.

**Auto Orient** turns the product for you, and **All** next to it does the whole batch:

| Method | What it does |
| --- | --- |
| **Lay Flat** (default) | Rests the product on its largest flat face, then turns it about the vertical so its footprint lines up with the axes and its longest side runs across the Front view. Right for boxes, housings, panels and most machined parts. |
| **Principal Axes** | Lines the product's longest spread up across the Front view, the next longest towards the Front camera, and the thinnest upright. Better for rounded or organic shapes with no flat face. It may leave a product upside down; Up/Down twice fixes that. |

**Reset** turns the product back to the way it faced when it was imported, undoing every
Auto Orient and arrow press since; **All** resets the whole batch. A product you built by
hand gets its starting orientation recorded the first time you turn it., and framing is measured across the whole batch.
With **Reframe Before Rendering** on (the default) you don't need to do anything about that:
Render All rebuilds the cameras before the first image. If you have switched it off, click
**Build Cameras** again once you are done orienting.

### 5. Batch Render

Set an **Output Directory**, choose a **Render Mode**, and hit **Render All**.

| Render mode | Output |
| --- | --- |
| **Full Render** | Uses your current engine (Cycles/EEVEE) and materials. |
| **Clay (Workbench)** | Fast single-colour clay pass with cavity shading. Default. |
| **Both** | Writes a `_render` and a `_clay` image per view. |

Every product is isolated in turn (all others excluded from the view layer), so nothing
bleeds between shots.

#### Extra passes

Tick any of these under **Extra passes** to write another image per view alongside the
render mode's. Each has its own `{mode}` in the file name, and gets its own contact sheet.

| Pass | `{mode}` | What it is |
| --- | --- | --- |
| **Line Art** | `lines` | A technical drawing: silhouettes and creases as lines. **Crease Angle** sets how sharp a fold has to be to get a line; smooth curves get only their outline. **Fill** is White (black on white), Clay (lines over the clay render) or None (lines on transparency). |
| **Mask** | `mask` | White product on black, antialiased, for use as a matte. |
| **AO** | `ao` | Ambient occlusion: a white product darkened in its creases and recesses, with lighting and materials taken out. **Distance** is how far occlusion reaches, as a fraction of the product's size. Needs the Cycles add-on (on by default). |

Line Art and Mask are fast Workbench renders whatever your engine is. Line Art finds its
lines from the geometry's normals rather than with Freestyle, so it needs nothing set up
and does not slow your Full render down.

#### Pre-flight check

The **Pre-flight** section under Batch Render looks for anything that would waste a render,
before any render time is spent. **Check Batch** runs it on demand; with **On Render** ticked
(the default) it also runs when you press Render All.

| Severity | Found | One-click fix |
| --- | --- | --- |
| Error | No products, or none ticked | |
| Error | Output format is a video rather than an image | |
| Error | Output path is a file, or the folder cannot be written | |
| Error | No views selected, or no cameras with Reframe off | Build cameras |
| Error | The file name template would give two images the same name | |
| Error | AO pass on, but the Cycles add-on is off | |
| Warning | Output folder is `//` relative but the `.blend` was never saved, so `//` points nowhere useful | Save the file |
| Warning | Output folder does not exist yet | Create it |
| Warning | Cameras are out of date (Reframe off): a product was turned, scaled or added, or the views, padding or resolution changed since Build Cameras | Rebuild cameras |
| Warning | An empty product. It is skipped when rendering rather than producing blank frames | |
| Warning | Faces with flipped normals, or a whole mesh inside out | Recalculate normals |
| Warning | Products are spread around the scene instead of centred, so each renders as a speck | Recenter |
| Warning | Objects outside `MV_Products` that would appear in every shot | Switch off their render visibility |
| Warning | Full render with no lights and no HDRI | Build lighting |
| Warning | Lights Follow Camera is on but the lighting predates the rig | Rebuild lighting |
| Warning | Shadow Catcher with an engine other than Cycles; HDRI file missing | |

Each issue is listed in the panel with the product it concerns, and a wrench button where
there is a fix. Errors stop Render All with a message saying why. Warnings bring up a
dialog listing them, with **Render Anyway** and **Cancel**. Called from a script, Render All
stops on errors the same way but never asks; warnings are left for the panel.

Normals are checked by looking at every edge: two faces sharing an edge should run along it
in opposite directions, and where they run the same way one of them is flipped. A closed
mesh whose faces all agree but enclose a negative volume is inside out as a whole. The fix
recalculates every face of the product to point outwards.

#### Progress and cancelling

The batch runs one image at a time with Blender still responsive. The status bar shows how
far it has got, which image is next, and roughly how long is left:

```
MultiView: 12/90  AA_03_Bracket Top  ~4m 10s left  -  Esc to cancel
```

**Esc** stops the batch after the image currently rendering. The time left is an average of
the images so far, so it settles after the first few. Each file is also printed to the
system console as it is written.

#### Choosing what to render

The **Products to render** list shows every product under `MV_Products` with the label its
files will get. Untick a product to leave it out. The two buttons beside the list tick or
untick all of them, and the main button changes to **Render N Ticked** when some are off.

**Render Active** renders only the product selected in the list, whether it is ticked or
not. Clicking a row also makes it the product **Orient Products** works on.

Leaving a product out never renumbers the rest. Labels come from each product's place in the
whole list, so `AA_03_Knob` is still `AA_03` when `AA_02` is unticked, and re-rendering one
product later writes into the same folder it used before.

#### Resuming with Skip Existing

With **Skip Existing** ticked, images that are already in the output folder are left alone
and only the missing ones are rendered. Use it to pick up a batch that crashed or that you
cancelled. The counter and the time left then cover only the remaining images. A zero-byte
file, which is what an interrupted write leaves behind, counts as missing.

Leave it off (the default) when you have changed a setting and want every image redone.
Skip Existing only checks whether a file is there, not what settings it was rendered with.

#### Reframing

**Reframe Before Rendering** (on by default) rebuilds the camera rig from the current view
selection, Front Axis, padding, output resolution and product positions before the first
image. A product you rotated, or a resolution you changed after building cameras, can't
leave a stale framing behind.

Framing always covers the whole batch, ticked or not, so a product rendered on its own comes
out at the same scale as the run it belongs to. Turn this off if you have moved or adjusted
the `MV_Cam_*` cameras by hand and want those used as they are.

**Only products are isolated.** Geometry that lives outside `MV_Products` is not a product,
so it is never hidden and turns up in every shot of every product. The usual offender is the
cube Blender starts a new file with: two metres across, sitting on the world origin exactly
where a fitted product lands, and quite capable of filling the frame and hiding the product
behind it -- which reads as a blank render with no obvious cause.

The panel warns before you spend the render time:

```
[!] 1 object(s) outside MV_Products
    appear in every render:
      Cube
    Delete them, move them into a
    product, or switch off their
    render visibility (camera icon).
```

Objects you have already switched off for rendering are not listed, so a deliberate backdrop
or staging rig does not keep setting the warning off.

**Render engine, sample count, resolution, and file format stay in Blender's own Output and
Render Properties.** MultiView only drives cameras, visibility, and file paths. It never
overwrites your render settings, and the clay pass restores your engine when it finishes.

#### File naming

Output is organised per product and named deterministically. The suffix comes from
the render mode: **Clay** writes `_clay`, **Full Render** writes no suffix, and **Both**
writes `_render` and `_clay` side by side. Clay is the default, so a first run looks
like this:

```
renders/
  AA_01_Widget/
    AA_01_Widget_Front_clay.png
    AA_01_Widget_Top_clay.png
    AA_01_Widget_Persp_FTR_clay.png
  AA_02_Bracket/
    AA_02_Bracket_Front_clay.png
    ...
```

The `AA_01` label is controlled by three fields:

- **Start Prefix**: the letter pair for the first product (`AA`, `BB`, ...). Only the
  first character is read, since the label just repeats it, so typing `AB` gives `AA`.
- **Start Number**: the number the batch starts at, so a second batch can continue from
  `AA_11` instead of restarting at `AA_01`.
- **Products per Letter**: how many products before the prefix rolls over to the next
  letter pair. After `ZZ` the label grows a character rather than wrapping, so it runs
  `AAA`, `BBB`, ... and every product keeps a folder of its own.

#### Naming templates

The layout above is the default. **Naming → Folder** and **Naming → File Name** let you
change it with tokens:

| Token | Example | Meaning |
| --- | --- | --- |
| `{label}` | `AA_01` | The product's label |
| `{prefix}` | `AA` | The letter part of the label |
| `{number}` | `01` | The number part of the label |
| `{product}` | `Widget` | The product collection's name |
| `{view}` | `Front` | The camera view, or `Sheet` / `Turntable` |
| `{mode}` | `clay` | `clay`, `render` (Both mode), or empty for Full Render |

The defaults are `{label}_{product}` for the folder and `{label}_{product}_{view}_{mode}` for
the file. A token that comes out empty takes one separator next to it along with it, so
`..._Front_{mode}` gives `..._Front` in Full Render mode rather than a trailing underscore.

- Use `/` in the folder template to nest folders, e.g. `{mode}/{label}_{product}` puts clay
  and full renders in separate trees. Leave it empty to put everything straight in the
  output directory.
- An unknown token is left in the name as typed, so a typo shows up in the preview under the
  fields (the first image of the batch, as it will be written) instead of silently vanishing.
- If the template would give two images the same name (no `{view}`, or no `{mode}` in Both
  mode), the render stops before it starts and says so.

#### Contact sheets

Tick **Contact Sheet** and each product also gets one image with all of its views in a grid,
the product's name across the top and each view's name underneath:
`AA_01_Widget/AA_01_Widget_Sheet_clay.png`. Both mode makes one sheet per mode.

- **Columns**: views per row. `0` picks a roughly square grid.
- **Cell Width**: how wide each view is drawn, in pixels.
- **Labels**, **Background**, **Text**: the captions and colours.

With Post-Processing on, the sheet is built from the processed copies, so trimmed images
make a tighter sheet. Labels need a Blender recent enough to draw text into an image (5.0
does); on an older one the sheet is drawn without captions.

#### Turntables

Tick **Turntable** and each product is also rendered spinning one full turn, then encoded:

- **Style**: Clay (fast, matches the clay stills) or Full Render.
- **Frames** and **FPS**: 36 frames at 24 fps is a 1.5 second loop.
- **Elevation**: how far above the product the camera looks down from.
- **MP4** (H.264) and/or **GIF**. The GIF is scaled so its longest edge is **GIF Size**,
  and uses one palette for the whole loop so the background doesn't flicker.

The product turns about its own centre under the fixed studio lights, as on a real
turntable. Every product is framed by one camera wide enough for the whole batch at every
angle, so turntables share a scale the same way the stills do. Frames are kept in a
`turntable` folder next to the stills (`AA_01_Widget/turntable/..._001.png`); the video and
GIF go next to the stills. Transparent renders are put on the scene's **Background Color**,
since neither format does transparency well. The product is put back exactly where it
was afterwards, even if you cancel half way through.

#### Post-processing

Tick **Post-Processing** to write a processed copy of every image. **The original renders
are never touched**: the copies go in a separate folder (**Folder**, default `processed`)
that mirrors the original layout, so you can change the settings and re-process without
re-rendering.

| Option | What it does |
| --- | --- |
| **Trim to Content** | Crops the empty background around the product, leaving **Margin** (a fraction of the product's size) around it. Each image then fills its own frame, so views no longer share one scale. |
| **Pad to Square** | Extends the shorter side with background so the image is square. |
| **Flatten** | Puts transparent renders on a solid colour. JPEG always does this. |
| **Format** | PNG, JPEG or WebP, with **Quality** for the lossy two. |
| **Max Size** | Shrinks the image so its longest edge is at most this many pixels. `0` keeps the size. |
| **Extra sizes** | Smaller copies too, e.g. `1024, 256` writes `..._Front_clay_1024.jpg` and `..._Front_clay_256.jpg`. Images are never scaled up. |

Trimming works on transparency when the render has it, and otherwise on whatever colour the
four corners share, so it works on a solid studio background too.

With **Skip Existing** on, an original that is already on disk is not re-rendered, but a
missing processed copy of it is still made. To re-process everything after changing the
settings, delete the `processed` folder and render again with Skip Existing on: only the
copies are rebuilt.

#### Manifest

**Manifest** (CSV + JSON by default) writes `manifest.csv` and/or `manifest.json` into the
output directory, listing every output with:

`label`, `product`, `kind` (render, processed, sheet, turntable), `view`, `mode`, `path`
(relative to the output directory), `width`, `height`, `source_file`, `source_size` and
`source_units`.

`source_file`, `source_size` and `source_units` are recorded when a file is imported:
`source_size` is the product's bounding box before Fit on Import rescaled it, in
`source_units` (`mm` for STEP and IGES, the file's own unit for 3MF, **Mesh Units** for
other meshes, empty after a STEPper import). Products assembled by hand have no source file
and are measured in metres the first time Standardize runs.

Rendering part of a batch updates the rows for those products and keeps the rest, so the
manifest always describes everything in the output directory. Rows for files that have
since been deleted are dropped.

---

## Collections the add-on creates

| Collection | Contents |
| --- | --- |
| `MV_Products` | One child collection per product. This is what gets iterated and isolated. |
| `MV_Cameras` | Generated cameras, named `MV_Cam_<View>`. |
| `MV_Lighting` | The lights from the active lighting preset, hung off the `MV_LightRig` empty. |
| `MV_Stage` | The ground plane, `MV_Ground`, when Ground is not None. |

It also creates one world datablock, `MV_World`, for the background, and a few materials
named `MV_...` for the ground, the AO pass and the material presets.

Rebuilding cameras or lighting clears and regenerates only that collection, discarding the
camera and light datablocks it made last time rather than leaving them behind. Your
products, and any other world in the file, are never touched.

---

## Troubleshooting

**"No cameras. Build cameras first."**: run *Build Cameras* in the Cameras / Views panel, or
switch **Reframe Before Rendering** back on.

**"No views selected."**: the view set is **Custom** with nothing ticked (and no enabled
custom views). Tick at least one view.

**"No products are ticked for rendering."**: tick products in the **Products to render**
list, or use **Render Active** for the selected one.

**A cancelled or crashed batch**: tick **Skip Existing** and render again. Only the images
that are missing get rendered.

**Renders come back blank, or with something unexpected in them**: check the warning above
**Render All**. Anything outside `MV_Products` is rendered along with every product, and a
large object near the origin can hide the product completely. Delete it, move it into a
product collection, or turn off its render visibility.

**"No product collections under 'MV_Products'."**: import a STEP or STL file, or add an empty
product collection and put your meshes inside it. Meshes sitting loose in the scene
collection are not seen as products.

**STEP import does nothing**: check that the FreeCAD path in add-on preferences points at
`freecadcmd`, not the GUI `freecad` binary. Open `Window → Toggle System Console` (Windows)
to see the subprocess output.

**Products are all different sizes in the renders**: run *Standardize Products* in the
Standardize panel with **Rescale** enabled.

**The "Front" view isn't the front**: change **Front Axis** in Cameras / Views and rebuild
the cameras. If only some products are wrong, Front Axis will not help, because it moves the whole
batch. Use *Orient Products* to turn the offenders individually, then rebuild.

**Only one product is visible in the viewport**: **Isolate Active Product** is on, which is
the default while orienting. Click **Show All** in Cameras / Views, or untick the box.
Renders are unaffected either way.

**Renders are cropped after rotating products**: rotating changes the bounding box the
framing was measured from. Switch on **Reframe Before Rendering**, or click *Build Cameras*
again.

**Imported STEP geometry is blocky**: lower **Tessellation Deflection** in preferences
(try `0.02`) and re-import.

---

## License

MIT. See [LICENSE](LICENSE).
