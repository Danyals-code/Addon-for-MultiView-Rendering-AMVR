# Line drawings from 3D models: methods, datasets, and engineering-view (orthographic three-view) drawings

Context: these notes are for placing the "MultiView Product Renderer" Blender add-on, which writes a "line art" pass for each view. That pass is silhouettes plus creases found in image space: it renders the model with a normal matcap and applies a crease-angle threshold, optionally over a clay render. The add-on also renders orthographic front, top and side views.

Source reliability: items marked **[fetched]** were confirmed from the page or search snippet this session. Items marked **[background]** come from well-known primary sources that were not re-fetched this session. Their URLs are the canonical project pages, but the writer should spot-check them before quoting exact numbers.

---

## Q1. Classic NPR line rendering: which line types exist, and which are practical in tools today?

### Takeaway
The graphics literature splits lines into view-dependent types and view-independent types:
- **View-dependent:** occluding contours and silhouettes, suggestive contours, and apparent ridges.
- **View-independent:** creases, ridges and valleys, and material or part boundaries.

Each type also needs a separate visibility (hidden-line) computation. In today's tools only contours, creases, boundaries, intersections and visibility are robust. Blender ships two object-space line engines that do this: Freestyle (raster render, with an SVG export add-on) and Grease Pencil Line Art (vector strokes, with selectable occlusion levels). Suggestive contours and apparent ridges remain mostly research code. The add-on's matcap-plus-threshold approach is an image-space approximation of "contour + crease" and has no visibility information.

