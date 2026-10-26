# CAD / Engineering-Part Datasets and ML Work That Uses Rendered Images of CAD Models

Scope: how the CAD/engineering ML community gets images out of CAD (B-rep/STEP) data, what each dataset ships, and where a CAD-native multi-view renderer (STEP/IGES via FreeCAD, keeping part names and STEP colours, standardized views) would help. Research date: October 2026.

## 1. Datasets: formats, whether renders are provided, how renders were made, and whether names, colours and assembly structure survive

### Takeaway
Most major CAD datasets ship B-rep (STEP/Parasolid/SMT) and sometimes tessellated meshes, but **none of the classic CAD datasets ships a standardized, documented multi-view image set**. Where images exist, they are unspecified thumbnails or screen captures (Fusion 360 Gallery) or narrow, task-specific renders (FllumaOne's "visible-edge" views, Img2CAD's Blender renders). Assembly hierarchy, names and appearance survive mainly in Fusion 360 Gallery Assembly (JSON metadata) and AutoMate (Onshape assemblies). ABO, the product-imagery contrast case, is the only one with a fully documented Blender rendering protocol, PBR materials, canonical orientation and real-world scale, but it has artist meshes rather than CAD.

### Cited Findings

**ABC (Koch et al., CVPR 2019)**
- About 1 million CAD models, each "a collection of explicitly parametrized curves and surfaces", with ground truth for differential quantities, patch segmentation, feature detection and reconstruction. The abstract says sampling the parametric descriptions "allows generating data in different formats and resolutions." — [arXiv 1812.06216](https://arxiv.org/abs/1812.06216)
- Each chunk holds about 10k objects, packaged as separate 7z archives per file type: `step`, `para` (Parasolid), `obj`, `feat`, `stat`, `meta`, plus `ofs` and `stl2`. For chunk 0081 the archives run from about 1.1 GB (STEP) and 2.0 GB (Parasolid) to 5.6 GB (OBJ) and 8.7 GB (STL). Released under the MIT License, but "the copyright of these CAD models is owned by their creators", and the authors thank Onshape for providing the models. — [NYU FDA, ABC chunk 0081](https://archive.nyu.edu/jspui/handle/2451/44409?mode=simple); [NYU FDA, chunk 0002](https://archivefda.dlib.nyu.edu/handle/2451/44318)
- No rendered images appear among the listed chunk file types. — [NYU FDA chunk listing](https://archive.nyu.edu/jspui/handle/2451/44409?mode=simple)
- A 2026 Autodesk re-release, "ABC-1M" (Hugging Face ADSKAILab/ABC-1M), is listed as processed ABC solids with geometry and topology attributes and train/val/test splits. — [awesome-ai4cad survey list](https://github.com/gudo7208/awesome-ai4cad)

**Fusion 360 Gallery (Willis et al., SIGGRAPH 2021, plus follow-ups)**
- Sub-datasets: Assembly (8,251 assemblies, 154,468 parts), Assembly-Joint (32,148 joints, 23,029 parts), Reconstruction (8,625 sequences), Segmentation (35,680 parts; the extended set has 42,912 STEP files). Faces in the Segmentation set are labelled by modelling operation (Extrude, Fillet, Chamfer, and so on). — [Fusion360GalleryDataset repo](https://github.com/AutodeskAILab/Fusion360GalleryDataset)
- **Reconstruction** gives per design `.smt` (native Autodesk Shape Manager B-rep), `.step`, `.obj` (triangulated, each face a named group, "not manifold"), `.json` (construction sequence) and `.png`. The PNG is "a png screen capture of the design at this point in the sequence". The docs give no camera, lighting or resolution. Units are cm and radians. Entity names are mostly auto-generated ("Sketch1", "Body1") and "could also be in a localized version." The split is 6,900 train / 1,725 test. — [reconstruction.md](https://raw.githubusercontent.com/AutodeskAILab/Fusion360GalleryDataset/master/docs/reconstruction.md)
- **Assembly** gives `.smt`, `.step`, `.obj` (meshes "not guaranteed to be manifold"), JSON, and "a thumbnail .png image file together with each body and one for the overall assembly". The thumbnails' rendering method is not described. Bodies, components and occurrences carry `name`, and components carry `part_number`. Each body has a `material` (UUID and name, used for density and mass) and an `appearance` (UUID and name of the user-assigned appearance), **but no colour values are documented**. A `tree` holds the designer-defined hierarchy, and occurrences carry `transform`. All units are cm. — [assembly.md](https://raw.githubusercontent.com/AutodeskAILab/Fusion360GalleryDataset/master/docs/assembly.md)
- The repo's `tools/` directory holds Fusion 360 API tools for reconstruction, B-rep traversal and "conversion to other formats". No dedicated rendering pipeline is named. — [Fusion360GalleryDataset repo](https://github.com/AutodeskAILab/Fusion360GalleryDataset)

**DeepCAD (Wu et al., ICCV 2021)**
- `cad_json` holds construction sequences "parsed from Onshape public documents with links from [ABC dataset]". `cad_vec` holds vectorized sequences. Utilities include `export2step.py` (STEP export, with pythonocc-core 7.5.1 as a dependency), `json2pc.py` (point clouds) and `show.py`, which visualizes "with opencascade". The dataset ships no images. — [DeepCAD repo](https://github.com/ChrisWu1997/DeepCAD)

**SketchGraphs (Seff et al., ICML 2020 workshop)**
- "15 million sketches extracted from real-world CAD models" (Onshape), stored as geometric constraint graphs. Raw JSON is 128 zstd tar archives (about 43 GB), plus construction sequences in a custom binary file (15 GB) and filtered splits. The page mentions no rendered images and no 3D or B-rep geometry. — [SketchGraphs repo](https://github.com/PrincetonLIPS/SketchGraphs)

**MFCAD / MFCAD++ / Hierarchical CADNet**
- MFCAD is "a dataset of 3D CAD models with machining feature labels". The models sit in `dataset/step`, and the pythonocc-core scripts are for exploring and visualizing them. No images are provided. — [hducg/MFCAD](https://github.com/hducg/MFCAD)
- MFCAD++ succeeds MFCAD with more complex models and non-planar features: 24 machining feature classes plus stock, 3 to 10 features per model, stored in STEP (ISO 10303), generated with PythonOCC. Hierarchical CADNet learns directly from B-reps and was evaluated on it. — [Hierarchical CADNet, CAD journal (QUB PDF)](https://pure.qub.ac.uk/files/328098955/1_s2.0_S0010448522000240_main.pdf); [ScienceDirect](https://sciencedirect.com/science/article/pii/S0010448522000240?via=ihub%3D)

**CADNET (Manda, Bhaskare, Muthuganapathy, IEEE Access 2021)**
- 3,317 engineering models in 43 categories, collected from the Engineering Shape Benchmark (ESB) and the National Design Repository and augmented with newly modelled parts. The best classifier fed Light Field Descriptor-style **rendered images** into a ResNet-inspired CNN. This is an early example of a multi-view, image-based approach to classifying mechanical parts. — [arXiv 2107.06481](https://arxiv.org/abs/2107.06481v1); [ar5iv](https://ar5iv.labs.arxiv.org/html/2107.06481)

**MCB, the Mechanical Components Benchmark (Kim et al., ECCV 2020)**
- More than 58,000 annotated 3D mechanical parts. Dataset A aggregates TraceParts, 3D Warehouse and GrabCAD, and Dataset B aggregates 3D Warehouse and GrabCAD. TraceParts gave API access to its catalogue. The benchmark covers point-cloud, voxel and view-based (multi-view image) classifiers, and the authors stress "the significant difficulty of collecting 3D CAD models of mechanical components." — [Purdue project page](https://engineering.purdue.edu/cdesign/wp/a-large-scale-annotated-mechanical-components-benchmark-for-classification-and-retrieval-tasks-with-deep-neural-networks/); [TraceParts press release](https://info.traceparts.com/news/traceparts-news/traceparts-supported-purdue-university-for-their-mechanical-components-benchmark-mcb-research/); [ECCV page](https://www.ecva.net/papers/eccv_2020/papers_ECCV/html/2945_ECCV_2020_paper.php)

**AutoMate (Jones et al., SIGGRAPH Asia 2021): Onshape assemblies**
- Scraped from public Onshape documents via the Onshape API: 255,213 assemblies with mates, deduplicated with geometric "fingerprints" down to 92,529 unique assemblies. The Zenodo release has Parasolid and STEP (34.9 GB). Counts differ between versions: the paper text says 541,635 mates and its table says 514,635, while Dryad lists 451,967 parts, 255,211 assemblies and 1,292,016 mates. Duplicates were "a major problem". — [arXiv 2105.12238](https://arxiv.org/html/2105.12238v2); [Dryad](https://datadryad.org/dataset/doi:10.5061/dryad.2547d7wvw); [Zenodo](https://zenodo.org/records/7776208)

**Text2CAD (Khan et al., NeurIPS 2024 Spotlight)**
- About 170K DeepCAD models and about 660K text annotations. Annotation stage 1 renders **multi-view images of each individual part and of the final model** from "predetermined camera angles", and LLaVA-NeXT writes shape descriptions from them. Stage 2 has an LLM (Mistral) turn those descriptions into multi-level instructions. The paper names no renderer and gives no resolution or colours. — [arXiv 2409.17106 HTML](https://arxiv.org/html/2409.17106v1)

**CAD-MLLM / Omni-CAD (2024)**
- 453,220 models after augmentation, each with text, multi-view images, point clouds and command sequences. The authors claim it is "the only dataset ... that simultaneously supports multi-view images, text, and point cloud". The Hugging Face card defers image rendering to the GitHub code, and I could not confirm the render specifics. — [arXiv 2411.04954](https://arxiv.org/pdf/2411.04954); [HF dataset card](https://huggingface.co/datasets/jingwei-xu-00/Omni-CAD/discussions/1/files)

**CAD-Recode / cadrille (2025)**
- CAD-Recode has about 1 million procedurally generated CadQuery programs and is point-cloud only. cadrille adds images by tessellating the B-rep and rendering **4 fixed views tiled into a 2x2 grid of 268 x 268 px** for the Qwen vision encoder. It says it follows "established data generation protocols" and names no tool, lighting or colour. GT models are normalized to fit [-0.5, 0.5]^3. — [cadrille, arXiv 2505.22914](https://arxiv.org/html/2505.22914)

**Img2CAD (two different papers share this name)**
- Img2CAD (SIGGRAPH Asia 2025; arXiv 2408.01437) uses a VLM (GPT-4V in v1, Llama 3.2 later) to predict CAD command structure and the TrAssembler transformer for parameters. Its released dataset includes a `blender_renderings/` folder of PNGs. — [GitHub](https://github.com/qq456cvb/Img2CAD); [HF dataset](https://huggingface.co/datasets/qq456cvb/img2cad-dataset); [ACM](https://dl.acm.org/doi/10.1145/3757377.3763891)
- A different "Img2CAD" (IEEE journal) builds "ABC-mono", over 200K DeepCAD-derived models with **36 Blender views per model from random viewpoints**. — [ResearchGate](https://www.researchgate.net/publication/384680308_Img2CAD_Conditioned_3D_CAD_Model_Generation_from_Single_Image_with_Structured_Visual_Geometry)

**CADTalk (Yuan et al., CVPR 2024)**
- Benchmark of 5,288 machine-made and 45 human-made CAD programs with semantic comments. — [CVPR open access](https://openaccess.thecvf.com/content/CVPR2024/html/Yuan_CADTalk_An_Algorithm_and_Benchmark_for_Semantic_Commenting_of_CAD_CVPR_2024_paper.html)

**2026 datasets that ship renders**
- FllumaOne-100K (arXiv 2606.17696) has 100K kernel-validated samples from an OpenCASCADE-based CAD system. Each includes the program, feature tree, IR, STEP, point cloud, text, metadata and **"eight canonical visible-edge renderings"**. — [arXiv 2606.17696](https://arxiv.org/pdf/2606.17696)
- OmniMech (arXiv 2608.05539, Aug 2026) has more than 251,000 dimensioned and toleranced 2D drawings paired with native CAD, multi-view renderings, meshes, STEP and B-rep. The data is announced but its release is unconfirmed. — [alphaxiv 2608.05539](https://www.alphaxiv.org/abs/2608.05539)
- Also listed for 2026: STEP-Parts (arXiv 2604.14927, a STEP B-rep toolchain with instance labels for about 180K DeepCAD/ABC models), an ECCV 2026 CAD Challenge "renders and engineering views paired with STEP B-rep targets", and SldprtNet (arXiv 2603.13098, SolidWorks .sldprt-based language-to-CAD). — [awesome-ai4cad](https://github.com/gudo7208/awesome-ai4cad)

**ABO, Amazon Berkeley Objects (Collins et al., CVPR 2022): the product-imagery contrast**
- 147,702 listings, 398,212 catalogue images, and 8,222 products with 360-degree turntables of 24 or 72 frames. 7,953 artist-made glTF 2.0 models carry PBR materials (base colour, metallic, roughness). Models sit in "a canonical coordinate system where the 'front' (when well defined) ... are aligned", with "a scale corresponding to real world units". — [ar5iv 2110.06199](https://ar5iv.labs.arxiv.org/html/2110.06199); [AWS Marketplace](https://aws.amazon.com/marketplace/pp/prodview-ygocdgcstr7v2)
- Rendering is fully specified. Material estimation uses 512x512 renders from 91 cameras on an upper icosphere (60-degree FOV) in Blender Cycles, lit by 3 random HDRIs out of 108 indoor ones (2.1M images). Single-view reconstruction uses 30 Blender viewpoints (40-degree FOV) on a blank background. The ABO-MVR retrieval benchmark matches renders against real catalogue images, and Recall@1 is about 30% for rendered queries versus about 40% for catalogue queries. — [ar5iv 2110.06199](https://ar5iv.labs.arxiv.org/html/2110.06199)

**BOP industrial objects (T-LESS, ITODD)**
- The 7 core BOP datasets (LM-O, T-LESS, ITODD, HB, YCB-V, TUD-L, IC-BIN) come with about 350K photorealistic PBR training images generated and annotated with BlenderProc (BlenderProc4BOP). Objects are physics-dropped into a cube whose walls get random CC0 PBR materials. PBR training clearly beat "render & paste". — [BOP Challenge 2022 report](https://arxiv.org/pdf/2302.13075); [BlenderProc4BOP README](https://github.com/DLR-RM/BlenderProc/blob/main/README_BlenderProc4BOP.md); [BOP 2020](https://bop.felk.cvut.cz/challenges/bop-challenge-2020/)

### Inferences
- Across the classic CAD datasets (ABC, DeepCAD, SketchGraphs, MFCAD/MFCAD++, AutoMate), images are not a first-class modality. Every image-consuming paper therefore re-renders the data itself, with its own camera rig, resolution and lighting, and these are often undocumented (Text2CAD, cadrille). This is the clearest gap a standardized CAD-to-multi-view tool could fill.
- Fusion 360 Gallery Assembly is the only classic CAD dataset found that keeps part names, hierarchy, material and appearance names. Even there, its PNG thumbnails come with no documented rendering protocol, and appearance colours are given as names/UUIDs rather than RGB values.
- ABO shows what a well-specified render protocol looks like: documented camera rig, HDRI lighting, canonical front orientation and real-world scale. No CAD dataset matches it. A CAD-native renderer that brings ABO-style protocol discipline to STEP data would be a credible positioning.
- Semantic, colour-preserving renders of **assemblies** (each part distinguishable by name and colour) appear to be missing from all of these datasets.

### Gaps
- I could not open the ABC paper's full text (the CVF PDF returned 403 and the arXiv PDF came back as unreadable binary). The tool used to tessellate the OBJ/STL meshes (Onshape export or Open CASCADE) and any statement on units, colours or multi-body models are therefore unverified.
- I did not verify the exact model and class counts for MFCAD (original) and MCB, or MCB's distributed file format (likely meshes), from primary pages. The MCB PDF fetch failed on a certificate error.
- I did not verify the Fusion 360 Segmentation dataset's per-file contents (e.g. whether PNGs or `.seg` label files are included).
- I did not research CADParser or Traceparts-only industrial datasets beyond MCB's use of TraceParts.
- I could not confirm Omni-CAD's render details or ITODD-specific rendering details.

## 2. ML tasks that consume CAD renders, and the rendering setups they report

### Takeaway
Image/sketch-to-CAD, CAD VLM captioning, multi-view part classification and industrial sim-to-real detection all consume CAD renders. Rendering is usually a thin, bespoke pre-processing step: fixed 4 to 36 views, untextured or depth-only, often with no tool named. Several papers explicitly blame render quality for downstream errors: perspective distortion (Text2CAD), unrealistic untextured renders (CADTalk), and the need for material and texture randomization (SIP-17).

### Cited Findings
- **CAD captioning / VLM annotation.** Text2CAD renders each part and the final model from predetermined angles for LLaVA-NeXT. Its limitations section says LLaVA-NeXT "is sensitive to the perspective distortions in multi-view images", and these errors propagate into the generated prompts. — [Text2CAD HTML](https://arxiv.org/html/2409.17106v1)
- **Semantic part labelling of CAD programs.** CADTalk notes that untextured CAD renders look unrealistic to vision models trained on photos. It renders depth maps from **10 viewpoints** and passes them through ControlNet with the category name as the prompt, using 4 seeds per view (40 images per shape). It reports 83.24% accuracy. — [CADTalk arXiv](https://arxiv.org/pdf/2311.16703); [MSR page](https://www.microsoft.com/en-us/research/?p=1034136)
- **Image-to-CAD reconstruction.** cadrille uses 4 fixed views tiled 2x2 at 268 px total. CAD-MLLM, evaluated on Omni-CAD, reaches mean Chamfer Distance 18.5 from point clouds versus 37.7 from multi-view images, so image conditioning still lags. — [cadrille arXiv 2505.22914](https://arxiv.org/html/2505.22914)
- Img2CAD (SIGGRAPH Asia 2025) trains a VLM plus TrAssembler on Blender renderings. The other Img2CAD (ABC-mono) uses 36 random-view Blender renders per model. — [Img2CAD GitHub](https://github.com/qq456cvb/Img2CAD); [ABC-mono Img2CAD](https://www.researchgate.net/publication/384680308_Img2CAD_Conditioned_3D_CAD_Model_Generation_from_Single_Image_with_Structured_Visual_Geometry)
- FllumaOne provides 8 canonical visible-edge renderings per sample, and MIRAGE-CAD (arXiv 2608.28669) uses these "rendered views" as an input modality for generating CAD programs. — [FllumaOne](https://arxiv.org/pdf/2606.17696); [MIRAGE-CAD](https://arxiv.org/pdf/2608.28669)
- Newer 2026 image-to-CAD work listed in the survey includes OpenRealCAD (real photographs paired with editable CAD sequences, arXiv 2608.30617), GIFT (building image-to-CAD training data, arXiv 2603.27448), Ortho2CAD (arXiv 2607.08891) and VisCAD (arXiv 2609.03811). This shows image-to-CAD is an active and growing task. — [awesome-ai4cad](https://github.com/gudo7208/awesome-ai4cad)
- **Multi-view classification of mechanical parts.** MCB benchmarks view-based classifiers alongside point and voxel methods. CADNET's best result uses LFD rendered views with a CNN. — [MCB project page](https://engineering.purdue.edu/cdesign/wp/a-large-scale-annotated-mechanical-components-benchmark-for-classification-and-retrieval-tasks-with-deep-neural-networks/); [CADNET arXiv](https://arxiv.org/abs/2107.06481v1)
- **Cross-domain retrieval.** ABO-MVR matches rendered queries against real catalogue photos, and rendered queries do worse (about 30% vs about 40% R@1). — [ABO](https://ar5iv.labs.arxiv.org/html/2110.06199)
- **Industrial sim-to-real.** SIP-17 (CVPRW 2023) rendered 17 industrial parts and trained only on synthetic images, testing on 566 real photos. "Noisy" Syn_R (randomized backgrounds and post-processing) beat clean Syn_O, and performance dropped sharply on assemblies, which the authors say shows the need for material and texture randomization. — [arXiv 2404.08778](https://arxiv.org/pdf/2404.08778); [CVPRW](https://openaccess.thecvf.com/content/CVPR2023W/VISION/papers/Zhu_Towards_Sim-to-Real_Industrial_Parts_Classification_With_Synthetic_Dataset_CVPRW_2023_paper.pdf)
- For bin picking, Ojer et al. (2025) randomize lighting intensity, temperature and direction, plus material smoothness and reflectivity. Models trained only on virtual data perform comparably on real scenes. — [Ojer et al. 2025](https://doi.org/10.1177/17298806251374367)
- In BOP, BlenderProc PBR images drive state-of-the-art 6D pose results: 82.7 AR from GDRNPP trained on synthetic data only (2022). — [BOP 2022](https://arxiv.org/pdf/2302.13075)
- Metallic, reflective and low-contrast parts are the hardest to render convincingly, and published randomization setups are often tailored to one line, sensor and part taxonomy. — [roboticstomorrow 2026](https://www.roboticstomorrow.com/article/2026/03/how-bin-picking-ai-models-are-trained/26329); [MVPro Media](https://mvpromedia.com/from-cad-to-ai-how-synthetic-data-is-changing-machine-vision-training/)

### Inferences
- There are two distinct consumer communities. (a) **CAD-generation and VLM researchers** want clean, consistent, canonical multi-views (fixed orthographic or isometric rigs, edge renders, part-level renders) and suffer from perspective distortion and undocumented rigs. (b) **Industrial vision and robotics practitioners** want photorealistic, randomized renders (BlenderProc, Omniverse). A Blender add-on that does standardized multi-view sets with consistent lighting and camera presets sits closer to (a), while offering a Blender-native path toward (b).
- Text2CAD and CADTalk both render individual parts or semantic regions. A tool that keeps STEP part names and colours could produce per-part renders, per-part masks and name labels directly, which would supply ready-made ground truth for part-aware VLM captioning and segmentation.
- Orthographic or fixed-FOV standardized views would directly address the perspective-distortion failure mode that Text2CAD reports.

### Gaps
- Most image-to-CAD papers I checked (Text2CAD, cadrille, Omni-CAD) do not name their renderer. I could not determine whether pythonOCC, Open3D, PyVista or Blender is the dominant choice.
- I did not find ITODD-specific rendering details beyond its BOP/BlenderProc inclusion.

## 3. Pain points: STEP-to-mesh at scale, loss of colours and part structure, units and scale, orientation

### Takeaway
Pipelines from STEP to images routinely lose appearance and structure. Colours and names survive only along the OCCT XCAF path, and common exporters can flatten them. Datasets mix units (Fusion is cm, ABO uses real-world scale), meshes are often non-manifold, and duplicates and orientation are handled ad hoc: methods typically just rescale into a unit cube.

### Cited Findings
- Keeping colours and names from STEP in OpenCASCADE requires the XCAF reader (`STEPCAFControl_Reader` with colour and name modes on). An OCC forum thread covers keeping STEP colours when geometry is modified. — [OCC forum](https://dev.opencascade.org/content/preserving-colours-step-file-when-modifying-geometry-open-cascade)
- One converter vendor says it preserves per-face colours by writing glTF with `RWGltf_CafWriter` after tessellating with `BRepMesh_IncrementalMesh`, and claims CadQuery's and KiCad's glTF/GLB exports collapse to all-white. This is a single vendor's wiki and should be treated as a lead, not verified fact. — [Adom Step2GLB](https://wiki.adom.inc/adom/adom-step2glb/files/README.md); contrast [CadQuery import/export docs](https://cadquery.readthedocs.io/en/stable/importexport.html), which show coloured assembly export
- build123d writes colours and names into XCAF labels before export and exposes linear and angular deflection settings for tessellating glTF. This shows that tessellation quality is a user-chosen parameter that varies between pipelines. — [build123d exporters3d](https://build123d.readthedocs.io/en/latest/_modules/exporters3d.html)
- Fusion 360 Gallery OBJ meshes are "not manifold" or "not guaranteed to be manifold". Units are cm, and names can be auto-generated or localized. — [reconstruction.md](https://raw.githubusercontent.com/AutodeskAILab/Fusion360GalleryDataset/master/docs/reconstruction.md); [assembly.md](https://raw.githubusercontent.com/AutodeskAILab/Fusion360GalleryDataset/master/docs/assembly.md)
- ABC distributes STEP, Parasolid, OBJ and STL side by side, and a single chunk of about 10k models takes about 1.1 GB as STEP versus about 8.7 GB as STL. Pre-tessellated meshes therefore cost about 8x the storage of the B-rep. — [NYU FDA chunk 0081](https://archive.nyu.edu/jspui/handle/2451/44409?mode=simple)
- Duplicates: AutoMate went from 255,213 scraped assemblies to 92,529 unique ones using geometric fingerprints. — [AutoMate](https://arxiv.org/html/2105.12238v2)
- Scale normalization is ad hoc. cadrille normalizes ground truth into [-0.5, 0.5]^3, whereas ABO keeps real-world units and a canonical front-facing orientation. — [cadrille](https://arxiv.org/html/2505.22914); [ABO](https://ar5iv.labs.arxiv.org/html/2110.06199)
- MCB's authors cite "the significant difficulty of collecting 3D CAD models of mechanical components" as the main barrier to building such datasets. — [MCB project page](https://engineering.purdue.edu/cdesign/wp/a-large-scale-annotated-mechanical-components-benchmark-for-classification-and-retrieval-tasks-with-deep-neural-networks/)
- FllumaOne keeps samples only after geometry, solid-validity and export checks, which implies that export and validity failures are common enough to need filtering. — [FllumaOne](https://arxiv.org/pdf/2606.17696)

### Inferences
- A FreeCAD-based importer that reads STEP colours and part names (FreeCAD's import is built on OCCT) and maps them to Blender objects and materials covers exactly the step where colour and structure are most often lost. Its documentation should state the tessellation deflection used and the unit handling (STEP mm vs Fusion cm), since nothing else standardizes them.
- Canonical orientation of mechanical parts (unlike ABO's "front" for products) is unsolved in these datasets. An "orient products" step (e.g. a PCA- or bounding-box-based canonical pose plus fixed view presets) is a differentiator, provided it is documented.

### Gaps
- I found no systematic study quantifying STEP tessellation failure rates or colour-loss rates at dataset scale.
- I did not verify FreeCAD-specific colour import behaviour from a primary source in this research thread.
- I found no primary source on standard practice for orienting CAD parts in ML datasets, beyond unit-cube normalization.

## 4. Existing tools for rendering CAD datasets

### Takeaway
There is no widely adopted, CAD-native, standardized multi-view rendering tool for engineering datasets. Practice is fragmented. Dataset repos ship OpenCASCADE/pythonOCC viewers (DeepCAD, MFCAD), Fusion 360 API scripts, or ad hoc Blender scripts (Img2CAD). BlenderProc is the standard for photoreal industrial training data but takes meshes (PLY/OBJ), not STEP, and ignores CAD part semantics. Newer agentic CAD tools (build123d/CadQuery/FreeCAD MCP servers) render for LLM feedback, not for dataset generation.

### Cited Findings
- DeepCAD visualizes "with opencascade" (`show.py`) and exports STEP via pythonocc-core. — [DeepCAD repo](https://github.com/ChrisWu1997/DeepCAD)
- MFCAD ships pythonocc-core scripts in `occ/` for exploring and visualizing the STEP models. — [MFCAD repo](https://github.com/hducg/MFCAD)
- Fusion 360 Gallery ships Fusion 360 API-based tools for reconstruction, B-rep traversal and format conversion. These need a Fusion 360 installation, and the repo names no dedicated renderer. — [Fusion360GalleryDataset](https://github.com/AutodeskAILab/Fusion360GalleryDataset)
- Img2CAD ships Blender renderings as data (`blender_renderings/`). — [Img2CAD HF dataset](https://huggingface.co/datasets/qq456cvb/img2cad-dataset)
- BlenderProc4BOP is the de facto photoreal synthetic-data renderer for the BOP industrial-object benchmarks, built on Blender Cycles. — [BlenderProc4BOP README](https://github.com/DLR-RM/BlenderProc/blob/main/README_BlenderProc4BOP.md)
- On the commercial side, NVIDIA Omniverse Replicator and Isaac Sim offer domain-randomized synthetic data, and MVTec describes CAD-generated training data for 3D matching in bin picking. — [MVPro Media](https://mvpromedia.com/from-cad-to-ai-how-synthetic-data-is-changing-machine-vision-training/)
- Onshape's API was the access route for ABC, AutoMate and DeepCAD (scraping public documents), but none of these datasets documents using Onshape-rendered images. — [AutoMate](https://arxiv.org/html/2105.12238v2); [DeepCAD](https://github.com/ChrisWu1997/DeepCAD)
- 2025-2026 agentic CAD tools listed in the awesome-ai4cad survey include build123d-mcp ("rendering; STEP, STL, SVG, DXF export"), agentcad, text-to-cad (STEP/GLB/STL/3MF), CadQuery MCP servers, FreeCAD MCP servers and the Onshape FeatureScript MCP Server. These render as feedback for LLM agents, not as standardized dataset image sets. — [awesome-ai4cad](https://github.com/gudo7208/awesome-ai4cad)
- A commercial Blender STEP import/export add-on (Stepio) exists, which shows STEP-in-Blender is a recognized need in the Blender ecosystem. — [Stepio docs](https://superhivemarket.com/products/stepio---blender-step-import--export-add-on/docs)

### Inferences
- **Positioning:** The add-on would sit at the intersection that no existing tool covers. It reads STEP/IGES natively (via FreeCAD/OCCT), keeps part names and STEP colours, and outputs standardized, documented multi-view sets (fixed camera rigs, lighting and orientation) inside Blender. Blender then provides the path to photoreal and BlenderProc-style randomization when needed.
- **Concrete value propositions**, each tied to a gap found above:
  1. A reproducible, documented render protocol, which Text2CAD, cadrille and Omni-CAD lack. Ideally it would offer ABO-style metadata: camera intrinsics and extrinsics, lighting, resolution.
  2. Orthographic or low-distortion presets, addressing Text2CAD's perspective-distortion failures.
  3. Per-part renders, masks and name labels from STEP assembly structure, for part-aware VLM captioning (Text2CAD part renders, CADTalk semantics) and industrial assembly recognition (SIP-17's assembly drop).
  4. Colour fidelity from STEP, a step where common glTF pipelines reportedly lose colour.
  5. Explicit unit and scale handling plus canonical orientation, given the cm/mm/unit-cube inconsistency across datasets.
- **Likely competitive objections:** BlenderProc already exists for photoreal work, pythonOCC/OCP offscreen rendering is scriptable at scale without Blender, and large datasets (ABC: 1M models) need headless batch throughput. The add-on's case is strongest on semantic fidelity (names, colours, assemblies) and protocol standardization, not raw throughput.

### Gaps
- I found no primary source describing an Onshape API "shaded views" rendering pipeline used for an ML dataset.
- I did not check whether any open-source pythonOCC or OCP batch multi-view renderer for ML datasets is widely used; none surfaced in the searches.
- I did not verify the throughput of Blender-based or FreeCAD-based conversion at ABC scale.
