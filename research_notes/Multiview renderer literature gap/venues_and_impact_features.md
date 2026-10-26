# Publication Venues and High-Impact Features for "MultiView Product Renderer" (Blender add-on)

Notes compiled 2026-10-26. Primary sources were fetched directly where possible. Where a page blocked fetching (ScienceDirect/ASME returned 403), that is stated and the claim is marked as coming from a secondary source or moved to Gaps.

---

## Q1. JOSS (Journal of Open Source Software): review criteria, paper length, eligibility, precedents

### Takeaway
JOSS fits the tool's format best: a 750-1750-word paper, no fees, and a reviewer checklist. Its 2026 rules add hard gates the add-on may not yet meet. The repository must have been public for more than 6 months with ongoing development, there must be evidence of actual research use ("aspirational statements about future use are not sufficient"), and the paper must include a "Research impact statement" and an "AI usage disclosure". Automated tests in CI are rated "Good". Documented manual test steps are only "OK".

### Cited Findings
- Software must be OSI open source, in a repository that can be cloned without registration, with a public issue tracker that anyone can file issues against. — [JOSS submitting](https://joss.readthedocs.io/en/latest/submitting.html)
- Software "should be full-featured, well-documented, and contain procedures (such as automated tests) for checking correctness" and be "packaged appropriately according to common community standards for the programming language being used." — [JOSS submitting](https://joss.readthedocs.io/en/latest/submitting.html)
- Research-impact gate: "JOSS publishes articles about software that has demonstrated clear research impact"; "There must be evidence that the software is being used for research"; "Aspirational statements about future use are not sufficient." — [JOSS submitting](https://joss.readthedocs.io/en/latest/submitting.html)
- Open-development gate: "The repository must have been public for more than six months prior to submission"; "The development history must show ongoing iteration, not a single burst of commits"; projects developed privately "are not eligible until there is a public record of open development." — [JOSS submitting](https://joss.readthedocs.io/en/latest/submitting.html)
- Exclusions: "'Minor utility' packages, including 'thin' API clients, and single-function packages are not acceptable." — [JOSS submitting](https://joss.readthedocs.io/en/latest/submitting.html)
- Single-author projects must show indicators such as "tests and CI, clear documentation", plus "a CONTRIBUTING file, and stated support or governance expectations". Multi-author projects need "evidence of issues, pull requests, and public discussion." — [JOSS submitting](https://joss.readthedocs.io/en/latest/submitting.html)
- The paper "must not focus on new research results accomplished with the software." It is written as `paper.md` in the repository. There are no fees, and preprints are allowed. — [JOSS submitting](https://joss.readthedocs.io/en/latest/submitting.html)
- AI policy: AI use is permitted but must be disclosed (tools, versions, nature of assistance), and authors must assert that humans "reviewed, edited, validated all AI-assisted outputs and made the core design decisions." — [JOSS submitting](https://joss.readthedocs.io/en/latest/submitting.html)
- Length: "The paper should be between 750-1750 words." Required sections are Summary, Statement of need, State of the field, Software design, Research impact statement, and AI usage disclosure. The paper also needs authors and affiliations, key references including related software, funding acknowledgement, and representative research projects that use the software, if applicable. — [JOSS paper format](https://joss.readthedocs.io/en/latest/paper.html)
- Reviewer checklist. Reviewers install the software and "verify the core functionality." Installation is rated Good when it uses language-standard tooling. Tests are rated Good for "An automated test suite hooked up to continuous integration (GitHub Actions, Circle CI, or similar)", OK for "Documented manual steps that can be followed to objectively check the expected functionality", and Bad when there is "No way for you, the reviewer, to objectively assess whether the software works". The State of the field section must compare the software with commonly used packages and justify building new software rather than contributing to existing projects. — [JOSS review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html)
- Precedent: Denninger et al., "BlenderProc2: A Procedural Pipeline for Photorealistic Rendering," JOSS 8(82), 4901, published 20 Feb 2023 (submitted 21 Sep 2022), doi:10.21105/joss.04901. Its statement of need positions it against NDDS, NViSII, Habitat, Stillleben and Kubric in a feature table. The table columns are: semantic segmentation, depth rendering, optical flow, surface normals, object pose, bounding box, physics module, camera sampling, GUI-based debugging viewer, open-source renderer, and real-time. — [JOSS BlenderProc2 page](https://joss.theoj.org/papers/10.21105/joss.04901) / [PDF](https://joss.theoj.org/papers/10.21105/joss.04901.pdf)
- BlenderProc2 claims rendering of "color, depth, distance, surface normals, and semantic segmentation", plus "optical flow and normalized object coordinates (NOCS)", saved "either in the hdf5 container or in the BOP or COCO formats." — [BlenderProc2 JOSS PDF](https://joss.theoj.org/papers/10.21105/joss.04901.pdf)

### Inferences
- The BlenderProc2 feature table is the comparison a JOSS reviewer will expect. A "State of the field" section must explain why this add-on is not just a BlenderProc script. The best differentiators are a GUI-driven workflow for engineers, STEP/IGES import that keeps part names and colours, canonical orthographic engineering views, and line-art/clay passes for documentation.
- The add-on is a single Python file and GUI-driven. Reviewers may probe the "minor utility" exclusion and the "packaged appropriately" criterion. Distribution as a Blender Extension (the `blender_manifest.toml` format of Blender 4.2+) is probably the "language-standard tooling" equivalent.
- Committed automated tests running in CI (e.g. headless `blender -b --python` tests on GitHub Actions) move the Tests item from "OK" to "Good". This is the cheapest JOSS-readiness gain available.
- Research use is now mandatory. The authors need at least one documented research use, such as their own dataset, a thesis, or a third-party user, before submitting to JOSS.

### Gaps
- No Blender add-on (as opposed to Blender-based Python libraries) published in JOSS was verified in this pass.
- The exact date when JOSS introduced the 6-month and research-impact rules was not established. Treat them as current as of the fetched page (Oct 2026).

---

## Q2. SoftwareX (Elsevier) and Journal of Open Research Software (JORS)

### Takeaway
Both journals accept short "software description" papers. SoftwareX caps papers at about 3000 words, uses a fixed template with a code-metadata table, and requires a public repository. JORS publishes "software metapapers" with no stated length limit and an APC of GBP 824. Neither appears to require demonstrated prior research use the way JOSS now does, so both can be fallbacks if the JOSS gates are not yet met.

### Cited Findings
- SoftwareX submissions consist of "a short descriptive paper of 3000-word limit" plus an open-source software distribution. One listing says a maximum of 6 pages instead, so the two sources conflict. — search snippet from [Cirad "Où publier" SoftwareX entry](https://ou-publier.cirad.fr/en/node/5493) (secondary; the official Guide for Authors at sciencedirect.com returned HTTP 403)
- SoftwareX accepts submissions only if the code is freely available. — [Wikipedia: SoftwareX](https://en.wikipedia.org/wiki/SoftwareX) (secondary)
- The SoftwareX software-update template (Version 6, March 2026) states that only GitHub repositories are accepted in the metadata tables and that the repository needs a README.md and a Licence.txt. It directs original submissions to the OSP (Original Software Publication) template in the Guide for Authors. — [SoftwareX software-update template v6](https://legacyfileshare.elsevier.com/promis_misc/softwarex-software-update-template.docx) (content seen via search snippet)
- JORS software metapapers are accepted only for software deposited in a public repository under an open licence ("Papers will only be accepted for software that authors agree to make freely available in a public repository"). Authors use the DOCX/LaTeX template and include the repository's persistent identifier. The code must be "a substantive intellectual contribution", and installation should be easy, ideally via a registry. No length limit is stated. The APC is GBP 824 for Software Metapapers, with waivers requestable. — [JORS submissions](https://openresearchsoftware.metajnl.com/about/submissions)

### Inferences
- SoftwareX's standard OSP sections (from general familiarity with the template, not verified this session) are Motivation and significance, Software description, Illustrative examples, Impact, and Conclusions. Its "Impact" section plays the role of the JOSS research-impact statement but is usually judged less strictly. Verify against the current template before writing.
- SoftwareX is indexed with an impact factor and is Elsevier open access, so expect an APC. The current figure was not obtained.

### Gaps
- The official SoftwareX Guide for Authors could not be fetched (HTTP 403 from ScienceDirect), so the APC, the exact code-metadata fields and the current word limit remain unconfirmed from the primary source.
- JORS's detailed peer-review criteria page was not fetched.

---

## Q3. ASME JCISE and Elsevier Computer-Aided Design (CAD): scope for visualization and data-generation tools

### Takeaway
Elsevier's *Computer-Aided Design* lists "Dataset papers" as an article type ("an algorithmic contribution is not required") and has "data driven modeling and synthesis" in scope. A CAD-to-multi-view dataset, released with the tool, is therefore a credible CAD submission. Visualization and rendering are not listed topics there. ASME JCISE's scope page could not be fetched. Its closest dataset-related call (a 2022 "Data Wrangling" special issue) has closed. The sister ASME *Journal of Mechanical Design* ran a "Design by Data: Cultivating Datasets for Engineering Design" special issue, now closed.

### Cited Findings
- CAD aims and scope cover the computational foundations and methods of design, for work with "significant geometric, topological, spatial, or configuration design content." Topics include "Applications of AI in design, including neural networks and machine learning", "Data driven modeling and synthesis", and "Data acquisition, model recognition and reconstruction". Article types are Research, Application, Survey, Technical notes, and **Dataset papers** (the dataset must be freely usable for research and no algorithmic contribution is required). Visualization and rendering are not listed. — [Elsevier: Computer-Aided Design](https://shop.elsevier.com/journals/computer-aided-design/0010-4485)
- JCISE special issue "Data Wrangling to Support Research on Engineering Design and Manufacturing" examined how engineering data is generated, collected, curated, stored and transformed. Submissions were due March 2022 for a December 2022 issue. — [ASME news](https://www.asme.org/topics-resources/society-news/asme-news/special-journal-issue-on-data-wrangling-to-support-research-on-engineering-design-and-manufacturing) / [CFP PDF](https://www.asme.org/getmedia/87daddba-8908-4de6-a5ea-70b3abd62a35/JCISE-SI-DataWranglingtoSupportResearch.pdf)
- JMD special issue "Design by Data: Cultivating Datasets for Engineering Design" sought papers that publicly release datasets, including complex 2D/3D design artifacts (including CAD). The deadline was extended to July 1, 2024, with publication March 1, 2025. — [JMD CFP](https://asmejmd.org/2025/02/18/call-for-papers-design-by-data-cultivating-datasets-for-engineering-design/)
- Related CAD-learning datasets in this community: ABC provides 1M CAD models in B-Rep, and Fusion 360 Gallery provides 8,625 human-designed CAD reconstruction sequences. — [Geometric Deep Learning for CAD survey, arXiv 2402.17695](https://arxiv.org/pdf/2402.17695); [Fusion 360 Gallery paper](https://www.research.autodesk.com/app/uploads/2023/03/Fusion_360_Gallery__A_Dataset_and_Environment_for_Programmatic_CAD_Construction_from_Human_Design_Sequences.pdf_recB1A7wJLthITzJo.pdf)

### Inferences
- For the CAD journal, frame the paper as a dataset paper or a data-driven-methods paper. One example would be a standardized multi-view render set of a public CAD corpus such as ABC or Fusion 360 Gallery, with STEP part names preserved as part-ID masks, plus a baseline such as multi-view part segmentation or retrieval. A pure tool paper fits less well.
- JCISE (computing in engineering) plausibly accepts tool papers with engineering applications, but this could not be verified from the primary scope page.

### Gaps
- The ASME JCISE "About the Journal" page returned HTTP 403, so its current scope wording, technical-brief format and any open special issues are unverified.
- No example of a rendering-tool or data-generation-tool paper in JCISE or CAD was found in this pass.

---

## Q4. CV workshops on synthetic data and the NeurIPS Datasets & Benchmarks track (now "Evaluations and Datasets")

### Takeaway
SynData4CV at CVPR is the most directly relevant workshop. The 3rd edition took place 4 June 2026 in Denver. It takes 4-page short and 8-page long papers through OpenReview, uses double-blind review, and does not publish in the CVPR proceedings, so a later journal or JOSS paper remains possible. NeurIPS 2026 renamed its D&B track "Evaluations and Datasets" (E&D). It now names "Data generators" as in scope and requires code release when a reusable software tool is the primary contribution. Dataset submissions need Croissant metadata with Responsible AI (RAI) fields, hosted on Dataverse, Kaggle, Hugging Face or OpenML. A NeurIPS-level submission needs a generated dataset plus baselines, not just the tool.

### Cited Findings
- SynData4CV 2026 (3rd edition, CVPR 2026, June 4, 2026, Denver). Topics include the effectiveness of synthetic data (including "whether it needs to look realistic"), "Efficient and scalable synthetic data generation pipelines", "Novel methods for generating synthetic data", "Benchmarks and evaluation metrics", risks and ethics, and mixing synthetic and real data. Short papers are 4 pages and long papers 8 pages (excluding references), in the CVPR template with double-blind review via OpenReview. The 2026 deadline was March 17, 2026. "Accepted papers will NOT be included in CVPR proceedings." — [SynData4CV site](https://syndata4cv.github.io/)
- A short paper at SynData4CV 2026 won a best short paper award. — [Politecnico di Milano news](https://www.deib.polimi.it/eng/news/details/1509)
- NeurIPS 2026 E&D track scope includes "Data generators and reinforcement learning environments" and benchmarking tools. When a reusable executable artifact ("software tool") is the primary contribution, code release at submission is required. Dataset papers must explain scope, assumptions, limitations and intended evaluative use. Data must be accessible to reviewers without a personal request, and datasets over 4GB need a small reviewer sample. Non-compliance can justify desk rejection. Review is double-blind by default, with single-blind allowed when datasets cannot be anonymized. The 2026 dates were: abstract May 4, full paper May 6, notification Sept 24. — [NeurIPS 2026 Call for Evaluations & Datasets](https://neurips.cc/Conferences/2026/CallForEvaluationsDatasets)
- "All dataset submissions must now include Responsible AI (RAI) metadata as part of the dataset's Croissant file." Submissions missing it "will be flagged during review." NeurIPS provides an RAI editor and a Croissant validator. — [NeurIPS blog, 4 May 2026](https://blog.neurips.cc/2026/05/04/responsible-ai-metadata-requirements-for-the-evaluations-and-datasets-track-neurips-2026/)
- Hosting guidelines require datasets with Croissant metadata (core and minimal RAI) on Harvard Dataverse, Kaggle, Hugging Face or OpenML, or a custom solution. — [NeurIPS 2026 hosting guidelines](https://nips.cc/Conferences/2026/EvaluationsDatasetsHosting) (via search result summary)

### Inferences
- Realistic path: a SynData4CV short paper (4 pages) presenting the tool plus a small experiment, for example training a detector or segmenter on renders of industrial parts and testing on real photos. Being non-archival, it does not block a later JOSS or SoftwareX paper.
- For NeurIPS E&D, the contribution would need to be "data generator plus a released benchmark dataset with baselines". Exporting a Croissant JSON-LD file directly from the manifest would remove a submission chore.

### Gaps
- The ICCV/ECCV synthetic-data workshops for 2025-2026 and their CFPs were not researched in this pass. Synthetic-data papers there are typically 4-8 pages and may be archival or non-archival depending on the workshop.
- The NeurIPS E&D page limit was not stated on the call page (it defers to the main-track CFP).

---

## Q5. Zenodo DOI and software citation (CITATION.cff)

### Takeaway
Add a `CITATION.cff` (cff-version 1.2.0) to enable GitHub's "Cite this repository" button. Enable the Zenodo GitHub integration so that each GitHub release mints a versioned DOI. JOSS, SoftwareX and JORS all expect an archived, citable software version. Sources disagree on whether `.zenodo.json` or `CITATION.cff` takes precedence when both exist, so use only one or test with a release.

### Cited Findings
- A `CITATION.cff` on the default branch adds a "Cite this repository" link on GitHub, which generates APA and BibTeX. `type: dataset` produces a data citation, and `preferred-citation` can point to a paper. The example fields are `cff-version: 1.2.0`, `message`, `authors` (family-names/given-names), `title`, `version`, `doi`, `date-released` and `url`. — [GitHub Docs: About CITATION files](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files)
- JOSS requires the paper to link to the software archive. — [JOSS review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html)
- After the repository is enabled in Zenodo's GitHub settings, the next GitHub release triggers archiving and DOI minting. A release containing CITATION.cff populates the Zenodo record from that file, while one without it uses GitHub API metadata. — [CASRAI: DataCite, GitHub, Zenodo](https://casrai.org/wp/?p=1132); [DEV Community](https://dev.to/dmytronasyrov/github-release-to-zenodo-doi-265f) (secondary)
- Conflict: one source says `.zenodo.json` overrides CITATION.cff when both exist, while a Sage commit says the reverse. — [DEV Community](https://dev.to/dmytronasyrov/github-release-to-zenodo-doi-265f) vs [Sage commit](https://app.semanticdiff.com/gh/mkoeppe/sage/commit/7e0eb1c9219371a660a52fdac5bba7d693ec627c)
- Croissant has an optional `citeAs` field (preferably BibTeX), so a rendered dataset can carry the tool's citation. — [Croissant 1.0 spec](https://docs.mlcommons.org/croissant/docs/croissant-spec.html)

### Inferences
- Have the renderer write the tool version, DOI and `citeAs` into every manifest it produces. Each dataset then self-cites the software, which builds the evidence of research use that JOSS requires.

### Gaps
- Zenodo's official help page on GitHub metadata precedence was not fetched.

---

## Q6. Standard annotations/passes and file formats expected from synthetic rendering tools

### Takeaway
Across BlenderProc2, Kubric and BOP, the de facto "full" annotation set is RGB, depth (and/or distance), surface normals, instance and semantic segmentation (plus visible and amodal masks), 2D/3D bounding boxes, camera intrinsics and extrinsics per image, and 6D object pose. Optical flow and object coordinates (NOCS) are common extras. Standard containers are COCO (boxes and RLE masks), BOP (scene_camera/scene_gt/scene_gt_info + masks, mm units, OpenCV camera), NeRF/nerfstudio `transforms.json` (OpenGL/Blender camera-to-world), and HDF5. The add-on currently lacks every geometric annotation except a mask, and has no camera-pose export. These are the biggest research-impact gaps.

### Cited Findings
- BlenderProc2 renders "color, depth, distance, surface normals, and semantic segmentation", "optical flow and normalized object coordinates (NOCS)", and saves in "hdf5 ... BOP or COCO formats". — [BlenderProc2 JOSS PDF](https://joss.theoj.org/papers/10.21105/joss.04901.pdf)
- BlenderProc README: "RGB, stereo, depth, normal and segmentation images/sequences"; "Writing: .hdf5 containers, COCO & BOP annotations"; loading of `*.obj`, `*.ply`, `*.blend`, `*.fbx`, BOP, ShapeNet, etc. It runs via the `blenderproc run <script>` CLI, with `blenderproc debug` opening the Blender UI. — [BlenderProc GitHub](https://github.com/DLR-RM/BlenderProc)
- Kubric exports "1 depth maps, 2 instance segmentation, 3 optical flow, 4 surface normals, and 5 object coordinates" plus "2D/3D trajectories, 2D/3D bounding boxes, velocities, mass, friction, camera parameters, collision events, as well as custom metadata." The authors note that existing datasets "rarely contain all possible annotations ... lacking key signals such as camera pose, instance or semantic segmentation masks, or optical flow." — [Kubric, Greff et al., CVPR 2022, arXiv 2203.03570](https://arxiv.org/pdf/2203.03570)
- BOP format. `scene_camera.json` has `cam_K` (3x3 row-wise), `depth_scale` ("Multiply the depth image with this factor to get depth in mm") and optional `cam_R_w2c`/`cam_t_w2c`. `scene_gt.json` has `obj_id`, `cam_R_m2c` and `cam_t_m2c`. `scene_gt_info.json` has `bbox_obj`, `bbox_visib`, `px_count_all`, `px_count_valid`, `px_count_visib` and `visib_fract`. `scene_gt_coco.json` holds COCO RLE annotations. Folders are `rgb/`, `depth/` (16-bit), `mask/` and `mask_visib/` (named `IMID_GTID.png`). Models are ASCII PLY in mm, with `models_info.json` giving the diameter and bounding box. Coordinate systems are right-handed, the camera follows OpenCV, and translations are in mm. A `test_targets_multiview_bop25.json` exists for multi-view tasks. — [bop_toolkit: BOP datasets format](https://github.com/thodan/bop_toolkit/blob/master/docs/bop_datasets_format.md)
- nerfstudio `transforms.json` uses the "OpenGL/Blender (and original NeRF) coordinate convention" (+X right, +Y up, camera looks along -Z). Fields are `camera_model` (OPENCV/OPENCV_FISHEYE), `fl_x`, `fl_y`, `cx`, `cy`, `w`, `h`, distortion `k1`-`k4`/`p1`,`p2`, and `frames[]` with `file_path` and 4x4 `transform_matrix`, plus optional `depth_file_path` (16/32-bit, mm) and `mask_path`. — [nerfstudio data conventions](https://docs.nerf.studio/quickstart/data_conventions.html)
- Instant-NGP reads `transforms.json` "in a format compatible with" the original NeRF codebase, adds `aabb_scale`, `scale` and `offset`, and provides `colmap2nerf.py` to convert COLMAP reconstructions. — [instant-ngp NeRF dataset tips](https://github.com/NVlabs/instant-ngp/blob/master/docs/nerf_dataset_tips.md)
- Objaverse-XL / Zero123-style multi-view object renders use Blender with 12 views per object sampled on a sphere around the centred object (`000-011.png` per object). — [Objaverse-XL NeurIPS 2023 D&B supplement](https://papers.neurips.cc/paper_files/paper/2023/file/70364304877b5e767de4e9a2a511be0c-Supplemental-Datasets_and_Benchmarks.pdf); [zero123 repo](https://github.com/cvlab-columbia/zero123)

### Inferences
- Suggested priority order for widening research impact, roughly most impact per effort first:
  1. **Per-view camera pose export** (intrinsics K + extrinsics) in the manifest, plus a `transforms.json` writer. This is trivial for a fixed rig and makes every output usable for NeRF, Gaussian-splatting, novel-view-synthesis and multi-view 3D learning.
  2. **Depth (metric, mm, 16-bit PNG or EXR) and surface normals** via Blender's built-in Z and Normal passes.
  3. **Instance/part-ID masks** from STEP part names (via Cycles/EEVEE Object/Material index or Cryptomatte). This is a unique differentiator, since STEP import preserving part names is rare and part-level segmentation of CAD assemblies is under-served.
  4. **COCO export** (boxes and RLE masks per part/product) and **BOP export**. For a single object at a known pose, `scene_gt` is simply the object-to-camera transform, so the BOP writer is cheap.
  5. A headless CLI and deterministic seeds (see Q8 and Q9).
- Unit conventions matter. BOP uses mm and an OpenCV camera, while NeRF/nerfstudio uses an OpenGL camera-to-world. Exporting both, with the convention stated in the manifest, avoids the most common user bug.

### Gaps
- The COCO format specification (Lin et al. 2014) and COLMAP's `cameras.txt`/`images.txt` text format were not fetched this session. Both are widely documented. KITTI-style formats suit driving datasets and are not a priority for object-centric product renders.
- No tool-by-tool comparison of keypoint export was found.

---

## Q7. Evidence on domain randomization vs photorealism (relevant to industrial and CAD objects)

### Takeaway
The evidence supports both, used together. For texture-less industrial CAD parts, the BOP Challenge 2020 found that physically based renders (PBR) of objects in plausible scenes beat OpenGL "render & paste" images by large margins, for example CosyPose on T-LESS at 64.0% vs 6.1%. Randomized textures still helped texture-less CAD (T-LESS) by forcing shape focus. Domain randomization (Tobin 2017) and structured DR (Prakash et al. 2018) show that non-photoreal randomized data can transfer to the real world. The add-on's clean studio renders are neither, so adding randomization (backgrounds/HDRIs, lighting, materials, distractors, camera jitter) is needed for training-data use.

### Cited Findings
- Tobin et al. 2017 (IROS) trained an object detector on simulated images with non-realistic random textures that is accurate to about 1.5 cm in the real world and robust to distractors and partial occlusion. They describe it as the first successful transfer of a deep network trained only on simulated RGB images to real-world robotic control. — [arXiv 1703.06907](https://arxiv.org/abs/1703.06907v1)
- Structured Domain Randomization (Prakash, Boochoon, Brophy, Acuna, Cameracci, State, Shapira, Birchfield; arXiv 1810.10093, ICRA 2019) places objects and distractors according to problem-specific probability distributions. Trained only on synthetic data, it outperforms VKITTI, Sim 200k, standard DR and real BDD100K data on KITTI car detection. "Synthetic SDR data combined with real KITTI data outperforms real KITTI data alone." — [arXiv 1810.10093](https://arxiv.org/abs/1810.10093)
- Hodaň et al. 2019 rendered objects in full 3D scenes with physics-based placement and PBR. Faster R-CNN "achieves a 24% absolute improvement of mAP@.75IoU on Rutgers APC" and 11% on LineMod-Occluded vs a baseline pasting renders onto random photos. — [arXiv 1902.03334](https://arxiv.org/abs/1902.03334)
- BOP Challenge 2020 (Hodaň et al., ECCV 2020 workshop) gave participants 350K PBR training images from BlenderProc4BOP. It notes that CAD models "are either available before the physical objects, which is often the case for manufactured objects". Its findings:
  - "Methods achieved noticeably higher accuracy scores when trained on PBR training images than when trained on 'render & paste' images."
  - CosyPose improved "by a significant 57.9% (from 6.1% to 64.0%) on T-LESS, by 19.0% on TUD-L, and by 30.9% on YCB-V" with 50K PBR vs 50K render-and-paste-v1 images, where object poses were identical. The paper concludes that "ray-tracing rendering technique, PBR materials and objects realistically embedded in synthetic environments seem to be the decisive factors."
  - PBR gave an average improvement of 35.9% over render & paste v1 and 25.5% over v2.
  - Randomizing surface textures of texture-less T-LESS CAD models (render & paste v2) gave +39.2% over v1 on T-LESS but no gain on TUD-L (-7.1%) and YCB-V (-0.8%).
  - PBR matters more for training detection/segmentation than for pose refinement.
  - Real images still add accuracy, but "competitive results can be achieved with PBR images only."
  - [arXiv 2009.07378](https://arxiv.org/abs/2009.07378) (full-text PDF, Secs. 1, 4.3, Table 3)
- Kubric authors: "Photo-realism is often considered essential for narrowing the generalization gap, but even without perfect realism, synthetic data can be remarkably effective." — [Kubric arXiv 2203.03570](https://arxiv.org/pdf/2203.03570)

### Inferences
- For "turn CAD into training data" claims, the strongest evidence-backed feature set is Cycles PBR rendering with randomized physically plausible context: random PBR materials or floor/walls, HDRI lighting, distractor objects, and camera pose sampling around the canonical rig. The add-on already uses Blender, so Cycles realism is available.
- The canonical rig and clean passes are themselves valuable for a different use: standardized multi-view benchmarks, retrieval, documentation and NVS evaluation. The paper can position randomization as an optional mode layered on top of canonical views.
- An evaluation that would satisfy SynData4CV reviewers: train a detector or segmenter on (a) canonical clean renders, (b) randomized renders, and (c) randomized + PBR, then test on a small set of real photos of the same industrial parts, or on T-LESS, which ships CAD models.

### Gaps
- Specific post-2023 BOP challenge findings (BOP 2023/2024/2025 model-based vs model-free tracks) on synthetic data were not fetched.
- No primary source was found that quantifies randomization vs photorealism specifically for STEP-derived mechanical assemblies beyond T-LESS.

---

## Q8. Throughput, scale and headless operation expectations

### Takeaway
Research generators are expected to run headless and in parallel (one independent worker per scene or object), often in Docker on clusters or cloud. Reported scales are in the CPU-years and thousands-of-GPU-hours range. Kubric's optical-flow dataset took about 3 CPU-years, and the Objaverse-XL 12-view renders took about 8K T4 GPU-hours (48 GPUs for about a week). A GUI-only add-on will be judged as unsuitable for dataset-scale generation unless it offers a CLI and batch entry point.

### Cited Findings
- Kubric "seamlessly scales to large jobs distributed over thousands of machines, and generating TBs of data". Its workflow is a worker script that renders a single random scene, run many times with GCP launcher scripts. It ships a Docker image to "ensure portability and remove the bulk of the installation pain," noting "the difficulty in installing the Blender Python module and the substantial variations between versions." — [Kubric arXiv 2203.03570](https://arxiv.org/pdf/2203.03570)
- Kubric: "our optical flow dataset required roughly 3 CPU-years of compute-time". The authors urge researchers to avoid generating unnecessarily large datasets. Converting ShapeNet assets took about 16 hours on an 80-core VM. Path tracing "requires substantial computational resources" and a rasterizing backend is planned to trade speed against quality. — [Kubric arXiv 2203.03570](https://arxiv.org/pdf/2203.03570)
- Kubric reports 13 generated datasets (arXiv version), against 11 in the CVPR proceedings version. — [Kubric CVPR 2022](https://openaccess.thecvf.com/content/CVPR2022/html/Greff_Kubric_A_Scalable_Dataset_Generator_CVPR_2022_paper.html)
- BlenderProc2 distinguishes game-engine generators that "generate dozens of images per second" from path-tracing tools like itself, which "focus on the realism of the final images instead of on their generation speed." — [BlenderProc2 JOSS PDF](https://joss.theoj.org/papers/10.21105/joss.04901.pdf)
- Objaverse-XL rendering (12 views per object, Blender) "was done for around 1 week on 48 NVIDIA T4 GPUs, totaling around 8K GPU hours." — [Objaverse-XL NeurIPS 2023 D&B supplement](https://papers.neurips.cc/paper_files/paper/2023/file/70364304877b5e767de4e9a2a511be0c-Supplemental-Datasets_and_Benchmarks.pdf) (via search snippet)
- BOP 2020 provided 350K pre-rendered PBR images. — [arXiv 2009.07378](https://arxiv.org/abs/2009.07378)

### Inferences
- Minimum expectations for a research audience:
  - a `blender -b -P` / `--python-expr` CLI entry point that takes a config file (JSON/YAML) and an input folder;
  - one-process-per-object sharding, so it parallelizes on SLURM or cloud (the existing resumable batch is a good basis);
  - a Docker image or pinned Blender version;
  - EEVEE (fast) and Cycles (realistic) presets;
  - reported throughput (images per hour per GPU at stated resolution and samples) in the paper. Reviewers compare against these figures.
- The paper should report its own measured throughput. No standard benchmark exists, so stating hardware, resolution, engine and samples is the expected practice.

### Gaps
- No images-per-hour figure was found for BlenderProc or Kubric. Both papers report scale qualitatively or in total compute rather than per-image rates.
- Zero123's original Objaverse 1.0 render cost was not found (only training cost was reported).

---

## Q9. Reproducibility and provenance: dataset documentation standards a manifest could align with

### Takeaway
Croissant 1.0 (MLCommons, JSON-LD on schema.org/Dataset), plus its RAI extension, is now a hard requirement for NeurIPS dataset submissions and is auto-generated by Hugging Face, Kaggle and OpenML. The add-on's CSV/JSON manifest maps naturally onto Croissant: a FileSet per image pass, RecordSets for per-view metadata, and sha256 checksums. Datasheets for Datasets (Gebru et al.) is the narrative counterpart that the "limitations / intended use" fields echo.

### Cited Findings
- Croissant 1.0 was published 2024-03-01 and declares `dct:conformsTo: http://mlcommons.org/croissant/1.0`.
  - **Required fields:** `@context`, `@type` (schema.org Dataset), `dct:conformsTo`, `description`, `license`, `name`, `url`, `creator`, `datePublished` and `distribution`.
  - **Recommended fields:** `version` (semver), `dateCreated`, `dateModified`, `keywords`, `publisher`, `inLanguage` and `sameAs`. `citeAs` (BibTeX) is optional.
  - **Resources:** `FileObject` (`contentUrl`, `contentSize`, `encodingFormat`, `sha256`) and `FileSet` (`includes`/`excludes` globs).
  - **Records:** `RecordSet` and `Field`, with `dataType` such as `sc:ImageObject` or `cr:BoundingBox`, `source`/`extract` (CSV column, JSONPath) and `references` for joins.
  - The RAI extension adds vocabulary for labeling, fairness and compliance.
  - [Croissant 1.0 spec](https://docs.mlcommons.org/croissant/docs/croissant-spec.html)
- NeurIPS 2026 requires Croissant with core and RAI fields covering limitations, potential biases and intended use. Preferred hosts generate the core fields automatically. — [NeurIPS blog 2026-05-04](https://blog.neurips.cc/2026/05/04/responsible-ai-metadata-requirements-for-the-evaluations-and-datasets-track-neurips-2026/); [NeurIPS 2026 E&D CFP](https://neurips.cc/Conferences/2026/CallForEvaluationsDatasets)
- The NeurIPS E&D CFP lists Data Cards, Model Cards and evaluation cards as in scope, and requires dataset papers to state scope, assumptions, limitations and intended use. — [NeurIPS 2026 E&D CFP](https://neurips.cc/Conferences/2026/CallForEvaluationsDatasets)
- Kubric lists "Portable and Reproducible" as a design goal: the pipeline "produces the same results -- even when executed on different machines". — [Kubric arXiv 2203.03570](https://arxiv.org/pdf/2203.03570)
- Datasheets for Datasets (Gebru et al., arXiv 1803.09010; CACM 2021) proposes a standard question set covering motivation, composition, collection process, preprocessing/cleaning/labeling, uses, distribution and maintenance. — [arXiv 1803.09010](https://arxiv.org/abs/1803.09010) (section list from prior knowledge; not re-fetched this session)

### Inferences
- Manifest additions that would make outputs "research-grade":
  - tool version and DOI; Blender version; render engine and samples; random seed(s);
  - a source-file hash (sha256 of each input CAD/mesh) and normalization transform applied (scale factor, rotation);
  - per-image camera K and pose, plus the convention used;
  - a pass list with units;
  - licence of the source models;
  - an optional `croissant.json` emitted alongside the CSV/JSON. The add-on already writes a manifest, so emitting Croissant is cheap and directly useful for NeurIPS E&D and Hugging Face hosting.
- The existing "pre-flight checks" and resumable batch can be presented as provenance and reproducibility features in the paper.

### Gaps
- The exact list of the minimal RAI fields NeurIPS requires was not enumerated on the fetched pages.
- The Datasheets paper was not re-fetched this session. The section list above should be checked against [arXiv 1803.09010](https://arxiv.org/abs/1803.09010) before quoting.
