# Synthetic data and procedural rendering pipelines: what they cover, for positioning MultiView Product Renderer

Scope: BlenderProc/BlenderProc2, Kubric, NVIDIA Omniverse Replicator (Isaac Sim), Unity Perception, Infinigen, BlenderSynth, Render for CNN (Su et al. 2015). Researched October 2026. Primary sources were GitHub READMEs, official docs, arXiv and JOSS pages, and NVIDIA forums.

## Q1. For each tool: inputs (STEP/CAD or mesh only), outputs and annotations, how it is driven, license, intended users

### Takeaway
Every tool here is a code-first or config-first generator of ML training data. They output dense ground truth (depth, normals, instance/semantic segmentation, flow) and machine-readable annotations (COCO, BOP, camera K matrices, poses). None of the Blender-based tools documents native STEP/IGES import; they all load meshes. Only NVIDIA Isaac Sim/Omniverse ships a CAD-to-USD converter, and users report frequent STEP import failures with it. Unity Perception is discontinued. Kubric is pinned to Blender 2.93.

### Cited Findings

**BlenderProc / BlenderProc2 (DLR-RM)**
- License: GPL-3.0. — [BlenderProc GitHub](https://github.com/DLR-RM/BlenderProc)
- Inputs: the README lists "Loading: `*.obj`, `*.ply`, `*.blend`, `*.fbx`, BOP, ShapeNet, Haven, 3D-FRONT, etc." It does not mention STEP, IGES or any other B-rep CAD format. — [BlenderProc GitHub](https://github.com/DLR-RM/BlenderProc)
- Outputs: RGB, stereo, depth, normal and segmentation images or sequences. Writers produce ".hdf5 containers, COCO & BOP annotations". — [BlenderProc GitHub](https://github.com/DLR-RM/BlenderProc)
- The docs list examples for optical flow, NOCS, semantic segmentation, diffuse color images, COCO annotations ("Write COCO annotations to a .json file for selected objects in the scene") and BOP Challenge data ("Generate the pose-annotated data used at the BOP Challenge 2020"). — [BlenderProc docs](https://dlr-rm.github.io/BlenderProc/)
- Cameras: "Set, sample or load camera poses from file". Examples include sampling camera positions inside a shape with rotation constraints. The API call is `bproc.camera.add_camera_pose(cam_pose)`. — [BlenderProc GitHub](https://github.com/DLR-RM/BlenderProc); [BlenderProc docs](https://dlr-rm.github.io/BlenderProc/)
- Driven by Python scripts through a CLI: `blenderproc run <script>`. It runs inside Blender's Python environment. `blenderproc debug quickstart.py` opens the Blender UI with the script loaded in the Scripting tab, which is a debugging aid, not a no-code GUI. `blenderproc vis hdf5` visualizes output. — [BlenderProc GitHub](https://github.com/DLR-RM/BlenderProc); [BlenderProc docs](https://dlr-rm.github.io/BlenderProc/)
- No scale or unit normalization for loaded objects is documented on the docs landing page. — [BlenderProc docs](https://dlr-rm.github.io/BlenderProc/)

**Kubric (Google Research)**
- License: Apache-2.0. Built on PyBullet (physics) and Blender 2.93 (rendering). The Blender version is pinned, so opening generated `.blend` files requires that version. — [Kubric GitHub](https://github.com/google-research/kubric)
- Driven by Python scripts (e.g. `examples/helloworld.py`) run inside the `kubricdockerhub/kubruntu` Docker image. — [Kubric GitHub](https://github.com/google-research/kubric)
- Outputs in the MOVi datasets:
  - Per-frame: "video" (RGB), "segmentations" (per-pixel object IDs), "depth", "normal" (world-coordinate normals), "object_coordinates", "forward_flow" and "backward_flow".
  - Camera metadata: "focal_length", "sensor_width", "field_of_view", "positions", "quaternions" and the intrinsic matrix "K".
  - Per-instance metadata: positions, quaternions, velocities, "bboxes", "bboxes_3d", "visibility" and collision events.
  
  — [Kubric MOVi README](https://github.com/google-research/kubric/blob/main/challenges/movi/README.md)
- Asset sources: KuBasic (simple CLEVR-like shapes), Google Scanned Objects (GSO), and Poly Haven HDRIs for background and lighting. — [Kubric MOVi README](https://github.com/google-research/kubric/blob/main/challenges/movi/README.md)
- Intended use: "cheap", richly annotated, controllable synthetic data. It is demonstrated with "13 different generated datasets for tasks ranging from studying 3D NeRF models to optical flow estimation", and it scales to thousands of machines and terabytes of data. — [Kubric arXiv 2203.03570](https://arxiv.org/abs/2203.03570)

**NVIDIA Omniverse Replicator / Isaac Sim**
- Replicator is a set of extensions. omni.syntheticdata passes renderer AOVs to annotators. The visualizer shows "2D/3D bounding boxes, normals, depth and more". Writers emit DNN-specific formats to local or cloud storage. The workflow is: randomize the scene, select annotators, write output. — [Omniverse Replicator docs](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html)
- Registry annotators include `camera_params`/CameraParams, `normals`, `distance_to_image_plane`, `distance_to_camera` and `instance_segmentation`/`instance_id_segmentation`. Annotators are accessed via `omni.replicator.core.annotators.get()`. — [Replicator annotators (v1.12.16)](https://docs.omniverse.nvidia.com/py/replicator/1.12.16/source/extensions/omni.replicator.core/docs/annotators_details.html)
- OmniGraph nodes include Bounding Box 2D/3D, Camera Params, Instance/Semantic Segmentation, Get Pointcloud and Get Skeleton Data. — [Replicator Python API](https://docs.omniverse.nvidia.com/py/replicator/latest/source/extensions/omni.replicator.core/docs/API.html)
- Ways to drive it:
  - Python API.
  - Replicator YAML config, converted to OmniGraph.
  - GUI Synthetic Data Recorder (Tools > Replicator), whose default writer is `BasicWriter` and which is meant for "quick test recordings".
  - GUI Semantics Schema Editor for labelling prims.
  
  — [Isaac Sim Replicator overview](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_overview.html); [Omniverse Replicator docs](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html)
- Isaac Sim license:
  - The GitHub repo shows an Apache 2.0 badge.
  - First run requires accepting the "Omniverse Licensing Terms", and the build downloads the Kit SDK from NVIDIA.
  - It requires Windows 11 or Ubuntu 22.04/24.04 and an RTX-class GPU.
  - It imports "URDF, MJCF, and CAD".
  
  — [Isaac Sim GitHub](https://github.com/isaac-sim/IsaacSim)
- CAD import: the `omni.kit.converter.cad` extension suite ships with Kit SDK and Isaac Sim and imports via the File menu. — [Omniverse CAD Converter docs](https://docs.omniverse.nvidia.com/kit/docs/omni.kit.converter.cad/207.0.3/Overview.html) (from a search snippet; the page returned 403 when fetched)

**Unity Perception**
- Status: "This project has been discontinued and is no longer supported by Unity." — [Unity Perception GitHub](https://github.com/Unity-Technologies/com.unity.perception)
- License: Apache 2.0. — [Unity Perception GitHub](https://github.com/Unity-Technologies/com.unity.perception)
- Features:
  - Labeling of GameObjects, Perception Camera, a Randomization framework, and accumulation/path tracing.
  - Outputs include 2D/3D bounding boxes, instance/semantic segmentation, keypoints and COCO pose labels.
  - Output endpoints are SOLO (default), Perception, or none. COCO comes from converting SOLO with pysolotools.
  - The README does not mention depth or normals.
  
  — [Unity Perception GitHub](https://github.com/Unity-Technologies/com.unity.perception)
- Driven through the Unity Editor (editor components plus C#), with Python (pysolotools) for analysis. It is an "easy-to-use and highly customizable toolset" with an "extensible Randomization framework". — [Unity Perception arXiv 2107.04259](https://arxiv.org/abs/2107.04259)

**Infinigen (Princeton VL)**
- License: BSD-3-Clause. — [Infinigen GitHub](https://github.com/princeton-vl/infinigen)
- Generates procedural photorealistic scenes. Variants are Infinigen Nature, Infinigen Indoors and Infinigen Articulated (articulated simulation assets). — [Infinigen GitHub](https://github.com/princeton-vl/infinigen)
- Ground-truth outputs shown: RGB, depth, surface normals, instance segmentation, plus a separate "Extended ground-truth" doc. — [Infinigen GitHub](https://github.com/princeton-vl/infinigen)
- Driven by config files, the CLI (`manage_jobs`) and Python procedural generators. It installs via uv or Docker. — [Infinigen GitHub](https://github.com/princeton-vl/infinigen)
- External assets: there is an "Add external assets to indoor scenes" doc and OBJ/OpenUSD export. Importing user CAD is not a documented focus. — [Infinigen GitHub](https://github.com/princeton-vl/infinigen)

**BlenderSynth (Ollie Boyne)**
- Python library on PyPI (`blendersynth`) for large-scale synthetic datasets in Blender 3 and 4. MIT license, Beta status. — [BlenderSynth GitHub](https://github.com/OllieBoyne/BlenderSynth)
- Features: custom shader AOVs, node control, multithreading, "multiview rendering", and depth/normal outputs. It includes a rendering-speed comparison against BlenderProc. — [BlenderSynth GitHub](https://github.com/OllieBoyne/BlenderSynth)
- Used in research projects such as FOUND, FOCUS (synthetic feet) and Sim4D (4D SLAM). — [BlenderSynth GitHub](https://github.com/OllieBoyne/BlenderSynth)

**Render for CNN (Su, Qi, Li, Guibas, ICCV 2015)**
- Pipeline:
  - ShapeNet models are rendered in Blender (2.71 tested), about 2.4M images in roughly 8 hours on six servers.
  - Viewpoint and truncation distributions are estimated by kernel density estimation in MATLAB 2014b, then sampled.
  - Renders are cropped and composited onto SUN2012 backgrounds.
  - Filenames encode class, azimuth, elevation and tilt.
  - A Caffe viewpoint estimator is included.
  - MIT license; 247 stars; no releases.
  
  — [RenderForCNN GitHub](https://github.com/ShapeNet/RenderForCNN)

### Inferences
- Across the field, the inputs are meshes or dataset formats (OBJ/PLY/FBX/blend, ShapeNet, GSO, BOP) or USD. Only Omniverse provides a STEP/CAD path, and it is tied to RTX hardware and a heavyweight Kit install. A Blender add-on that imports STEP/IGES through FreeCAD with part names and colours fills a real gap among the Blender-based tools.
- MultiView Product Renderer's absent outputs (depth, normals, segmentation, camera K/extrinsics, COCO/BOP) are exactly the core of BlenderProc, Kubric and Replicator. Positioning should not claim ML-dataset parity. Adding depth, normal and index passes plus a camera-intrinsics/extrinsics JSON would be cheap in Blender and would close most of the annotation gap.
- None of these tools is no-code. Replicator's Synthetic Data Recorder and Unity's Editor are partial GUIs, but they still need scene setup, labelling and scripting for randomization.

### Gaps
- No exact supported-format list for the Omniverse CAD Converter (STEP/IGES/JT etc.): the docs page returned HTTP 403.
- No complete, current list of Replicator writers (KittiWriter, COCO, pose writers) from a primary page in this session. Only BasicWriter is confirmed.
- Kubric's maintenance status is not stated in its README. The only evidence is the Blender 2.93 pin and 70 open issues.
- BlenderSynth's input formats and lighting features are not documented on its README.

## Q2. Do any offer standardized product-style multi-view rigs, consistent framing, line-art/technical-drawing output, or studio lighting presets?

### Takeaway
None of the reviewed tools documents fixed canonical orthographic views (front/top/side/iso) or a shared-framing rig that keeps scale consistent across objects. None offers line-art or technical-drawing output or named studio lighting presets. Their camera models are designed for sampling and randomization, not for catalog-style standardization.

### Cited Findings
- BlenderProc's camera features are "Set, sample or load camera poses from file", plus constrained sampling inside a shape. Fixed canonical views are not a listed feature. — [BlenderProc GitHub](https://github.com/DLR-RM/BlenderProc)
- Render for CNN samples viewpoints (azimuth, elevation, tilt) and truncation from KDE-estimated distributions fitted to real-image statistics. This is randomized, not canonical, viewpoint coverage. — [RenderForCNN GitHub](https://github.com/ShapeNet/RenderForCNN)
- Kubric's MOVi lighting and backgrounds come from random Poly Haven HDRIs, and camera parameters are recorded per frame. This is randomized environment lighting, not studio presets. — [Kubric MOVi README](https://github.com/google-research/kubric/blob/main/challenges/movi/README.md)
- Replicator's workflow is built around "randomize the scene" before annotation. — [Omniverse Replicator docs](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html)
- Unity Perception's distinguishing feature is its "extensible Randomization framework". — [Unity Perception arXiv 2107.04259](https://arxiv.org/abs/2107.04259)
- BlenderSynth advertises "multiview rendering" but documents no rig standard or lighting features. — [BlenderSynth GitHub](https://github.com/OllieBoyne/BlenderSynth)
- The listed outputs contain no line-art or Freestyle output: BlenderProc (RGB, depth, normal, segmentation, flow, NOCS, diffuse) and Kubric (RGB, segmentation, depth, normal, object coordinates, flow). — [BlenderProc GitHub](https://github.com/DLR-RM/BlenderProc); [Kubric MOVi README](https://github.com/google-research/kubric/blob/main/challenges/movi/README.md)

### Inferences
- These are the add-on's clearest differentiators against this class of tools:
  - Canonical ortho plus perspective rigs with framing shared across a product set.
  - Camera-following studio lighting.
  - Clay, line-art and AO passes.
  - Contact sheets and turntables.
  
  Synthetic-data pipelines optimize for distribution coverage (domain randomization). This add-on optimizes for comparability and presentation consistency.
- In principle, all of these behaviours could be scripted in BlenderProc or BlenderSynth. The gap is that they are neither provided out of the box nor exposed without code.

### Gaps
- Absence claims rest on READMEs and doc landing pages, not on a full API audit. A BlenderProc or Replicator example of fixed orthographic views may exist without being advertised.
- Did not check product-visualization or e-commerce tools (KeyShot, Omniverse product configurator samples). They are outside this scope but are likely closer competitors for the "studio" side.

## Q3. Known pain points: setup complexity, programming required, CAD import, scale handling

### Takeaway
Reported pain points cluster around:
- Programming and environment setup: Blender's Python environment, Docker, pinned Blender versions, MATLAB/Caffe for legacy tools.
- Heavy runtimes: RTX GPUs and Kit/Omniverse licensing.
- CAD import fragility: Isaac Sim STEP import breaks across versions and install types, and Blender STEP importers need OpenCascade.
- Unit and scale mismatches when moving from CAD (mm) to Blender (m).

### Cited Findings
- BlenderProc "has to be run inside the blender python environment". Usage is a Python script via the CLI. — [BlenderProc GitHub](https://github.com/DLR-RM/BlenderProc)
- Kubric runs via the Docker image `kubruntu` and is pinned to Blender 2.93. — [Kubric GitHub](https://github.com/google-research/kubric)
- Render for CNN dependencies:
  - Blender 2.71.
  - MATLAB 2014b with a separately compiled KDE package.
  - A custom Caffe fork (caffe-render-for-cnn).
  - Tested only on 64-bit Linux.
  
  — [RenderForCNN GitHub](https://github.com/ShapeNet/RenderForCNN)
- Isaac Sim requires an RTX-class GPU, specific OS versions and GCC 11 on Ubuntu 24.04. It also needs internet access during the build and acceptance of the Omniverse Licensing Terms. — [Isaac Sim GitHub](https://github.com/isaac-sim/IsaacSim)
- Isaac Sim STEP import failures (forum threads):
  - Isaac Sim 4.2.0: NVIDIA staff reproduced a STEP import failure. The suggested fix was to disable the CAD converter extensions and install matching versions (201.2.1 / 500.0.26).
  - Isaac Sim 5.1 pip install on Windows: STEP import fails because the HOOPS subprocess cannot find kit\python.
  - Other threads: "STEP format not available" in the Isaac Sim CAD importer, and "Failed to Import STEP File".
  
  — [NVIDIA forum 4.2.0](https://forums.developer.nvidia.com/t/import-issue-not-able-to-import-step-file-using-isaac-sim-4-2-0/310803); [NVIDIA forum 5.1 pip](https://forums.developer.nvidia.com/t/isaac-sim-5-1-windows-pip-step-import-fails-because-hoops-subprocess-cannot-find-kit-python/378494); [NVIDIA forum STEP not available](https://forums.developer.nvidia.com/t/step-format-not-available-in-omniverse-isaac-sim-cad-importer/226306); [NVIDIA forum failed STEP](https://forums.developer.nvidia.com/t/failed-to-import-step-file/328977)
- Blender STEP import in general (not BlenderProc-specific):
  - Free options need a manual pip install of OpenCascade bindings or produce broken meshes.
  - Large STEP files load only partially.
  - CAD mm units require a 0.001 scale fix.
  
  — [Blender Artists: new STEP importer](https://blenderartists.org/t/new-step-importer-native-cad-import-for-blender-4-2/1641518); [Blender Artists STEP import thread](https://blenderartists.org/t/step-import/1203804)
- Unity Perception is discontinued, so users are left with no vendor support. — [Unity Perception GitHub](https://github.com/Unity-Technologies/com.unity.perception)

### Inferences
- The add-on's no-code panel, FreeCAD-based STEP/IGES import, and automatic scale/centre/orientation standardization directly address the most commonly reported friction points. The evidence for the CAD and scale problems comes from the Omniverse forums and the Blender community, not from BlenderProc or Kubric issue trackers.

### Gaps
- Did not search the BlenderProc or Kubric GitHub issue trackers for specific CAD or scale complaints. The web search for "BlenderProc STEP" returned only generic Blender STEP threads, which suggests STEP is simply out of scope for BlenderProc rather than a reported bug.
- No quantitative usability studies (e.g. setup time) were found for any of these tools.

## Q4. Publications: exact citations, venues, citation counts

### Takeaway
BlenderProc2 (JOSS 2023, plus arXiv 2019), Kubric (CVPR 2022), Infinigen (CVPR 2023) and Infinigen Indoors (CVPR 2024), Unity Perception (arXiv 2021, no peer-reviewed venue found) and Render for CNN (ICCV 2015) are all published. Replicator and BlenderSynth have no dedicated paper found. Citation counts could not be retrieved because the Semantic Scholar API was rate-limited.

### Cited Findings
- **BlenderProc2:** Denninger, M., Winkelbauer, D., Sundermeyer, M., Boerdijk, W., Knauer, M., Strobl, K. H., Humt, M., & Triebel, R. (2023). "BlenderProc2: A Procedural Pipeline for Photorealistic Rendering." *Journal of Open Source Software*, 8(82), 4901. https://doi.org/10.21105/joss.04901 — [JOSS](https://joss.theoj.org/papers/10.21105/joss.04901)
- **BlenderProc (2019):** the earlier arXiv paper is linked from the README. — [arXiv 1911.01911](https://arxiv.org/abs/1911.01911) via [BlenderProc GitHub](https://github.com/DLR-RM/BlenderProc)
- **Kubric:** Greff, K., et al. (34 authors, last author Tagliasacchi, A.) (2022). "Kubric: A Scalable Dataset Generator." *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*. arXiv:2203.03570. — [arXiv](https://arxiv.org/abs/2203.03570); [Kubric GitHub](https://github.com/google-research/kubric)
- **Infinigen:** Raistrick, A., et al. "Infinite Photorealistic Worlds using Procedural Generation." CVPR 2023. — [Infinigen GitHub](https://github.com/princeton-vl/infinigen)
- **Infinigen Indoors:** Raistrick, A., et al. "Infinigen Indoors: Photorealistic Indoor Scenes using Procedural Generation." CVPR 2024. — [Infinigen GitHub](https://github.com/princeton-vl/infinigen)
- **Infinigen-Articulated:** Joshi, A., et al. "Infinigen-Articulated: Procedural Generation of Articulated Simulation Assets." arXiv 2505.10755 (2025). The README also lists ProcFunc, arXiv 2604.26943 (2026). — [Infinigen GitHub](https://github.com/princeton-vl/infinigen)
- **Unity Perception:** Borkman, S., et al. (15 authors) (2021). "Unity Perception: Generate Synthetic Data for Computer Vision." arXiv:2107.04259. The repo itself suggests citing it as a `@misc` "Unity Perception Package". — [arXiv](https://arxiv.org/abs/2107.04259); [Unity Perception GitHub](https://github.com/Unity-Technologies/com.unity.perception)
- **Render for CNN:** Su, H., Qi, C. R., Li, Y., & Guibas, L. J. (2015). "Render for CNN: Viewpoint Estimation in Images Using CNNs Trained with Rendered 3D Model Views." *IEEE International Conference on Computer Vision (ICCV)*, December 2015. arXiv:1505.05641. — [RenderForCNN GitHub](https://github.com/ShapeNet/RenderForCNN)
- **NVIDIA Replicator:** documented as Omniverse extensions with no standalone paper cited in the docs. — [Omniverse Replicator docs](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html)
- **BlenderSynth:** no paper is listed on the README. It is cited through the projects that use it (FOUND, FOCUS, Sim4D). — [BlenderSynth GitHub](https://github.com/OllieBoyne/BlenderSynth)

### Inferences
- For a JOSS-style or workshop paper on the add-on, BlenderProc2 (JOSS 2023) is the closest precedent in venue and genre: open-source Blender tooling published in JOSS. Kubric and Infinigen set the bar for CVPR-level dataset-generator papers.

### Gaps
- No citation counts: the Semantic Scholar API returned HTTP 429, and no other source was queried. Get them from Google Scholar or Semantic Scholar before quoting.
- Page numbers for the Kubric, Infinigen and Render for CNN proceedings were not retrieved. The arXiv IDs are given instead.
- Did not verify whether Unity Perception was ever published at a peer-reviewed venue. Only arXiv was found.
