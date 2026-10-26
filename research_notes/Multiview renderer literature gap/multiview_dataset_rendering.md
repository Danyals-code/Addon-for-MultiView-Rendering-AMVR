# Multi-view rendering protocols in CV and 3D-generation datasets (positioning for MultiView Product Renderer)

Verification note: items marked **[fetched]** were confirmed against the primary source during this session (Oct 2026). Items marked **[from paper, not re-fetched]** come from the cited primary paper or repo but could not be re-opened this session because PDF fetches timed out. Re-check those numbers before quoting them in a publication.

## Q1. Multi-view CNN era (MVCNN, ModelNet/ShapeNet conventions, RotationNet, Render for CNN)

### Takeaway
Classification-era work used a small set of fixed, hand-picked rigs: 12 views on a 30-degree-elevated ring (which assumes an upright object), or 20/80 views from polyhedron vertices (no upright assumption). Shading was simple and untextured (Phong). "Render for CNN" introduced randomized, Blender-based synthetic rendering with random lighting and backgrounds. Each paper shipped its own scripts, and none produced a reusable rig standard.

### Cited Findings
- MVCNN (Su et al., ICCV 2015), 12-view setup: assumes upright meshes. 12 virtual cameras are placed every 30 degrees around the vertical axis, elevated 30 degrees from the ground plane and pointing at the centroid. Meshes are rendered with the Phong reflection model, with no colour or texture, after being uniformly scaled to fit the viewing volume. [from paper, not re-fetched] — [MVCNN arXiv 1505.00880](https://arxiv.org/abs/1505.00880)
- MVCNN, 80-view setup: no upright assumption. 20 cameras sit at the vertices of an enclosing polyhedron (the paper says "icosahedron", but an icosahedron has only 12 vertices; 20 vertices is a dodecahedron), and each camera renders 4 in-plane rotations (0/90/180/270 degrees), giving 80 views. [from paper, not re-fetched] — [MVCNN arXiv 1505.00880](https://arxiv.org/abs/1505.00880)
- RotationNet (Kanezaki et al., CVPR 2018) uses two rigs: (i) 12 views around an upright object, like MVCNN, and (ii) 20 views from the vertices of a dodecahedron. It treats viewpoint labels as latent variables. Results are reported on ModelNet10/40. [from paper, not re-fetched] — [RotationNet arXiv 1603.06208](https://arxiv.org/abs/1603.06208)
- Render for CNN (Su et al., ICCV 2015) renders ShapeNet models in Blender with randomized viewpoint, lighting, truncation and backgrounds (SUN397 images), to train viewpoint estimators. It synthesized about 2.4M images. The code is a research repo (ShapeNet/RenderForCNN). [from paper, not re-fetched] — [Render for CNN arXiv 1505.05641](https://arxiv.org/abs/1505.05641); [GitHub ShapeNet/RenderForCNN](https://github.com/ShapeNet/RenderForCNN)

### Inferences
- The 12-view, 30-degree-elevation ring became a de facto convention for upright objects. The add-on's canonical six orthographic views are a different (engineering-drawing) convention, so offering an "MVCNN 12-view" preset would let users reproduce benchmarks directly.
- Normalization in this era was "scale to fit the view volume" with untextured shading. The add-on's clay pass is the closest analogue.

### Gaps
- MVCNN image resolution and exact light placement could not be re-verified this session.

## Q2. 3D-generation era: rigs, normalization, lighting, passes and tools

### Takeaway
Each major work defines its own rig, and no two are the same.
- Rigs vary from uniform random-sphere sampling (Zero-1-to-3, LRM, TRELLIS) to fixed rings: 16 views at 30 degrees (SyncDreamer), 6 views alternating +20/-10 degrees (Zero123++ v1.2), 4 orthogonal views (MVDream, Instant3D, cadrille), 6 orthographic views (Wonder3D), and 38 views across rings plus top/bottom (G-Objaverse).
- Normalization ranges from [-0.5, 0.5]^3 to [-1, 1]^3.
- Field of view is variously fixed at 30, 40 or 49.1 degrees, or random between 15 and 60.
- Lighting is random area lights, random HDRI, or path-traced.
- Almost all use Blender (raw bpy scripts or BlenderProc), but each project uses its own script.

### Cited Findings

**Objaverse / Objaverse-XL (data source plus reference renderer)**
- The Objaverse-XL rendering script is pinned to Blender 3.2.2. It renders 12 views per object by default (`num_renders=12`) at randomized camera locations, with an option such as `--only_northern_hemisphere`. Outputs are PNG images, a 3x4 camera matrix per view as `.npy`, and a `metadata.json` (bbox, mesh/poly counts, lamp_count, sha256). Each object's output is zipped. It runs via `python3 main.py` and needs Xorg on headless servers. [fetched] — [objaverse-xl scripts/rendering README](https://github.com/allenai/objaverse-xl/tree/main/scripts/rendering)

**Zero-1-to-3 (Liu et al., ICCV 2023)**
- 12 views per object, with cameras sampled uniformly on a sphere and pointing at the object centre. Radius is drawn uniformly from [1.5, 2.2], horizontal FoV is 49.1 degrees, and the camera is a pinhole. Assets are normalized to the unit cube [-0.5, 0.5]^3. Renders are 512x512 (training used 256x256) on a white background, with "randomized area lighting", in Blender Cycles (128 samples plus denoising). About 10M images in total. The rendering code is inherited from the Objaverse rendering repo. [fetched] — [Zero-1-to-3 arXiv 2303.11328](https://arxiv.org/abs/2303.11328)

**Zero123++ (Shi et al., 2023)**
- Six views tiled in a 3x2 grid, using absolute elevations and azimuths relative to the input view. Trained on Objaverse with "random HDRI environment lighting". [fetched] — [Zero123++ arXiv 2310.15110](https://arxiv.org/abs/2310.15110)
- v1.1 uses azimuths 30/90/150/210/270/330 and elevations alternating 30/-20 degrees. v1.2 uses the same azimuths, elevations alternating 20/-10 degrees, and a fixed output FoV of 30 degrees. v1.2 "always outputs views assuming a normalized object size" and is more robust to input FoV. Outputs have a gray background (the zero value of the SD VAE). [fetched] — [Zero123++ README](https://github.com/SUDO-AI-3D/zero123plus)
- The paper and README disagree on v1.1 elevations: the paper says 30 degrees down and 20 degrees up, the README says 30/-20. The protocol changed between v1.1 and v1.2 within a single project. [fetched] — [paper](https://arxiv.org/abs/2310.15110) vs [README](https://github.com/SUDO-AI-3D/zero123plus)

**SyncDreamer (Liu et al., ICLR 2024)**
- 16 fixed target views at 30 degrees elevation, with azimuths spread evenly over 0-360 degrees (22.5-degree steps). Each object also gets 16 extra input views at the same azimuths but random elevations. Objects are placed at the origin and normalized inside a cube of side 1. Uses about 800k Objaverse objects, at 256x256 latent-compatible resolution. The paper does not specify the engine, lighting, distance or FoV. Evaluation uses 30 randomly chosen GSO objects. [fetched] — [SyncDreamer arXiv 2309.03453](https://arxiv.org/abs/2309.03453)

**Wonder3D (Long et al., CVPR 2024)**
- Six views (front, front-right, right, back, left, front-left), with RGB and normal maps generated jointly. Trained on the Objaverse LVIS subset (about 30k+ objects after cleanup), rendered with BlenderProc, with random rotations applied to assets. Objects are centred at unit scale, training is at 256x256, and evaluation uses the same 30 GSO objects as SyncDreamer. [fetched] — [Wonder3D arXiv 2310.15008](https://arxiv.org/abs/2310.15008)
- The repo's `render_codes` provides `blenderProc_ortho.py` (orthographic, `--ortho_scale 1.35`, resolution 512) and `blenderProc_persp.py` (perspective, `--radius 2.0`), plus batch shell scripts. BlenderProc uses Cycles, which the README says can hang on some GPUs (A800). [fetched] — [Wonder3D render_codes README](https://github.com/xxlong0/Wonder3D/tree/main/render_codes)

**MVDream (Shi et al., ICLR 2024)**
- About 350K Objaverse objects (CLIP-filtered). Each is rendered at 32 uniformly spaced azimuths, twice with different random settings. Objects are centred and fit in [-0.5, 0.5]. FoV is random in [15, 60] degrees and elevation random in [0, 30] degrees. Camera distance is 0.5 times the NDC focal length times a random factor in [0.9, 1.1], which keeps the apparent size constant across FoVs. Lighting is a random Blender HDRI. Renders are saved as RGBA, and the background is filled with random grayscale during training. Training samples 4 orthogonal views out of the 32, at 256x256. [fetched] — [MVDream arXiv 2308.16512](https://arxiv.org/abs/2308.16512)

**Instant3D (Li et al., ICLR 2024)**
- Generates 4 views in a 2x2 grid at fixed elevation 20 degrees and azimuths 0/90/180/270, then reconstructs with a feed-forward LRM-style model. [from paper, not re-fetched] — [Instant3D arXiv 2311.06214](https://arxiv.org/abs/2311.06214)

**LRM (Hong et al., ICLR 2024)**
- 730,648 Objaverse assets normalized to [-1, 1]^3. Each gets 32 random views with the camera pointing at the shape, ball radius in [1.5, 3.0] and height in [-0.75, 1.60]. Renders are 1024x1024 on a pure white background. Training also uses 220,219 MVImgNet videos, cropped and resized using predicted masks with background removed (Rembg). Poses are normalized so the input camera sits at [0, -2, 0] with z up, and intrinsics are normalized by image size. The paper does not state lighting or the render tool. Evaluation uses 100 random GSO objects with 20 reference views each. [fetched] — [LRM arXiv 2311.04400](https://arxiv.org/abs/2311.04400)

**TripoSR (Tochilkin et al., 2024)**
- An LRM-derivative trained on a curated Objaverse subset. The report says its rendering techniques were changed to better match the distribution of real images. [from paper, not re-fetched; exact rig not verified] — [TripoSR arXiv 2403.02151](https://arxiv.org/abs/2403.02151)

**TRELLIS (Microsoft, 2024–25)**
- `dataset_toolkits/render.py` defaults to 150 views per object, placed on a Hammersley sequence over the sphere with a random per-object offset. Radius is fixed at 2, FoV fixed at 40 degrees, and resolution 512x512. Uses Blender 3.0.1 with Cycles. A `transforms.json` per object marks success, and Blender stdout/stderr go to DEVNULL, so render failures are silent. [fetched] — [TRELLIS render.py](https://github.com/microsoft/TRELLIS/blob/main/dataset_toolkits/render.py)

**G-Objaverse / Gobjaverse (Alibaba, used by RichDreamer)**
- 38 views per object: a 24-view upper ring (elevation 5–30 degrees, 15-degree azimuth steps), a 12-view lower ring (elevation -5 to 5 degrees, 30-degree steps), plus top and bottom views. Rendered with Alibaba's TIDE renderer, a hybrid that rasterizes the first hit and path-traces indirect lighting, with adaptive sampling, denoising and path guiding. Passes are RGB, albedo, normal and depth. About 30M images, costing about 2,000 A10 GPU hours. [fetched] — [G-Objaverse project page](https://aigc3d.github.io/gobjaverse/)
- The release covers about 280K objects (about 6.5 TB). Per-view files are RGB PNG, `_albedo.png`, `_hdr.exr`, `_mr.png` (metal/roughness) and `_nd.exr` (normal and depth), plus a per-view JSON of camera info. The renderer is described as Unity-based, with poses converted to Blender's world-to-camera convention and normals in a "Normal-Bae" camera frame. [fetched] — [RichDreamer gobjaverse README](https://github.com/modelscope/richdreamer/tree/main/dataset/gobjaverse)
- The project page and the repo disagree on the renderer. The page names TIDE (a hybrid rasterization/path-tracing engine), while the repo README calls it "Unity-based". [fetched] — [project page](https://aigc3d.github.io/gobjaverse/) vs [README](https://github.com/modelscope/richdreamer/tree/main/dataset/gobjaverse)

**Scanned and real-capture datasets (for contrast)**
- Google Scanned Objects: 1,030 high-quality scanned household items (CC-BY 4.0). Papers use it mainly for evaluation renders. [from paper, not re-fetched] — [GSO arXiv 2204.11918](https://arxiv.org/abs/2204.11918)
- OmniObject3D: about 6,000 scanned objects in 190 categories. Provides Blender multi-view renders, point clouds and real captured videos with COLMAP poses. [from paper, not re-fetched; per-object view count not verified] — [OmniObject3D arXiv 2301.07525](https://arxiv.org/abs/2301.07525)
- CO3D: about 19k turntable-style phone videos (about 1.5M frames) across 50 MS-COCO categories, with poses and point clouds from COLMAP. [from paper, not re-fetched] — [CO3D arXiv 2109.00512](https://arxiv.org/abs/2109.00512)
- MVImgNet: about 6.5M frames from about 219k videos across 238 classes, with COLMAP-annotated poses. [from paper, not re-fetched] — [MVImgNet arXiv 2303.06042](https://arxiv.org/abs/2303.06042). LRM reports pre-processing 220,219 MVImgNet videos ([fetched](https://arxiv.org/abs/2311.04400)), which differs slightly from the count above.

### Inferences
- **Normalization conflicts.** Works use [-0.5, 0.5]^3 (Zero-1-to-3, MVDream), a cube of side 1 (SyncDreamer), [-1, 1]^3 (LRM) and "unit scale" (Wonder3D). A cube of side 1 and [-0.5, 0.5]^3 are the same box, so the real outlier is LRM's [-1, 1]^3, which is twice as large. Camera radius and FoV pairs also differ: r in [1.5, 2.2] at 49.1 degrees, r = 2 at 40 degrees, fixed 30-degree FoV, and FoV in [15, 60] with distance compensation. So "normalize to a target size at the origin" is universal in spirit but parameterized differently everywhere. A renderer that exposes these as named presets ("Zero123 / MVDream / LRM / TRELLIS / SyncDreamer / Zero123++ v1.2 / G-Objaverse") would be directly useful.
- **Projection.** Orthographic rigs appear only in Wonder3D (an orthographic BlenderProc script) and the classic six-view CAD convention. Most generation models train on perspective views. The add-on's shared orthographic six-view rig matches Wonder3D-style and engineering conventions, and its perspective views cover the rest.
- **Passes.** Normals and depth are standard in the newer datasets (G-Objaverse normal/depth/albedo; Wonder3D normals; Zero123++ depth ControlNet trained on "normalized linear depth"). Every dataset exports per-view camera matrices. The add-on's lack of depth, normals and pose export is therefore the biggest functional gap against 3D-generation use.
- **Lighting.** Generation datasets randomize lighting (random area lights, random HDRI) for augmentation, while the add-on uses consistent studio light that follows the camera. That suits product and catalogue consistency, but an ML user would want an optional randomized or HDRI mode.

### Gaps
- Instant3D's exact FoV, background and lighting, TripoSR's rig, OmniObject3D's per-object view count, and Wonder3D's normal frame (world vs. input-camera) were not verified this session.
- G-Objaverse image resolution: a folder name ("campos_512_v4") suggests 512, but no source states it.

## Q3. Are the scripts reusable tools or ad-hoc? Known inconsistencies and reproducibility problems

### Takeaway
Reusable, generic tooling exists: BlenderProc, Kubric and the Objaverse-XL scripts. But each 3D-generation paper ships its own Blender script, tied to a specific Blender version, rig, normalization and lighting. The protocols differ enough that models need adapters (elevation estimators, FoV normalization), and benchmark numbers on GSO are not comparable across papers.

### Cited Findings
- Zero-1-to-3 reused the Objaverse rendering repo's code. [fetched] — [Zero-1-to-3](https://arxiv.org/abs/2303.11328)
- Wonder3D used BlenderProc (cited as BlenderProc2) with its own ortho/persp wrapper scripts. [fetched] — [Wonder3D](https://arxiv.org/abs/2310.15008); [render_codes](https://github.com/xxlong0/Wonder3D/tree/main/render_codes)
- BlenderProc is a general, procedural Blender pipeline for photorealistic synthetic data. [from paper, not re-fetched] — [BlenderProc arXiv 1911.01911](https://arxiv.org/abs/1911.01911); [GitHub DLR-RM/BlenderProc](https://github.com/DLR-RM/BlenderProc)
- Kubric is a scalable data generator built on Blender and PyBullet. Its examples include GSO-based multi-object scenes. [from paper, not re-fetched] — [Kubric arXiv 2203.03570](https://arxiv.org/abs/2203.03570)
- Pinned Blender versions differ across projects: 3.2.2 for Objaverse-XL and 3.0.1 for TRELLIS. TRELLIS also discards Blender's output, so failures are silent. [fetched] — [objaverse-xl](https://github.com/allenai/objaverse-xl/tree/main/scripts/rendering); [TRELLIS render.py](https://github.com/microsoft/TRELLIS/blob/main/dataset_toolkits/render.py)
- **Pose-convention problem.** Zero-1-to-3 uses poses relative to the input view, so it needs the input's elevation. Downstream pipelines therefore add an elevation estimator that "introduces extra error". Zero123++ switched to absolute elevations with relative azimuths. [fetched] — [Zero123++](https://arxiv.org/abs/2310.15110)
- **Field-of-view and scale problem.** Zero123++ v1.2 had to "unify" the output FoV to 30 degrees and assume a normalized object size, because inputs come with varying FoVs and croppings. [fetched] — [Zero123++ README](https://github.com/SUDO-AI-3D/zero123plus)
- **Background inconsistency.** Backgrounds are white in Zero-1-to-3 and LRM, gray (the VAE zero value) in Zero123++, and random grayscale in MVDream. [fetched] — [Zero-1-to-3](https://arxiv.org/abs/2303.11328); [LRM](https://arxiv.org/abs/2311.04400); [Zero123++ README](https://github.com/SUDO-AI-3D/zero123plus); [MVDream](https://arxiv.org/abs/2308.16512)
- **Evaluation inconsistency.** SyncDreamer and Wonder3D evaluate on the same 30 GSO objects, and SyncDreamer does not specify how they were rendered. LRM uses 100 random GSO objects with 20 reference views each. [fetched] — [SyncDreamer](https://arxiv.org/abs/2309.03453); [Wonder3D](https://arxiv.org/abs/2310.15008); [LRM](https://arxiv.org/abs/2311.04400)
- **Same project, conflicting descriptions.** G-Objaverse's renderer is described as TIDE on the project page and as Unity-based in the repo README. Zero123++ v1.1 elevations differ between the paper and the README. [fetched] — sources as in Q2.

### Inferences
- The gap is a standardized, documented, parameterized rig with an exported manifest that records every protocol parameter (normalization box, radius, FoV, elevations, azimuths, lighting, background, Blender version). It is not a missing renderer, since Blender and BlenderProc are already ubiquitous. The add-on's JSON/CSV manifest is a strong base if it records these fields.
- Shared framing for all objects (one camera rig and one scale) is exactly what fixed-ring datasets (SyncDreamer, Zero123++, G-Objaverse) rely on. The add-on's "one framing shared across all objects" maps well to these.
- No reviewed work uses a no-code GUI. All are command-line batch scripts aimed at ML engineers, so a GUI add-on is differentiated for non-ML users (product, CAD and industrial teams), but it must also run headless and in batch to be credible for dataset building.

### Gaps
- I found no systematic, published study that quantifies how much rendering-protocol differences (normalization, lighting, FoV) change benchmark results. The evidence above is anecdotal: per-paper fixes and adapters.

## Q4. Standard camera and pose export formats

### Takeaway
Two families dominate:
- **NeRF-style `transforms.json`:** camera-to-world 4x4 matrices in the OpenGL/Blender convention, with `camera_angle_x` or explicit `fl_x`/`fl_y`/`cx`/`cy`/`w`/`h` and optional depth and mask paths. Used by NeRF, Instant-NGP, nerfstudio, and TRELLIS (which writes `transforms.json`).
- **COLMAP text or binary:** world-to-camera quaternion plus translation in the OpenCV convention.

Research datasets also use ad-hoc numpy matrices (Objaverse-XL 3x4 `.npy`) or per-view JSON (G-Objaverse).

### Cited Findings
- **nerfstudio convention.** Uses the OpenGL/Blender/original-NeRF convention: +X right, +Y up, +Z back, so the camera looks down -Z. COLMAP/OpenCV flips Y and Z.
  - `transforms.json` may carry global intrinsics: `camera_model` (OPENCV or OPENCV_FISHEYE), `fl_x`, `fl_y`, `cx`, `cy`, `w`, `h`, and distortion `k1`–`k4`, `p1`, `p2`.
  - Each frame has a 4x4 camera-to-world `transform_matrix`, a `file_path`, and optional `depth_file_path` (16/32-bit, millimetres, 0 = unknown) and `mask_path`.
  
  [fetched] — [nerfstudio data conventions](https://docs.nerf.studio/quickstart/data_conventions.html)
- **Original NeRF synthetic "Blender" scenes.** Use `transforms_{train,val,test}.json` holding `camera_angle_x` and per-frame `transform_matrix`, rendered from Blender. [from repo, not re-fetched] — [NeRF GitHub bmild/nerf](https://github.com/bmild/nerf)
- **Instant-NGP.** Its `transforms.json` extends the NeRF format with fields such as explicit intrinsics and `aabb_scale`. [from repo, not re-fetched] — [instant-ngp nerf dataset tips](https://github.com/NVlabs/instant-ngp/blob/master/docs/nerf_dataset_tips.md)
- **COLMAP.** The text format stores `cameras.txt` (intrinsics per camera model) and `images.txt` (per image: QW QX QY QZ TX TY TZ, a world-to-camera rotation and translation). [from docs, not re-fetched] — [COLMAP output format](https://colmap.github.io/format.html)
- **Objaverse-XL.** Writes one 3x4 camera matrix per view as `.npy`. [fetched] — [objaverse-xl rendering](https://github.com/allenai/objaverse-xl/tree/main/scripts/rendering)
- **G-Objaverse.** Writes per-view JSON camera info in Blender's world-to-camera convention, with normal/depth in EXR. [fetched] — [gobjaverse README](https://github.com/modelscope/richdreamer/tree/main/dataset/gobjaverse)
- **BlenderNeRF.** An existing open-source Blender add-on that exports NeRF-compatible camera data (`transforms.json`) from Blender scenes. It is the closest GUI competitor for pose export, but it targets NeRF capture, not normalized object-collection rendering. [from repo, not re-fetched] — [GitHub maximeraafat/BlenderNeRF](https://github.com/maximeraafat/BlenderNeRF)

### Inferences
- The minimum viable pose export for the add-on is a nerfstudio/Instant-NGP-compatible `transforms.json` per object, written in Blender's own OpenGL convention so no axis flip is needed. Add optional `depth_file_path` and `mask_path` (the add-on already produces masks), and optionally a COLMAP text export. Also store the normalization transform (scale and offset) in the manifest, so poses map back to original CAD units.

### Gaps
- No single "dataset rendering manifest" standard was found. Each project's metadata schema is bespoke.

## Q5. Work that targets CAD or engineering parts specifically

### Takeaway
CAD-specific work (image-to-CAD, CAD reconstruction) renders B-rep models tessellated to meshes, from a few fixed views. Examples are 4 views in a 2x2 grid in cadrille, and a single isometric Blender view per shape in a CADFit benchmark. These are ad-hoc and minimally documented: projection, lighting and tool are often unstated. None of the 3D-generation datasets above target engineering parts. This is a plausible niche for a CAD-aware, documented multi-view renderer with canonical orthographic views.

### Cited Findings
- **cadrille (ICLR 2026).** Multi-modal CAD reconstruction from point clouds, multi-view images or text. Images are "rendered with fixed camera positions, and concatenated into 2x2 grid" (4 views tiled into one 268x268 image). The B-rep is tessellated to a mesh and then rendered.
  - Projection, lighting and tool are not specified. Ground truth is normalized to [-0.5, 0.5]^3 for evaluation.
  - Data includes DeepCAD (Text2CAD version, about 160k train / 8,046 test), CAD-Recode (about 1M procedural CadQuery programs), Fusion360 (1,725 test) and CC3D scans.
  - It also evaluates on Omni-CAD (CAD-MLLM's dataset), whose rendering protocol cadrille does not describe.
  
  [fetched] — [cadrille arXiv 2505.22914](https://arxiv.org/html/2505.22914v3)
- **CADFit (2026).** Builds an ABC image-to-CAD benchmark by sampling 150 shapes per complexity window and rendering one isometric Blender view per shape. [search-result summary, not opened] — [CADFit arXiv 2605.01171](https://arxiv.org/pdf/2605.01171)
- **CADBench (2026).** Reportedly a unified multimodal CAD benchmark with 18,000 samples drawn from DeepCAD, Fusion 360, ABC, MCB and Objaverse, with single-view and multi-view render inputs. [search-result summary, not opened; render parameters not verified] — [emergentmind entry 2605.10873](https://www.emergentmind.com/papers/2605.10873)
- **IEEE DataPort.** Lists a "Multi-View-Image-Based CAD Reverse Engineering Dataset": single and multi-view RGB renders from canonical viewpoints, paired with DeepCAD-style sketch/extrude sequences. [search-result summary, not opened] — [IEEE DataPort](https://ieee-dataport.org/documents/multi-view-image-based-cad-reverse-engineering-dataset)
- **UniCAD (2026).** Notes that ABC has over 1M models but provides only B-rep geometry, without modelling histories. [search-result summary, not opened] — [UniCAD arXiv 2606.05058](https://arxiv.org/pdf/2606.05058)
- **ABC dataset.** About 1M CAD models from Onshape, distributed as geometry (B-rep/meshes), not as standardized renders. [from paper, not re-fetched] — [ABC arXiv 1812.06216](https://arxiv.org/abs/1812.06216)

### Inferences
- Engineering-part rendering is fragmented. Each CAD paper picks a few fixed views (isometric, 4 orthogonal) without publishing a reusable renderer or full parameters. A tool that imports STEP/CAD and renders canonical orthographic front/back/top/bottom/left/right views plus isometric/perspective views, with masks, line-art (edges matter for CAD), depth, normals and pose export, would fill a real gap for CAD-ML benchmarks.
- The add-on's line-art and clay passes are unusually well matched to CAD (texture-less parts), where photoreal RGB with HDRI adds little.

### Gaps
- Exact rendering parameters for Omni-CAD/CAD-MLLM, CADBench and the IEEE DataPort dataset were not verified. The CADFit/CADBench/UniCAD entries rest on search-result summaries only.
- I did not find a CAD-specific dataset that publishes depth or normal renders with camera poses in NeRF or COLMAP format.