### Cited Findings
- Bénard and Hertzmann's tutorial "Line Drawings from 3D Models" (Foundations and Trends in Computer Graphics and Vision, vol. 11 no. 1–2, pp. 1–159, 2019; arXiv:1810.01175) is the standard reference. It covers the geometry of occluding contours on meshes and smooth surfaces, plus algorithms for extracting contours, computing their visibility, and stylized rendering. It compares exact methods with hardware-accelerated fast methods and surveys other line types. **[fetched]** — [arXiv](https://arxiv.org/abs/1810.01175); [NOW Publishers](https://nowpublishers.com/article/Details/CGV-075)
- **Suggestive contours** (DeCarlo, Finkelstein, Rusinkiewicz and Santella, SIGGRAPH 2003): these are lines where the surface would become a contour in a nearby viewpoint, that is, zeros of radial curvature where its directional derivative is positive. They are view-dependent and complement occluding contours. Reference code is the "rtsc" real-time suggestive contours library from Princeton. **[background]** — [Princeton project page](https://gfx.cs.princeton.edu/proj/sugcon/)
- **Apparent ridges** (Judd, Durand and Adelson, SIGGRAPH 2007): view-dependent ridges defined on the surface as projected to the screen. **[background]** — [MIT project page](https://people.csail.mit.edu/tjudd/apparentridges.html)
- **"Where Do People Draw Lines?"** (Cole et al., SIGGRAPH 2008): artists drew the same rendered 3D models, and the study then compared their lines with computed line types. It found that occluding contours plus a combination of other types (suggestive contours, ridges and valleys, apparent ridges) explain most of the artists' lines. This artist dataset later became the benchmark for learned line drawing. **[background]** — [Princeton project page](https://gfx.cs.princeton.edu/proj/ld3d/). Neural Contours confirms that the Cole et al. drawings are the standard evaluation set. **[fetched]** — [Neural Contours, CVPR 2020](https://openaccess.thecvf.com/content_CVPR_2020/html/Liu_Neural_Contours_Learning_to_Draw_Lines_From_3D_Shapes_CVPR_2020_paper.html)
- **Blender Grease Pencil Line Art modifier:**
  - The 2.93 and 3.2 manuals list the edge types Contour (the separation line between front- and back-facing faces), Loose, Material Borders, Edge Marks, Intersections and Crease.
  - Crease is set by a Crease Threshold: "Edge angles that are smaller than this value will be treated as crease." The current dev manual instead has "Crease on Smooth" and "Crease on Sharp" options.
  - An Occlusion subpanel has a Level and a Range. Level 0 gives visible lines; Level 1 selects lines hidden by exactly one layer of faces. This makes it possible to extract hidden lines geometrically.
  - The output is Grease Pencil vector strokes.

  **[fetched, via search snippets of the manual]** — [Blender manual (dev)](https://docs.blender.org/manual/en/dev/grease_pencil/modifiers/generate/line_art.html); [2.93 manual](https://docs.blender.org/manual/ja/2.93/grease_pencil/modifiers/generate/line_art.html); [3.2 manual](https://docs.blender.org/manual/fi/3.2/grease_pencil/modifiers/generate/line_art.html)
- **Freestyle SVG Exporter:** this Blender add-on exports Freestyle renders to SVG. It can fill contours with material colours and bundle an animation into one SVG. Per the manual, "Because the representation of Freestyle strokes and SVG path objects is fundamentally different, a one-on-one translation between Freestyle and SVG is not possible." **[fetched, snippets of 4.0/4.1 manual]** — [Blender 4.1 manual](https://docs.blender.org/manual/en/4.1/addons/render/render_freestyle_svg.html). The page returned 404 at `/manual/en/latest/addons/...`. This suggests that from 4.2 onward the add-on is no longer in the bundled-add-ons section of the manual (Blender moved most bundled add-ons to the Extensions platform in 4.2), but this was **not confirmed**.

### Inferences
- The add-on's line pass recovers occluding contours (from silhouette or depth breaks) and creases (from normal discontinuities above an angle threshold). These are the same two line families that Line Art calls "Contour" and "Crease", and they are the two types the literature finds most important (Cole et al.). It does not produce suggestive contours or apparent ridges. Those matter mostly for smooth organic shapes and much less for CAD-like products.
- Line Art in Blender already gives geometric contour, crease, intersection, material-border and occlusion-level lines as vectors. A natural upgrade path is an optional Line Art-based pass, which adds visible and hidden separation and vector output. Freestyle with the SVG exporter is the other route.

### Gaps
- I did not fetch the current (Blender 5.x) Line Art manual text, which was truncated by page size. The exact current edge-type list and whether "Light Contour" and "Shadow" types are present are unverified.
- The status of the Freestyle SVG exporter in Blender 4.2+ (extension vs removed) is not confirmed.

---

## Q2. Datasets and ML that use rendered line drawings: how were the training drawings made?

### Takeaway
Most sketch, line-drawing and CAD learning pipelines **synthesize their training drawings by rendering 3D or CAD data**, because paired human drawings are scarce. The generators fall into three groups:
1. **NPR line extractors on meshes**: contours, suggestive contours, ridges (for example Neural Contours candidates).
2. **CAD-aware stroke renderers**: Sketch2CAD, Free2CAD, CAD2Sketch, which draw feature curves plus construction lines from CAD sequences.
3. **B-rep hidden-line-removal (HLR) projectors**, usually pythonOCC/OpenCascade, that produce orthographic three-view engineering drawings: SPARE3D, Ortho2CAD, OrthoCAD-322K.

Sketch-based retrieval benchmarks (SHREC'13/'14) use hand-drawn queries against 3D models. Retrieval methods then commonly render line or contour views of the 3D targets to bridge the domain gap.

### Cited Findings
**Learned line drawing**
- **Neural Contours** (Liu, Nabail, Hertzmann, Kalogerakis, CVPR 2020) has two branches: a differentiable module that operates on geometric features of the 3D model (the classic line types) and an image-based module that operates on view-based shape representations. A neural module combines them at test time.
  - Training labels came from **crowdsourced rankings** of candidate drawings by unskilled workers, not from artist drawings. The paper notes that in-person artist collection "does not scale well, and it also produces data without much stylistic consistency."
  - Evaluation used the Cole et al. artist drawings plus a new, more diverse extended test set.
  - Code and data: https://github.com/DifanLiu/NeuralContours

  **[fetched]** — [arXiv 2003.10333](https://arxiv.org/abs/2003.10333); [project page](https://people.cs.umass.edu/~dliu/projects/NeuralContours)

**Sketch to CAD (synthetic drawings rendered from CAD)**
- **Sketch2CAD** (Li, Pan, Bousseau, Mitra; ACM TOG / SIGGRAPH Asia 2020): there were no paired sketch and CAD-sequence datasets, so the authors generated **10k procedural CAD protocols yielding about 40k training shapes**. They overlaid sketch curves on the built shapes and rendered them from viewpoints to produce input sketch and context maps with segmentation ground truth. It supports four CAD operations. **[fetched]** — [UCL project page](https://geometry.cs.ucl.ac.uk/projects/2020/sketch2cad); [arXiv 2009.04927](https://arxiv.org/pdf/2009.04927)
- **Free2CAD** (Li, Pan, Bousseau, Mitra; ACM TOG / SIGGRAPH 2022): a Transformer groups freehand strokes into CAD operations. It is **trained only on synthetic data** yet generalizes to sketches of real CAD models and from novice users. Code and data are at github.com/Enigma-li/Free2CAD. **[fetched]** — [UCL Discovery](https://discovery-pp.ucl.ac.uk/id/eprint/10159067); [paper PDF](https://geometry.cs.ucl.ac.uk/projects/2022/free2cad/paper_docs/Free2CAD_SIG_2022.pdf)
- **CAD2Sketch** (Hähnlein, Li, Mitra, Bousseau; ACM TOG 41(6), Art. 279, 2022; DOI 10.1145/3550454.3555488) converts CAD sequences into **concept sketches** in three steps:
  1. Generate construction lines for each CAD operation.
  2. Choose a subset of them by binary optimization, to avoid clutter.
  3. Adjust line opacity and shape so they look hand-drawn.

  It produces large numbers of paired sketches and normal maps for training sketch-to-normal networks. The synthetic sketches resemble real pairs in **OpenSketch**, a dataset of expert concept sketches. **[fetched, via the GDL-for-CAD survey and search snippets]** — [GDL for CAD survey, arXiv 2402.17695](https://arxiv.org/pdf/2402.17695); [UCL Discovery](https://discovery-pp.ucl.ac.uk/id/eprint/10190377)

**Sketch-based 3D shape retrieval**
- **SHREC'13 Large Scale Sketch-Based 3D Shape Retrieval:** 7,200 hand-drawn sketches queried against 1,258 3D models in 80 classes. Per class, 80 sketches are split 50 for training and 30 for test. **[fetched]** — [Eurographics DL](https://diglib.eg.org/handle/10.2312/3DOR.3DOR13.089-096)
- **SHREC'14 Extended Large Scale SBR:** 13,680 sketches and 8,987 3D models in 171 classes, built on a unified multimodal benchmark. A CVIU 2014 comparison evaluated 15 methods. **[fetched]** — [SHREC'14 site](https://sites.usm.edu/bli/sharp/sharp/contest/2014/SBR/)

**Three-view / engineering-drawing reconstruction (synthetic orthographic drawings rendered from CAD)**
- **PlankAssembly** (Hu et al., ICCV 2023) converts "2D line drawings from three orthographic views into 3D CAD models" using a Transformer that outputs shape programs.
  - Its dataset has **26,707 shape programs derived from parametric CAD models** (furniture/plank models).
  - The supplementary material reports separate results for noise-free inputs, noisy inputs, and "inputs with visible lines only". This implies the default input includes **hidden lines**, and that removing them is treated as a degradation.
  - Classic back-projection methods are described as sensitive to input errors.

  **[fetched]** — [arXiv 2308.05744](https://arxiv.org/abs/2308.05744); [project page](https://manycore-research.github.io/PlankAssembly/); [ICCV open access](https://openaccess.thecvf.com/content/ICCV2023/html/Hu_PlankAssembly_Robust_3D_Reconstruction_from_Three_Orthographic_Views_with_Learnt_ICCV_2023_paper.html)
- **CAD2Program** ("From 2D CAD Drawings to 3D Parametric Models: A Vision-Language Approach", arXiv 2412.11892): 368K cabinet models with real production engineering drawings from an interior-design platform (364K / 2K / 2K split).
  - The drawings contain multiple orthographic views, sometimes section views, and views that may not be aligned, plus an annotation layer with dimensions and symbols.
  - It treats drawings as raster images, encoded with a ViT.
  - It states that classical methods "all assume that a clean geometry layer with exactly three axis-aligned views" is given, and that PlankAssembly requires exactly three axis-aligned views **in vector format**.
  - A raster-encoder variant of PlankAssembly performed comparably to the vector original.

  **[fetched]** — [arXiv HTML](https://arxiv.org/html/2412.11892v2)
- **Ortho2CAD** (Joglekar, Regmi, Shimada, Kara; arXiv 2607.08891, July 2026): a **pythonOCC-based generator** renders **first-angle orthographic projections from STEP models with dashed hidden lines and bounding-box dimensions**. It produced over 1 million drawings, plus 100 drawings with manually dimensioned features. The authors name the "unavailability of large scale orthographic drawing datasets" as their core motivation. **[fetched, abstract only]** — [arXiv 2607.08891](https://arxiv.org/abs/2607.08891)
- **CReFT-CAD / TriView2CAD** (arXiv 2506.00568, 2025) is a benchmark for orthographic-projection reasoning. It argues that existing benchmarks provide **only rasterized drawings without precise dimension annotations**. **[fetched, search snippet]** — [arXiv 2506.00568](https://arxiv.org/html/2506.00568v1)
- **OrthoCAD-322K** (IIT Madras group) provides standardized orthographic and isometric views of about 322K public CAD models, in **DXF and raster** formats, for 3D reconstruction and cross-modal retrieval. **[fetched, search snippet only; PDF too large to fetch]** — [PDF](https://ed.iitm.ac.in/~raman/agcl/OrthoCAD_322K_3DoR.pdf)
- **Zenodo: "Automatic 3D CAD models reconstruction from 2D orthographic drawings"** (Zhang, Pinquié, Polette, Carasi, De Charnace, Pernot; Computers & Graphics 2023) pairs **SVG** 2D drawings with STEP models, based on the Fusion 360 Gallery, plus ABC test cases. It is licensed CC BY 4.0. **[fetched]** — [Zenodo 7785223](https://zenodo.org/records/7785223)
- **SPARE3D** (Han et al., CVPR 2020) is a spatial-reasoning benchmark built from three-view and isometric line drawings of CAD models. As I recall, they are generated with pythonOCC HLR and include hidden lines. **[background — not verified this session]**

### Inferences
- The field's demand for line drawings rendered from 3D is **very high**: nearly every sketch-to-CAD or drawing-to-CAD paper writes its own renderer. The generators differ by community:
  - Graphics groups write NPR/feature-curve renderers.
  - CAD and engineering groups use OpenCascade HLR to get exact visible and hidden edges, often dashed and in vector form.
- No standard Blender-based generator appears in this literature. A Blender add-on producing consistent orthographic three-view line drawings would be a convenience tool, not a new research contribution, unless it matched engineering conventions: exact HLR, dashed hidden lines, vector output, and consistent scale.

### Gaps
- I could not confirm from primary text exactly how PlankAssembly renders its input lines (vector segments tokenized from the B-rep, with or without dash styling); the CVF PDF returned 403.
- ProSketch, Img2CAD, OpenSketch-specific rendering details, and SketchGraphs were not researched this session. SketchGraphs is a dataset of 2D constraint sketches from Onshape, not rendered views, so it is likely out of scope.
- The SHREC sketch-track papers' own target-view rendering methods were not fetched.

---

## Q3. Is there evidence that standardized three-view drawings with consistent scale help orthographic-view-to-CAD reconstruction?

### Takeaway
Yes, in two ways:
- **Direct:** classic and current methods (PlankAssembly) *require* exactly three axis-aligned views. Recent works build datasets with dimensions because size cues measurably help.
- **Indirect:** several 2025–2026 papers explicitly call large standardized orthographic drawing datasets missing.

Recent work also pushes **away** from strict standardization (raster input, unaligned views, annotations), so that methods are robust to real drawings.

### Cited Findings
- Classical three-view reconstruction methods "all assume that a clean geometry layer with exactly three axis-aligned views" is provided. PlankAssembly requires exactly three axis-aligned views in vector format. **[fetched]** — [CAD2Program, arXiv 2412.11892](https://arxiv.org/html/2412.11892v2)
- Adding the dimension/annotation layer raised CAD2Program's F1 from 62.65 to 82.76. The authors attribute this to dimensions giving direct size references, which vector pipelines usually discard as noise. This is evidence that **scale information is highly valuable**. **[fetched]** — [CAD2Program](https://arxiv.org/html/2412.11892v2)
- Ortho2CAD cites the "unavailability of large scale orthographic drawing datasets" and generates first-angle projections with dashed hidden lines and bounding-box dimensions. **[fetched]** — [arXiv 2607.08891](https://arxiv.org/abs/2607.08891)
- TriView2CAD/CReFT-CAD says existing benchmarks have only raster drawings without precise dimension annotations. **[fetched, snippet]** — [arXiv 2506.00568](https://arxiv.org/html/2506.00568v1)
- PlankAssembly argues that classic back-projection is brittle to noisy or incomplete input and evaluates robustness with noisy and visible-only inputs. Hidden lines carry information that visible-only drawings lose. **[fetched]** — [arXiv 2308.05744](https://arxiv.org/abs/2308.05744); [project page](https://manycore-research.github.io/PlankAssembly/)

### Inferences
- What helps downstream reconstruction is (a) **known view convention** (first or third angle; which view is front, top or side), (b) **consistent known scale** (the same pixels-per-unit in every view, or dimensions, or a bounding box), and (c) **hidden-line information**. The add-on's orthographic front, top and side views already give (a). If they share a single ortho scale and log it in metadata (e.g. ortho_scale and pixels-per-mm), they give (b). They lack (c).
- For product photography and e-commerce, consistent ortho views with known scale are useful as a by-product of the add-on. Positioning it as a drawing-to-CAD data generator would require hidden lines and vector output to match what Ortho2CAD and PlankAssembly-style pipelines consume.

### Gaps
- I found no controlled study that isolates "consistent scale across views" (versus per-view auto-fit) as a factor in reconstruction accuracy. The CAD2Program annotation ablation is the closest evidence.
- No user-study evidence was found on demand from practitioners, as opposed to ML researchers, for auto-generated three-view drawings from meshes.

---

## Q4. Image-space edge detection vs geometric line extraction: what is needed for engineering-drawing-like output?

### Takeaway
Image-space detection (normal or depth discontinuities in a rendered buffer, which is what the add-on does) is fast and robust for **visible** silhouettes and creases. It has structural limits:
- no hidden lines;
- resolution-dependent, aliased raster lines;
- thresholds that depend on the view;
- no line identity or semantics for line weights;
- no clean vector output.

Engineering drawings need object-space extraction with **exact visibility (HLR)**, typed lines (visible solid, hidden dashed, optionally center and phantom lines), line weights, and **vector output (SVG/DXF)** at a known scale.

### Cited Findings
- The Bénard and Hertzmann tutorial frames contour drawing as two separate problems: **extraction** and **visibility**. It contrasts exact object-space methods with hardware-accelerated (image-space) fast methods and discusses their trade-offs. **[fetched, abstract]** — [arXiv 1810.01175](https://arxiv.org/abs/1810.01175)
- Blender Line Art computes occlusion levels per line segment. Level 0 gives visible lines and Level 1 gives lines hidden by exactly one layer of faces, with a range option. This is the geometric capability needed to draw hidden lines, for example on a separate dashed Grease Pencil layer. **[fetched, manual snippets]** — [Blender manual](https://docs.blender.org/manual/en/dev/grease_pencil/modifiers/generate/line_art.html)
- Freestyle can export SVG, but the stroke-to-path translation is lossy: "a one-on-one translation between Freestyle and SVG is not possible." **[fetched]** — [Blender 4.1 manual](https://docs.blender.org/manual/en/4.1/addons/render/render_freestyle_svg.html)
- CAD-side dataset generators produce engineering conventions directly from B-reps with OpenCascade/pythonOCC: first-angle projection, dashed hidden lines, dimensions. **[fetched]** — [Ortho2CAD](https://arxiv.org/abs/2607.08891). Other datasets ship vector formats: DXF in OrthoCAD-322K **[snippet]** ([PDF](https://ed.iitm.ac.in/~raman/agcl/OrthoCAD_322K_3DoR.pdf)) and SVG in the Zhang et al. Fusion 360-based set **[fetched]** ([Zenodo](https://zenodo.org/records/7785223)).
- Learned approaches (Neural Contours) combine geometric line features with image-based features. Purely image-based cues alone were not considered sufficient for high-quality drawings. **[fetched]** — [Neural Contours](https://arxiv.org/abs/2003.10333)

### Inferences
Requirements for an "engineering-drawing mode" in the add-on, ordered by value:
1. **Visibility-aware geometric lines.** Use Blender Line Art (Contour + Crease + Intersection + Material Border) with occlusion level 0 for visible lines and level 1..N for hidden lines, on two Grease Pencil layers styled solid and thick vs dashed and thin. Alternatively use Freestyle with QI (quantitative invisibility) line sets. This replaces or augments the matcap-threshold pass.
2. **Vector export.** SVG per view, or DXF. Use the Grease Pencil SVG export operator or the Freestyle SVG exporter, keeping visible and hidden lines in separate groups or layers with stroke-dasharray for hidden lines.
3. **A shared, recorded scale.** Use the same orthographic scale for front, top and side. Write a sidecar JSON with mm-per-pixel or mm-per-SVG-unit, the view convention (first vs third angle) and the bounding-box dimensions. This matches what Ortho2CAD and CAD2Program show is useful.
4. **Line weights:** thicker for silhouettes and outlines, thinner for creases and hidden lines, following drafting convention.
5. **Optional extras:** center lines for cylindrical features, and a crease-angle setting in degrees that matches Line Art's crease threshold.

Limitations to state honestly: mesh inputs (STL/OBJ product meshes) lack B-rep feature edges, so crease detection depends on the tessellation and an angle threshold. Smooth fillets produce no crease, or spurious ones, unlike exact CAD HLR. Pixel-based outputs remain fine for ML training data that is consumed as rasters (CAD2Program shows that raster encoders can match vector input).

### Gaps
- Not verified this session:
  - whether Blender's current Grease Pencil v3 (4.3+/5.x) SVG export preserves layers and dash styles;
  - whether Line Art occlusion works identically with orthographic cameras.
- No primary source was found that quantifies how accurate image-space crease detection is compared with geometric extraction on CAD-like meshes.
