# MultiView Product Renderer

A Blender add-on for turning CAD products into consistent, batch-rendered image sets.

Import STEP, IGES and mesh files, standardize them at the world origin, build a rig of
orthographic and perspective cameras plus studio lighting, then render every product across
every view in one click, with predictable file names like `AA_01_Widget_Front_clay.png`.

- **Blender:** 4.0 and newer
- **Panel location:** `3D Viewport → Sidebar (N key) → MultiView`
- **Version:** 1.12.0
- **Cite:** see [`CITATION.cff`](CITATION.cff)

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

#### Material Pool

The **Material Pool** sub-panel turns a folder of PBR texture sets into materials for
your products. Point **Texture Folder** at a folder holding one sub-folder per material, as
downloaded from [ambientCG](https://ambientcg.com) or [Poly Haven](https://polyhaven.com),
and click the refresh button. Every folder with a colour map becomes a pool material:

```
textures/
  Bricks_A/      Bricks_A_1K-PNG_Color.png, _Roughness, _NormalGL, _Displacement
  oak_veneer/    oak_veneer_diff_1k.png, _rough_1k, _arm_1k, _nor_gl_1k
  Metal_Plate/   Metal_Plate_Color.jpg, Metal_Plate_Metalness.png
```

Maps are recognised by their names:
- colour: `Color`, `BaseColor`, `Albedo`, `Diffuse`, `diff`
- roughness: `Roughness`, `rough`
- metallic: `Metalness`, `Metallic`, `metal`
- packed AO/rough/metal: `arm`
- height: `Displacement`, `Height`, `disp`, `bump`
- opacity: `Opacity`, `Alpha`

A folder holding a single image uses it as the colour map, unless its name ends in a data
map's word (`_rough`, `_Metalness`, ...). A material is named after its folder. A folder
called `textures`, `maps` or `2k` takes the name of the one above it, since Poly Haven
downloads keep their maps in `<asset>/textures`. Two folders with the same name are told
apart by their path (`wood_Oak`, `metal_Oak`). A material keeps its name when you scan
again, so a library that later gains a second `Oak` names only the new one by its path.

The list shows the maps found for each material as letters (**C** colour, **R** roughness,
**M** metallic, **A** packed, **H** height, **N** normal, **O** opacity). Untick a material
to leave it out.

The list keeps where each texture file is. If the files move (a moved library, or the
`.blend` opened on another machine), the folder is scanned again before rendering. If the
textures a material uses still cannot be found, pre-flight stops the batch.

CAD files have no UV maps, so the textures are box projected in each part's own
coordinates. They stay put when the product turns and need no unwrapping. **Texture Size**
is how much of the real part one repeat of a texture covers, in millimetres. A 100 mm wood
texture looks the same size on a 30 mm knob and a 2 m cabinet, whatever scale Fit on Import
gave them. A product built by hand and never standardized is taken to be in metres.

Normal maps are listed but not used, because they need the UVs these meshes do not have.
Opacity maps are listed but not used either. Masks, part IDs and COCO/BOP annotations are
made once per view, so a material that cut holes in the product would leave them wrong for
that image.

**Product variants.** Set **Variants** above 0 and every Full render is made that many
times per view, each with a different draw from the pool. With **Per Part** on, every part
of the product draws its own material; off, the whole product shares one. A product set to
**Keep Own** in **Products to render** is left out and renders once, in its own materials.

The files get a `_v01`, `_v02`, ... suffix (or use `{variant}` in the naming templates), and
each variant gets its own contact sheet. Clay renders, line art, masks, depth, normals and
part IDs do not depend on the material, so they are rendered once per view. The manifest's
`variant` and `materials` columns record what each image wears, for example
`Block=Bricks_A; Peg=oak_veneer`.

Draws come from the **Seed**, the product's label, the variant number and the part, so
re-running gives the same variants. Adding variants, products or parts never changes the
other draws. Adding or unticking a pool material changes only the draws it wins or held.
The pool's contents are recorded in the manifest's provenance block.

**Material patches.** **Render Patches** writes one image per ticked material into
`materials/` in the output folder. It shows a flat swatch, one repeat seen straight on, next
to a ball under studio lights, with the material's name above. Tick **With Render All** to
make them as part of every batch, listed in the manifest. In a sharded command-line run the
first shard makes them, and rendering just the active product skips them. Patches render in
a scene of their own with the scene's colour management, and the pool materials are deleted
again after each run, so your scene is untouched. They use Cycles when your engine is
Workbench, which cannot show textures.

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

#### Published protocols

**Protocol** replaces the View Set with the camera rig of a published dataset or method, so
a render set can match what a benchmark or model expects:

| Protocol | Views | Field of view | Distance | Source |
| --- | --- | --- | --- | --- |
| **MVCNN, 12 views** | 12 around the product, 30 degrees apart, 30 degrees up | MultiView's | Shared framing | Su et al., ICCV 2015 |
| **SyncDreamer, 16 views** | 16 around, 22.5 degrees apart, 30 degrees up | MultiView's | Shared framing | Liu et al., ICLR 2024 |
| **Zero123++ v1.2, 6 views** | Azimuths 30, 90, ..., 330; elevations alternating 20 and -10 | 30 degrees | Shared framing | Shi et al., v1.2 README |
| **MVDream, 4 views** | Front, right, back, left at 15 degrees up | 37.5 degrees | Shared framing | Shi et al., ICLR 2024 (middle of its random ranges) |
| **Zero-1-to-3, 12 random views** | Uniform on the sphere, seeded | 49.1 degrees | 1.5-2.2 object sizes, seeded | Liu et al., ICCV 2023 |
| **TRELLIS, 150 views** | Hammersley sequence on the sphere, seeded offset | 40 degrees | 2 object sizes | Xiang et al., CVPR 2025 |
| **Catalogue, 15 degree plunge** | Front at 0 and 15 degrees; front-right, right, back, left, front-left at 15 | MultiView's | Shared framing | After the GS1 Product Image Specification's preferred plunge (names are MultiView's, not GS1 codes) |

Azimuth 0 is the Front view, so protocols follow **Front Axis** like the built-in views.
Distances given in object sizes assume the product is normalized into a unit cube, as these
works do, and are multiplied by **Target Size**: with **Fit Each** and a Target Size of
`1.0` they are the published numbers. Random protocols take a **Seed**, so the same rig can be
built again exactly. MVDream samples its elevation and field of view at random; the preset
fixes them at the middle of its ranges, and the paper should say so if it matters.

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
| `{variant}` | `v01` | The Material Pool variant, empty for everything rendered once |

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
- With Material Pool variants on, a file name template without `{variant}` gets `_{variant}`
  added at the end, unless the folder template has `{variant}`, e.g.
  `{label}_{product}/{variant}`, which gives each variant a folder of its own.

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

`label`, `product`, `kind` (render, processed, sheet, turntable, patch, ...), `view`, `mode`,
`path` (relative to the output directory), `width`, `height`, `source_file`, `source_size`,
`source_units`, `source_sha256`, `variant` and `materials` (see Material Pool).

`source_file`, `source_size` and `source_units` are recorded when a file is imported:
`source_size` is the product's bounding box before Fit on Import rescaled it, in
`source_units` (`mm` for STEP and IGES, the file's own unit for 3MF, **Mesh Units** for
other meshes, empty after a STEPper import). Products assembled by hand have no source file
and are measured in metres the first time Standardize runs.

Rendering part of a batch updates the rows for those products and keeps the rest, so the
manifest always describes everything in the output directory. Rows for files that have
since been deleted are dropped.

Every row also carries `source_sha256`, the SHA-256 hash of the file it was rendered from.
`manifest.json` opens with a `provenance` block holding enough to make the output again:
- MultiView's version, repository and citation
- the Blender version and the `.blend` file
- render engine, samples, resolution, file format and view transform
- start and finish times
- a snapshot of every setting in the panels, including protocol and randomization seeds

**Croissant** (in the Manifest section) also writes `croissant.json`: an
[MLCommons Croissant 1.0](https://docs.mlcommons.org/croissant/docs/croissant-spec.html)
description of the output as a dataset, which the NeurIPS datasets track asks for.
- The manifest CSV is its record set, one field per column, with its checksum.
- Each file type in the output (PNG, EXR, SVG, ...) is a file set.
- Name, description, licence, URL and citation come from the fields under the checkbox.
  Without a citation, the dataset cites MultiView itself.
- The Responsible AI fields are filled with what the tool knows for certain: synthetic
  renders of the listed files, no personal data. Intended use and limitations are left for
  you to add.

Croissant always writes the CSV manifest, whatever **Write** is set to. After a sharded
command-line run, `--merge` writes `croissant.json` for the merged whole.

---

#### Annotations for research

The **Annotations** section under Batch Render turns a render into a dataset. Everything
here is computed from the same fixed camera rig as the images, so it lines up with them to
the pixel. The test suite checks the camera numbers against Blender's own projection and the
depth against ray casts.

| Setting | Writes | Notes |
| --- | --- | --- |
| **Cameras** (on by default) | `AA_01_Widget_cameras.json`, `AA_01_Widget_transforms.json`, and `..._Turntable_..._transforms.json` | See below |
| **Depth** | `..._Front_depth.exr` | 32-bit EXR, distance along the view axis in scene units, 0 and alpha 0 off the product |
| **Normals** | `..._Front_normal.exr` | 32-bit EXR, camera space, OpenGL axes (+X right, +Y up, +Z towards the camera), values -1..1 |
| **Part IDs** | `..._Front_parts.png` | 16-bit greyscale PNG: 0 is background, *n* is the *n*-th part in `cameras.json`'s `parts` list. Parts are the product's objects, so a STEP assembly's parts keep the names its CAD file gave them |
| **COCO** | `coco.json` | One instance mask (uncompressed RLE) per visible part per image, with `part_id` and `part_name`. Categories are products. Turns on Part IDs |
| **BOP** | `bop/` | A [BOP](https://github.com/thodan/bop_toolkit/blob/master/docs/bop_datasets_format.md) dataset from the perspective views: `train_pbr/<scene>/rgb`, `depth` (uint16, mm), `mask`, `mask_visib`, `scene_camera.json`, `scene_gt.json`, `scene_gt_info.json`, plus `models/obj_*.ply` and `models_info.json`. Turns on Depth |

Depth, Normals and Part IDs are each one extra Cycles render per view: one sample, no
antialiasing filter, every surface replaced by an emitter that outputs the number itself.
Each pixel therefore belongs to exactly one surface. There is no blending of a part's ID with
the background, or of a foreground depth with what is behind it. They need the Cycles add-on
(on by default) whatever engine the Full render uses. They are never post-processed or put
on a contact sheet.

**`cameras.json`** describes every view of the product:

- `c2w_opengl`: camera-to-world matrix, Blender/OpenGL axes (looking down -Z, +Y up).
- `w2c_opencv`: world-to-camera matrix, OpenCV axes (looking down +Z, +Y down), as COLMAP
  and BOP use.
- `K` for perspective views. Orthographic views get `pixel_size` and `principal_point`
  instead, since no K describes them.
- `width`, `height`, `clip`, and the relative paths of every image of that view.
- `model_to_world`: the 4x4 matrix from the product's **source file coordinates** (in
  `source_units`) to the scene. MultiView records every move it makes to a product (fitting,
  recentring, turning, Auto Orient), so a pixel in any render can be traced back to a point
  in the original CAD file. Moves you make by hand in the viewport are not seen.

**`transforms.json`** is in the nerfstudio/Instant-NGP format, for NeRF and Gaussian
splatting tools. It lists the perspective views only, with per-frame intrinsics and
`mask_path` when the Mask pass is on. A turntable gets its own `transforms.json`: the
product turns and the camera stays still, so each frame is given the camera that would
circle a still product. That is what those tools expect.

BOP wants rigid poses in millimetres of the model, although the scene was scaled to fit.
The scale is taken back out of the camera translation, the model is exported in its own
source units converted to mm, and depth is written in the same mm, with a `depth_scale` per
image so large parts still fit in 16 bits. Only perspective views go into BOP, because the
format has no orthographic camera.

#### Engineering drawings

Tick **Drawings** for vector three-view drawings of each product: Front, Top and Right as
separate SVGs (`AA_01_Widget_Front_drawing.svg`, ...), and all three on one sheet
(`AA_01_Widget_Drawing.svg`).

- **True scale.** One SVG unit is one millimetre of the original part: a 120 mm housing
  is drawn 120 mm wide at 1:1, whatever Target Size it was rendered at. MultiView takes back
  out every scale it applied.
- **Hidden lines dashed.** Lines are the mesh's feature edges, found geometrically: creases
  sharper than **Crease Angle**, silhouettes and open boundaries. Each is then tested
  against a depth image of the same view, along its whole length, so a line that passes
  behind something turns dashed exactly where it disappears. **Accuracy** is that depth
  image's size; raise it for very fine detail.
- **Drafting layout.** The views use cameras of their own, oriented the way a drawing
  needs. The plan is seen with the front at the bottom, so its width lines up with the front
  elevation's, and the side view stands upright. **Third Angle** puts the plan above and the
  right view on the right; **First Angle** puts the plan below and the right view on the
  left.
- **Dimensions** print each view's overall width and height in millimetres.

Because lines come from the mesh, a curved face's tessellation can add short creases where
the facets are coarse. A higher Crease Angle, or a finer Tessellation Deflection at import,
removes them. The drawings have no centre lines or detailed dimensioning; they are
a faithful outline, not a finished drawing.

#### Randomization

**Randomize** varies each image for training data while keeping every annotation exact:

| Setting | What varies |
| --- | --- |
| **Camera Jitter**, **Distance Jitter** | Each view's camera swings up to this far off its canonical direction, and moves nearer or farther |
| **Lights** | The rig turns about the vertical by up to **Light Turn**, and each light changes strength by up to **Light Strength** |
| **HDRI** | Each image is lit and backed by a random HDRI from **HDRI Folder** (empty: the studio HDRIs that ship with Blender), turned and scaled at random |
| **Materials** | The product gets a random material preset and colour per image, in Full renders (not when Material Pool variants are on, which choose the materials instead) |
| **Distractors** | Random shapes in random colours, placed behind the product as each camera sees it, in Full renders |

Every draw comes from the **Seed**, the product's label and the view, so the same settings
always give the same images. A product or view added later does not shift anyone else's
numbers. A view's image, mask, depth, normals and part IDs are all rendered from the same
jittered camera, and that is the camera `cameras.json`, `transforms.json` and BOP record.
Distractors are only ever placed on the far side of the product from the camera, so they
never cover it, and they appear only in Full renders. Masks, part IDs, COCO instances and BOP
visibility therefore stay exactly the product. Turntables are not randomized. Everything is
put back afterwards: lights, world, cameras, and the distractors are deleted.

## Command line

Everything the panels do can run without Blender's window, from a job file:

```bash
blender -b --factory-startup --python multiview_product_renderer/cli.py -- --config job.json
```

The add-on does not need to be installed for this: `cli.py` loads it from the folder it sits
in. A job is JSON or TOML, and relative paths in it are relative to the job file:

```json
{
  "inputs": ["parts/", "extra/housing.step"],
  "recursive": true,
  "output": "renders/",
  "freecad": "C:/Program Files/FreeCAD 1.1/bin/freecadcmd.exe",
  "step_import_mode": "FREECAD",
  "standardize": false,
  "auto_orient": "FLAT",
  "scene_setup": true,
  "settings": {
    "render_mode": "CLAY",
    "view_set": "ALL",
    "pass_depth": true,
    "export_coco": true,
    "turntable_elevation": 20
  },
  "render": {"engine": "CYCLES", "samples": 64, "device": "CPU",
             "resolution": [1024, 1024], "file_format": "PNG"},
  "save_blend": "renders/job.blend"
}
```

| Key | Meaning |
| --- | --- |
| `blend` | Start from this `.blend` instead of an empty scene. With no `inputs`, its existing products are rendered |
| `inputs`, `recursive` | Files and folders to import (folders expanded, sorted) |
| `output` | Output folder; `--output` overrides it |
| `freecad`, `step_import_mode`, `deflection` | STEP/IGES conversion, as in the add-on preferences |
| `standardize`, `auto_orient` | Run Standardize Products / Auto Orient (true, `"FLAT"` or `"PCA"`) on everything after import |
| `scene_setup` | Apply Scene Setup (lighting, background, ground). Default true |
| `settings` | Any panel setting by name; `--list-settings` prints them all with their types. Angles are in degrees |
| `render` | `engine`, `samples`, `device`, `resolution`, `percentage`, `file_format` |
| `save_blend` | Save the set-up scene afterwards, to open and inspect in Blender |

Other modes:

- `--check` imports and sets up, runs the pre-flight check, prints its findings and renders
  nothing.
- `--shard 2/8` imports and renders only every eighth file, starting with the third. Labels
  still count through the whole job, so eight shards started at once, on one machine or
  eight, write exactly the files one run would. Each writes its own
  `manifest_shard02.json`, `coco_shard02.json` and BOP `models_info_shard02.json`.
- `--merge renders/` then combines those into `manifest.json`/`.csv`, `coco.json` and
  `models_info.json`.
- `--list-settings` prints every setting `settings` accepts.

It prints a `MULTIVIEW_SUMMARY {...}` JSON line at the end. The exit code is 0 when
everything rendered, 1 when some images failed, and 2 when the job could not run: a bad job
file, nothing imported, or pre-flight errors.

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

## Tests

The `tests/` folder holds the test suite: each `test_*.py` runs inside a background Blender
and checks the add-on end to end, by rendering real images and reading them back.

```bash
python tests/run_tests.py --blender "C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"
```

Any Python 3 runs the runner, including Blender's own (`<Blender>/5.0/python/bin/python`).
FreeCAD is optional: with `freecadcmd` on `PATH`, or `FREECAD_CMD` set, the STEP and IGES
import checks run too; without it they are skipped (`FREECAD_CMD=none` forces that). GitHub
Actions runs the suite on every push against Blender 5.0.0 (`.github/workflows/tests.yml`),
without FreeCAD.

The suite is written against **Blender 5.0**. The add-on aims to support 4.0 and newer, but
only 5.0 is tested.

## License

MIT. See [LICENSE](LICENSE).
