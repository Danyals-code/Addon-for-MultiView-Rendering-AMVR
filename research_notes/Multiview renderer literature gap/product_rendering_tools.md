# Product-visualization tools for automated multi-view batch rendering from CAD (landscape and gap analysis, as of Oct 2026)

Scope note: research done 2026-10-26 in about 16 search/fetch calls. Where only third-party or community sources were found, this is flagged. Prices are as of the date stated. Vendor pages were not checked by hand beyond what is cited.

## 1. What do commercial product-visualization tools offer for automated multi-view batch rendering, and at what cost?

### Takeaway
The commercial leaders (KeyShot Studio, SOLIDWORKS Visualize Professional, Autodesk VRED Professional/Design, NVIDIA Omniverse) can all automate rendering. They do it through paid tiers, per-seat subscriptions of roughly US$1,300-1,700+ a year, and either a GUI render queue or a scripting API you program yourself. None of the sources found describes a built-in "drop in a folder of STEP files, get a standardized orthographic six-view set, a turntable, a contact sheet and a manifest" pipeline. Batch multi-file workflows exist only as community scripts or as one-project, many-camera queues.

### Cited Findings
**KeyShot (Luxion / KeyShot Studio)**
- Official pricing page (seen Oct 2026; page carries 2026 copyright and June 2026 images, no effective date): Professional US$1,299/yr ($108.25/user/mo), Business US$1,599/yr ($133.25/user/mo), 3-year totals $3,897 / $4,797, Enterprise custom-quoted. — [KeyShot Pricing](https://www.keyshot.com/pricing/)
- Add-ons on the same page: Network Rendering $749/yr (32-core tier, Business/Enterprise), NX Plugin $348/yr, Studio VR $1,188/yr, Cloud Rendering by credits ($25 for 100 credits up to $6,875 for 50,000). The Cloud Render Queue requires version 2026.2+. "KeyShotWeb (XR & Configurator)" is listed as an add-on. The page says 34+ CAD formats are supported and includes one-click animation and product reveals. — [KeyShot Pricing](https://www.keyshot.com/pricing/)
- Third-party sources say perpetual licences were discontinued in 2023 and there is no free tier, only a 14-day trial. This is not confirmed on the official page. — [renderahouse.com](https://www.renderahouse.com/blog/keyshot-pricing); [myarchitectai.com](https://www.myarchitectai.com/blog/keyshot-pricing)
- Capterra lists a "$99 KeyShot Pro" figure that conflicts with the official pricing and is likely stale. — [Capterra](https://www.capterra.com/p/173819/KeyShot/pricing/)
- KeyShot has a Python scripting API (the `lux` module). KeyShot Studio 2024/2025 use Python 3.12; KeyShot 11 used 3.10. Scripting is a Pro feature, and a headless mode runs scripts from a terminal without the GUI. — [KeyShot 2024 manual: scripting](https://manuals.keyshot.com/keyshot2024/manual/scripting.html); [KeyShot Studio 2025 manual: scripting](https://manuals.keyshot.com/kss2025/manual/scripting.html); [KeyShot 11 manual](https://manual.keyshot.com/keyshot11/manual/scripting/)
- Batch over many CAD files is done with user scripts. A KeyShot community forum post shares `batch_import_render_queue.py`, which imports every CAD file in a folder, optionally applies a material template, sets up a camera and queues a render per file. It uses a GUI settings dialog. The post notes that `lux.ThumbnailRenderOptions` is for material thumbnails, not scene renders. — [KeyShot community forum](https://db_e596cbae_9eea_47cf_9859_c9418b6eabfd.influitive.com/forum/t/keyshot-studio-python-script-batch-import-render-automation/14613)
- Headless has limits: some functions "can not be exposed in headless scripting", and `renderAnimation` was not available headless. The workaround is to loop `lux.setAnimationFrame()` and `lux.RenderImage()`, then call `lux.encodeVideo()`. The render queue misbehaves with multiple instances open. — [KeyShot forum "Headless hurdles"](https://community.keyshot.com/forum/t/headless-hurdles/507)
- Third-party MCP servers wrap KeyShot headless mode for batch rendering of named cameras. One notes that the `lux` API changes between versions. — [KeyShot MCP (glama.ai)](https://glama.ai/mcp/servers/truman-t3/keyshot-mcp); [glama.ai](https://glama.ai/mcp/servers/fo2aege8yd)

**SOLIDWORKS Visualize (Dassault Systèmes)**
- The Render Queue and one-click "render all configurations / camera angles" from one project are Visualize **Professional**-only features. A one-click 360° turntable output exists, and turntables can be queued to render unattended. — [SOLIDWORKS: Visualize Professional-only features (PDF)](https://www.solidworks.com/sw/docs/SW_Visualize_Top_Professional-only_Features.pdf); [Javelin: Render Queue (2024)](https://www.javelin-tech.com/blog/2024/06/how-to-use-solidworks-visualize-professionals-rendering-queue-for-streamlined-design/); [Javelin: Professional vs Standard (2023)](https://www.javelin-tech.com/blog/2023/04/advantages-of-using-solidworks-visualize-professional-vs-standard/)
- Visualize Boost (network rendering) is included with each Professional seat. — [Javelin](https://www.javelin-tech.com/blog/?p=35219)
- No current public price was found. Pricing is through resellers. — [GoEngineer](https://www.goengineer.com/visualize-solidworks)

**Autodesk VRED**
- The Python API is only in VRED Professional and VRED Design, not VRED Basic. Autodesk lists batch-processing files and scaling renders across a cluster as uses. — [Autodesk Platform Services: VRED APIs](https://aps.autodesk.com/node/4011)
- The only price found is an aggregator's "starting from US$1,700" with no edition or term stated, so it is unreliable. — [Capterra UK](https://www.capterra.co.uk/software/182129/vred)

**Onshape (PTC)**
- The REST API thumbnails are a single isometric identification image per element. For other viewpoints, forum guidance points to the Part Studio/Assembly `/shadedviews` endpoints, which take a view matrix and `pixelSize`. Users report cropped or off-centre framing for large models. Automation needs API keys or OAuth. — [Onshape forum: thumbnails for BOM items](https://forum.onshape.com/discussion/18987/api-trying-to-find-a-more-efficient-way-to-pull-thumbnails-for-each-bom-item); [Onshape forum: auto-export view images](https://forum.onshape.com/discussion/17201/how-to-automatically-export-view-images)
- Onshape's own blog describes IKEA's CAD-to-catalogue workflow ("about 75% of images in the 2016 catalog began as 3D CAD models"). This is a secondary report of a conference talk. — [Onshape blog](https://www.onshape.com/en/blog/how-to-render-photorealistic-images-like-ikea)

**NVIDIA Omniverse**
- Product configurators are an official workflow: CAD is converted to OpenUSD and authored with the Kit SDK, with web delivery through the App Streaming API. — [Omniverse dev overview](https://docs.omniverse.nvidia.com/dev-overview/latest); [Product configurator reference architecture](https://docs.omniverse.nvidia.com/arch-diagrams/latest/ref-arch-diagrams/prod-config-diagram.html)
- NVIDIA says configurators can produce 2D renders or video "at scale" for marketing, citing up to 40% time savings. Katana, SAP and WPP have built on the stack. — [NVIDIA developer blog: product configurators with OpenUSD](https://developer.nvidia.com/blog/developing-product-configurators-with-openusd/)
- A June 2026 NVIDIA FAQ describes OpenUSD + SimReady + MDL turning master CAD into cloud-streamed car configurators. — [NVIDIA Perspectives FAQ](https://perspectives.nvidia.com/physical-ai/omniverse/task/faq/software-cloud-streamed-photorealistic-3d-car-configurator/)

### Inferences
- Every commercial automation path needs (a) a paid upper tier (KeyShot Pro-level scripting, Visualize Professional, VRED Professional/Design) and (b) custom scripting for batch-over-files. That puts a recurring cost of about $1,300+/seat/yr before any engineering effort on SMEs.
- The commercial tools are built around one hero project with many cameras or configurations. Batch processing of a catalogue folder of heterogeneous CAD files, with consistent framing and scale, is left to user scripts. This is the gap a free tool can fill.
- Onshape's shaded-views API is the closest thing to a free, headless multi-view generator in commercial CAD. It only works on Onshape-hosted documents, gives OpenGL-style shading, and users report framing problems.

### Gaps
- No official 2026 prices for SOLIDWORKS Visualize, VRED, Siemens NX Render/Teamcenter Visualization, Fusion rendering or Rhino. Not searched in depth because of the call budget.
- Not verified: whether KeyShot's built-in Studios/Render Queue can render a predefined set of orthographic views across many imported models without scripting.
- Fusion (Autodesk), Rhino (Rhino.Compute or Python batch rendering) and Siemens NX/Teamcenter Visualization were not researched in this pass.
- No official source confirms which KeyShot tier includes scripting or headless in the 2026 lineup. The pricing page does not say.

## 2. What does the Blender ecosystem offer (product-render add-ons and CAD/STEP importers)?

### Takeaway
Blender has many cheap ($15-ish to tens of dollars) paid add-ons that set up studio lighting, preset multi-camera rigs (including e-commerce sets and some orthographic sheets) and turntables, plus a free GPL STEP importer on the official extensions platform. The sources found describe single-scene tools. None advertises batch import of STEP/IGES folders with deterministic catalogue naming, contact sheets, trimmed/padded web derivatives and a CSV/JSON manifest.

### Cited Findings
**Product-render and batch add-ons (vendor listings, features not independently verified)**
- **Shot Studio Pro** (Superhive): five camera presets, "E-commerce (5), Marketplace Gallery (6), Hero Shots (4), Turnaround (8) and Orthographic Sheet (4)", a looping turntable exported as PNG frames or MP4, and batch rendering of all or selected cameras. — [Superhive: Shot Studio Pro](https://superhivemarket.com/products/shot-studio-pro)
- **1-Click Product Render Pro** (v1.2.0): one-click camera, lighting and background setup, batch Front/Side/3/4/Top views auto-named and organised, and a turntable. — [Superhive](https://superhivemarket.com/products/1-click-product-render-setup); [ArtStation](https://www.artstation.com/marketplace/p/1KgGK/1-click-product-render-pro-professional-camera-lighting-batch-tools-for-blender)
- **Studio Shot Builder**: generates 4, 6 or 8 product cameras, batch-renders them to PNG, and makes a 360° turntable rendered to H.264 MP4. — [Superhive: Studio Shot Builder](https://superhivemarket.com/products/studio-shot-builder)
- **OneClick Multi-Camera Render** (v3.2.0, $15 on BlenderKit): a multi-angle rig rendered to timestamped folders, no turntable. — [BlenderKit](https://www.blenderkit.com/addons/31b436e2-7cca-442c-aeee-6f7004275252)
- **SpinWiz**: turntable specialist with batch turntables across multiple models, requires Blender 4.1+. — [Blender Market: SpinWiz FAQ](https://blendermarket.com/products/spinwiz/faq)
- **Batch Render Pro** (Blender 5.0+): loads a folder of models and renders each from the selected cameras with render passes, no turntable. — [ArtStation](https://www.artstation.com/marketplace/p/1KBxv/blender-batch-render-pro-addon); see also [Superhive: Batch Render](https://superhivemarket.com/products/batch-render), [Multi-Camera Render Magic docs](https://superhivemarket.com/products/multi-camera-render-magic/docs)

**STEP/CAD importers for Blender**
- **STEP Importer** by Clonephaze is on the official Blender Extensions platform: free, GPL-3.0, imports .step/.stp without external tools using the bundled "cascadio" library, with tessellation quality presets, post-import topology cleanup and "basic material support". It is v1.0.2 for Blender 5.1+ on Windows, macOS and Linux. One review reports a Blender 5.2 break ("Module 'cascadio' has no attribute load"), fixed by reinstalling. — [extensions.blender.org: STEP Importer](https://extensions.blender.org/add-ons/step-importer/); [reviews](https://extensions.blender.org/add-ons/step-importer/reviews/)
- Paid OpenCASCADE-based alternatives: **Cadprep** (STEP/IGES/BREP), **MStep** (Windows-only; its listing reports errors on Blender 5.1+), and a paid "STEP Importer" for Blender 4.2+ claiming assembly hierarchy and parallel tessellation (promotional post, unverified). **StepIO** exports STEP rather than importing it. — [Superhive: Cadprep](https://superhivemarket.com/products/cadprep); [Superhive: MStep](https://superhivemarket.com/products/mstep); [BlenderArtists thread](https://blenderartists.org/t/new-step-importer-native-cad-import-for-blender-4-2/1641518); [Superhive: StepIO](https://superhivemarket.com/products/stepio---blender-step-import--export-add-on)

### Inferences
- The Blender market has the per-scene parts covered: camera rigs, turntables and lighting presets, some including an orthographic sheet. What it lacks is a catalogue pipeline: batch over a folder of CAD files, a fixed standardized view set with consistent scale and framing across products, deterministic naming, image post-processing, contact sheets and a machine-readable manifest. MultiView Product Renderer can claim that niche, provided the claim is worded as "none found advertising" rather than "none exist".
- Most listed add-ons are paid and closed or vendor-distributed. A free, open-source (GPL) add-on on extensions.blender.org would be one of very few.
- STEP import with colours and assembly structure in Blender depends on third-party importers of uneven maturity, and these break across Blender versions. Robust STEP colour and part handling is still a practical risk worth stating as a limitation.

### Gaps
- Not verified whether the free Clonephaze importer keeps STEP part colours and assembly hierarchy. The listing only says "basic material support".
- The "Product Render", "Photographer" and BlenderKit add-ons named in the brief were not looked up specifically.
- Prices for Shot Studio Pro, 1-Click Product Render Pro, Studio Shot Builder and SpinWiz were not captured from the listings.

## 3. What open-source or web-based options exist, and how do part distributors (TraceParts, 3D ContentCentral, CADENAS PARTcommunity) produce previews at scale?

### Takeaway
Open-source tools for STEP-to-image are mostly single-thumbnail utilities or libraries, such as Rust CLIs and OpenCASCADE wrappers, not catalogue renderers. How CADENAS and TraceParts generate preview images for millions of parts is not publicly documented in the sources found.

### Cited Findings
- **Catwalk (catwalk3d, Rust)** is a CLI that renders 3D models, including STEP, to PNG thumbnails on the CPU with no GPU or display server, headless on Linux, macOS and Windows. The docs.rs build for 2.0.0 failed. — [docs.rs: catwalk3d](https://docs.rs/catwalk3d/)
- **cadrum (Rust)** is a parametric CAD library on headless OpenCASCADE that reads and writes STEP/BRep and exports PNG/glTF/STL. It is a toolkit, not a renderer pipeline. — [docs.rs: cadrum 0.8.12](https://docs.rs/crate/cadrum/0.8.12)
- **Adom chip-thumbnailer** (MIT) makes shaded isometric PNGs from STEP for electronic parts. It depends on a separate step2glb/OCCT service, and one page marks it deprecated. — [Adom wiki README](https://wiki.adom.inc/api/pages/adom/adom-chip-thumbnailer/files/README.md); [deprecated notice](https://wiki.adom.inc/api/pages/adom/chip-thumbnailer/files/README.md)
- CADENAS PARTcommunity offers "millions of 3D CAD models from over 400 product catalogs". Version 7 lets manufacturers pin and update preview images and shows an interactive 3D preview. The press material does not say how previews are generated. — [CADENAS: PARTcommunity 7 press release](https://www.cadenas.de/press/reader/partcommunity-7-this-is-what-the-new-download-portal-version-offers-for-engineers-and-purchasers-pr)
- CADENAS reported 86 million 3D part downloads in 2013, which shows the scale of catalogue CAD distribution. — [PARTsolutions press release](https://partsolutions.com/?p=5716)

### Inferences
- Distributor portals show interactive WebGL viewers plus static preview images, likely made by their own server-side tessellation pipelines. Because this is undocumented, the paper should not make claims about their methods. It can say that catalogue-scale preview generation exists in proprietary portals while no open, documented equivalent was found.
- Open-source headless options give one shaded thumbnail per file. They do not give photoreal multi-view sets, turntables or manifests.

### Gaps
- TraceParts, 3D ContentCentral, FreeCAD screenshot/render workbenches, CadQuery/build123d viewers (e.g. ocp_vscode) and three.js thumbnailers were not searched because of the call budget.
- No primary source on CADENAS or TraceParts preview-image generation methods.

## 4. Which tools support the specific capabilities (STEP with parts/colours, standardized multi-view sets, turntables, line/technical drawings, batch over many files with consistent framing, manifests/metadata, headless)?

### Takeaway
From the sources found, no single tool combines all of these in a ready-made, free package. Turntables and multi-camera queues are common. Standardized ortho six-view sets are rare (one Blender add-on offers a 4-view orthographic sheet). Batch over files and headless operation need scripting in paid tools. Manifest/metadata output was not advertised by any tool found.

### Cited Findings
- Turntable one-click: SOLIDWORKS Visualize Professional ([Javelin](https://www.javelin-tech.com/blog/2024/06/how-to-use-solidworks-visualize-professionals-rendering-queue-for-streamlined-design/)); KeyShot animation, with headless animation done frame by frame ([KeyShot pricing](https://www.keyshot.com/pricing/); [KeyShot forum](https://community.keyshot.com/forum/t/headless-hurdles/507)); Blender add-ons Shot Studio Pro, Studio Shot Builder, SpinWiz ([Superhive](https://superhivemarket.com/products/shot-studio-pro); [Superhive](https://superhivemarket.com/products/studio-shot-builder); [Blender Market](https://blendermarket.com/products/spinwiz/faq)).
- Standardized view sets: Shot Studio Pro's "Orthographic Sheet (4)" and e-commerce presets ([Superhive](https://superhivemarket.com/products/shot-studio-pro)); 1-Click Product Render Pro's Front/Side/3/4/Top ([Superhive](https://superhivemarket.com/products/1-click-product-render-setup)); Onshape shaded views via a view matrix ([Onshape forum](https://forum.onshape.com/discussion/17201/how-to-automatically-export-view-images)).
- Batch over many files: KeyShot community script ([KeyShot forum](https://db_e596cbae_9eea_47cf_9859_c9418b6eabfd.influitive.com/forum/t/keyshot-studio-python-script-batch-import-render-automation/14613)); VRED Python batch processing ([Autodesk APS](https://aps.autodesk.com/node/4011)); Blender Batch Render Pro (folder of models) and SpinWiz (batch turntables) ([ArtStation](https://www.artstation.com/marketplace/p/1KBxv/blender-batch-render-pro-addon); [Blender Market](https://blendermarket.com/products/spinwiz/faq)).
- Headless: KeyShot headless scripting, with limitations ([KeyShot 2025 manual](https://manuals.keyshot.com/kss2025/manual/scripting.html)); Onshape REST API ([Onshape forum](https://forum.onshape.com/discussion/18987/api-trying-to-find-a-more-efficient-way-to-pull-thumbnails-for-each-bom-item)); Catwalk CLI ([docs.rs](https://docs.rs/catwalk3d/)).
- Catalogue naming conventions exist in standards. GS1 encodes GTIN, image type, facing, angle and state in file names (e.g. `09520123456740_A1C1`). — [GS1 Primary Images handout](https://gs1.org/docs/images/Primary-Images-handout.pdf)

### Inferences
- Gap matrix for positioning. The rows are fully supported by no tool found:
  1. a fixed, reproducible standard view set (six ortho + perspective) applied identically across a folder of products, with consistent scale and framing;
  2. deterministic, standards-inspired file naming;
  3. post-processing to web derivatives (trim, pad, resize) and contact sheets;
  4. a CSV/JSON manifest;
  5. all of this free and open source, scriptable and headless (Blender `-b`).
- Line/technical-drawing style output (e.g. Freestyle or Line Art) was not advertised by any of the product-render tools found. It is a possible differentiator if the add-on supports it, otherwise a limitation.

### Gaps
- Not verified against current docs whether KeyShot or VRED output metadata or manifest files with renders.
- Line-drawing support in KeyShot ("toon"/contour materials) and Visualize was not checked.

## 5. Is there academic or industry literature on automated product imagery from CAD, and on product-image standards (GS1, Amazon)?

### Takeaway
Academic work on rendering CAD at scale is almost entirely about **synthetic training data for computer vision** (CAD2Render, SynthiCAD, Blender-based pipelines), not catalogue or e-commerce imagery. No peer-reviewed paper on automated catalogue/PIM product-image generation from CAD was found. Industry evidence is anecdotal (IKEA). Strong normative grounding exists in the **GS1 Product Image Specification** (standard facings, plunge angles, naming) and marketplace rules such as Amazon's white background and 85% fill.

### Cited Findings
**Academic (synthetic data from CAD; closest neighbours)**
- **CAD2Render** (Moonen et al.) is a GPU-accelerated photoreal synthetic-data toolkit on Unity HDRP that works from manufacturer CAD, aimed at manufacturing. — [ResearchGate](https://www.researchgate.net/publication/365783734_CAD2Render_A_Modular_Toolkit_for_GPU-accelerated_Photorealistic_Synthetic_Data_Generation_for_the_Manufacturing_Industry); [Zenodo](https://zenodo.org/records/15501381)
- **SynthiCAD** automatically creates customised image datasets from CAD models, tested on 10 industrial objects (engine parts, screws). — [ResearchGate](https://www.researchgate.net/publication/374151177_SynthiCAD_Generation_of_Industrial_Image_Data_Sets_for_Resilience_Evaluation_of_Safety-Critical_Classifiers)
- **CAD2DMD-SET** renders CAD in Blender through its Python API with randomised lighting, orientation and camera distance. — [arXiv 2508.21732](https://arxiv.org/pdf/2508.21732)
- A Blender-Python pipeline for object-to-model deep learning in industrial applications composites renders on SUN backgrounds, with code released. — [arXiv 1909.10976](https://arxiv.org/pdf/1909.10976)
- About 100 synthetic images per CAD design, varying colour, texture, light and camera, for additive-manufacturing segmentation. — [arXiv 2210.07466](https://arxiv.org/pdf/2210.07466)
- DepthSynth produces real-time synthetic depth data from CAD. — [ResearchGate](https://www.researchgate.net/publication/314115413_DepthSynth_Real-Time_Realistic_Synthetic_Data_Generation_from_CAD_Models_for_25D_Recognition)

**Industry case**
- IKEA: about 75% of 2016 catalogue images began as 3D CAD models. This is a secondary report on Onshape's blog. — [Onshape blog](https://www.onshape.com/en/blog/how-to-render-photorealistic-images-like-ikea)

**Standards and marketplace guidelines**
- The GS1 Product Image Specification Standard is at Release 4.4 (ratified April 2024). Earlier releases are 4.0 (May 2021) and 3.6 (Sep 2020, legacy). There is also a separate GS1 Product Image Sharing Guideline (Release 1.0, Dec 2021). — [GS1 current standard](https://www.gs1.org/standards/gs1-product-image-specification-standard/current-standard) (page returned 403 to the fetcher; release and date are from the search index); [GS1 Release 4.0](https://www.gs1.org/standards/gs1-product-image-specification-standard/40); [GS1 Release 3.6](https://gs1.org/standards/gs1-product-image-specification-standard/36); [GS1 Image Sharing Guideline](https://gs1.org/standards/product-image-sharing-guideline/current-standard)
- GS1 angle guidance: a centre front view at 15° top elevation is preferred for 3D images, with left/right 15° rotation views where warranted. A 0° plunge is used for 2D images and for products of negligible depth. Primary-image file names encode GTIN, image type, facing, orientation (Centre/Left/Right/No-plunge) and state, e.g. `09520123456740_A1C1`. — [GS1 Primary Images handout](https://gs1.org/docs/images/Primary-Images-handout.pdf)
- National variations: GS1 New Zealand requires a 2D front shot with no plunge plus a 3D plunge shot, with exemptions such as wine bottles and flat items ≤10 mm deep. GS1 Belgium/Luxembourg makes a front packshot without plunge mandatory for FMCG and foodservice. GS1 Canada publishes its own image submission standard. — [GS1 NZ: what images to supply](https://support.gs1nz.org/hc/en-us/articles/360019561512-What-kind-of-images-do-I-need-to-supply); [GS1 NZ photography specs](https://support.gs1nz.org/hc/en-us/articles/360018596392-What-are-GS1-New-Zealand-s-photography-specifications); [GS1 Belgium/Luxembourg](https://gs1belu.org/en/media/6531/download); [GS1 Canada image submission standard (PDF)](https://gs1ca.org/gs1ca-components/documents/GS1CA_MKTG_Image_Submission_Standard_EN.pdf)
- Amazon main-image rules (mostly third-party summaries): pure white background (RGB 255,255,255), product filling at least 85% of the frame, no text, logos or props, and the full product visible. Extra angles go in secondary images. Minimum resolution claims vary from 500 to 1,000 px on the longest side, with about 1,600 px+ suggested for zoom. The 85% figure is also in a Seller Central forum post. — [Amazon Seller Forums](https://sellercentral.amazon.com/seller-forums/discussions/t/13af96ea-6b07-4bf9-8dbe-a13292c2e3b1); [Jungle Scout](https://www.junglescout.com/resources/articles/amazon-image-requirements/); [SellerSprite](https://www.sellersprite.com/en/blog/amazon-image-requirements)

### Inferences
- There is a clear **literature gap**: rendering CAD at scale is well studied as synthetic data for machine learning (randomised views), but deterministic, standardized, catalogue-grade imagery from CAD (fixed views, consistent framing and scale, naming, manifests) has no academic treatment in what was found. The add-on can be positioned as filling that gap and as reusable for synthetic-data work (via its manifest and deterministic views).
- GS1's facing/plunge/naming model maps onto the add-on's features. Orthographic front/back/left/right/top/bottom correspond to GS1 facings at 0° plunge, the perspective view to a 15° plunge, and catalogue naming to GS1-style deterministic file names. The trim/pad/resize step maps to Amazon's white background and 85% fill. A GS1-compatible naming preset and a 15°-plunge preset would strengthen the positioning. This is a suggestion, not something the sources say.

### Gaps
- The full GS1 4.4 text could not be fetched (HTTP 403). Details on resolution, background, clipping paths, 360° spin images and file format come only from the handout and national-office pages, and were not captured in detail.
- Amazon's official Seller Central image-requirements help page was not retrieved; figures are from third-party guides and a forum post.
- Google Scholar/ASME were not searched directly for "e-commerce product rendering from CAD", "PIM imagery" or "configurator rendering". A targeted Scholar search could still turn up a paper, so state "none found in this search" rather than "none exists".
