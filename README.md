# JupyterLite-Population-Data-Comparison

**[Read the Book](https://jltobias.github.io/JupyterLite-Population-Data-Comparison/book/intro.html) | [Open JupyterLite Lab](https://jltobias.github.io/JupyterLite-Population-Data-Comparison/lab/lab/index.html?path=01_introduction.ipynb) | [Launch Population-Data-Comparison-Viewer](https://jltobias.github.io/JupyterLite-Population-Data-Comparison/viewer/index.html)**

![Project concept: four aligned maps of an imaginary coastal region show district shading, coarse and fine population grids, and settlement patterns above a notebook and comparison chart.](assets/population-comparison-splash.png)

**Compare population estimates, explore their assumptions, and reproduce the analysis in your browser.**

JupyterLite-Population-Data-Comparison implements an initial static teaching version of the visual and quantitative comparison workflows of **POPGRID Viewer** through a **Jupyter Book**, **JupyterLite Lab**, three executable browser notebooks, and a standalone **Population-Data-Comparison-Viewer**. The roadmap will connect these workflows with **RustGIS**, **GeoLibre**, and **JupyterGIS**, with the longer-term goal of becoming a population comparison widget within **[FieldWork](https://digital-twin-ph.github.io/fieldwork/)**.

**Status: implemented synthetic teaching workspace.** The Book, Lab, and standalone viewer share deterministic invented count grids. The viewer provides four linked panels, independent layer selectors, cell inspection, rectangular area comparison, validated rectangular-cell GeoJSON import, coverage, charts, and CSV/JSON/SVG downloads with provenance. **All bundled population counts are synthetic; no real population product is connected.** GIS integrations, real raster workflows, district/polygon summaries, and a FieldWork widget remain planned.

*The splash is an original AI-generated concept illustration with invented geography and illustrative marks. It is not a screenshot, a population dataset, or an analytical result. Generation details are recorded in [assets/README.md](assets/README.md).*

## Inspiration and acknowledgments

**This work is inspired by POPGRID Viewer and the prior research, software, and data stewardship of NASA, NASA's Socioeconomic Data and Applications Center (SEDAC), Columbia University's Center for International Earth Science Information Network (CIESIN), and the POPGRID Data Collaborative.** Credit belongs to the original viewer's developers, researchers, data producers, and supporting institutions.

POPGRID Viewer brought together linked maps, population estimates for user-defined areas, and metadata to help users select suitable datasets. NASA's [2020 update](https://www.earthdata.nasa.gov/news/sedac-updates-global-covid-19-viewer-popgrid-viewer) and [2023 feature article](https://www.earthdata.nasa.gov/news/feature-articles/data-tool-focus-popgrid-viewer) document this work. The latter describes four-panel exploration and a single-panel comparison mode supporting drawn boundaries, uploaded shapefiles, and population-total charts. See the [earlier article URL](https://www.earthdata.nasa.gov/learn/articles/popgrid-viewer-sedac) if the newer URL is unavailable.

The scientific foundation is the **fitness for use** perspective in [Leyk et al. (2019)](https://doi.org/10.5194/essd-11-1385-2019): choose a population product according to the question, geography, time, population definition, and source-data quality. Finer output cells alone do not establish greater accuracy.

This repository is an independent reimplementation under a new project name. It does not claim to be an official NASA, SEDAC, CIESIN, or POPGRID release. Historical viewer links are retained for attribution; future real-data integrations must acquire data from documented, working sources rather than depend on the legacy viewer's services.

## What works now

| Capability | Implemented experience |
| --- | --- |
| Four-panel comparison | Independently select synthetic or imported count layers; synchronize pan/zoom or navigate independently; inspect native cell counts, units, and source metadata. |
| Rectangular area analysis | Draw a rectangle with two clicks, or enter WGS84 bounds. Use spherical overlap fractions with an explicit uniform-within-cell assumption. |
| Coverage and results | Distinguish valid zero counts from NoData; show totals, usable coverage, cell counts, a table and chart. |
| Portable exports | Download CSV, JSON and chart SVG with source, license, year, synthetic status, active bounds and method. Full supplied metadata survive in JSON, CSV `metadata_json`, and SVG descriptions; charts also show visible source credits. |
| Validated count-grid import | Add small nonoverlapping rectangular GeoJSON cells with required source metadata; reject unsupported geometry, invalid/negative/nonfinite counts, oversized cells and files. See [the import contract](book/methods.md#import-contract). |
| Reproducible notebooks | Run three standard-library Python lessons in browser Pyodide: introductory totals, area/coverage semantics, and import/export. The Book renders the same canonical notebooks. |

The shared example rectangle produces **400, 400, 800, and 240** invented people across the four scenarios. The final scenario has incomplete coverage. These illustrate methodological sensitivity and do not establish that any product is correct. Polygon boundaries, administrative summaries, settlement context, real rasters, and GIS handoffs are future work.

## Population data sources

The historical reference set includes **GPW, LandScan, WorldPop, GHS-POP, Esri WPE, and HRSL**. The [GEO Knowledge Hub POPGRID Viewer package](https://gkhub.earthobservations.org/packages/xxb7r-60d58) identifies the example years below. Methods and nominal resolutions are summarized from [Leyk et al. (2019), section 4](https://essd.copernicus.org/articles/11/1385/2019/#section4) and the producer documentation linked here.

| Source and original producer | Historical viewer example / nominal grid size | Allocation approach and inputs |
| --- | --- | --- |
| **Gridded Population of the World (GPW)** — CIESIN / NASA SEDAC | GPWv4 revision 10, 2015 / approximately 1 km | Distributes official subnational census counts in proportion to cell land area, without secondary population covariates. Record whether totals are census-based or UN-adjusted. |
| **LandScan Global** — [Oak Ridge National Laboratory](https://landscan.ornl.gov/) | 2015 / approximately 1 km | Multivariate dasymetric allocation using census counts, imagery, land cover, roads, slope, and settlement information. Represents ambient population averaged across day and night. |
| **WorldPop** — [WorldPop Project](https://www.worldpop.org/methods/) | 2014 estimates / approximately 100 m | Product methods vary. Random-forest approaches derive allocation weights from census and geospatial covariates such as settlements, roads, land cover, and nightlights. Older products also used land-cover-based allocation. |
| **Global Human Settlement Population Grid (GHS-POP)** — European Commission Joint Research Centre and CIESIN | 2015 / 250 m | Allocates census-derived residential population using satellite-derived built-up area. The historical approach used Landsat-based settlement information; later releases have different inputs and allocation models. |
| **Esri World Population Estimate (WPE)** — Esri | 2016 / 150 m | Allocates census counts using settlement weights from land cover, road intersections, populated places, and Landsat imagery texture. |
| **High Resolution Settlement Layer (HRSL)** — Facebook Connectivity Lab and CIESIN | 2015 / approximately 30 m | Detects settlements with machine learning on very-high-resolution imagery, then proportionally allocates census population to identified settlement cells. |

The years reproduce a documented historical comparison and are not a matched-year selection. Metre equivalents for angular grids are approximate and vary with latitude. The [POPGRID Collaborative StoryMap](https://storymaps.arcgis.com/stories/e5f8fa489a9c40d289664975491a6457) provides additional producer context.

Version-specific methods matter. [WorldPop's methods guide](https://www.worldpop.org/methods/) distinguishes land-cover allocation, random-forest redistribution, and bottom-up approaches; the selected 2014 asset's metadata must establish which method it used. As another example, [GHS-POP R2023A](https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php) incorporates built-up volume and classification, so its method should not be described as identical to the earlier built-up-area allocation.

**Integration status:** all six real-data families are candidates for evaluation; none is bundled or connected. The only count grids included are explicitly synthetic teaching fixtures. Census boundaries and contextual settlement layers will complement them. Every supported asset will need a product identifier, version, reference year, population concept, units, CRS, resolution, input-census vintage, method, source citation, access URL, and applicable terms. Historical inclusion in POPGRID does not establish present download access or browser compatibility.

## Data citations, attribution, and use requirements

*Repository inventory and linked provider guidance checked November 6, 2026.*

### What is actually included

| Repository material | Source and attribution status |
| --- | --- |
| `README.md`, `book/`, `notebooks/` | Project description, research citations, executable teaching lessons and methods. No observed population measurements or third-party map images are reproduced. |
| `data/demo.json`, `data/import-example.geojson` | Deterministic invented teaching cells, version 1.0; CC0-1.0. No census, imagery, population, basemap or boundary inputs. [Generation, checksum and license record](data/README.md). Every layer and export records synthetic status. |
| `viewer/`, `scripts/`, `tests/`, `.github/workflows/` | Static comparison app, allowlisted paired-site build, analytical/browser checks, and GitHub Pages deployment. Original project code is [MIT licensed](LICENSE); that license does not relicense third-party data or software. |
| `assets/population-comparison-splash.png` | Project illustration generated with OpenAI's built-in image-generation tool. Its geography and marks are invented. The [image record](assets/README.md) includes the generation date, full prompt, and alternative description. It uses no external population, boundary, imagery, or basemap dataset. |
| `assets/README.md` | Provenance and prompt for the splash illustration. |
| Real population grids, census boundaries, settlement rasters, nighttime lights, and basemap tiles | **Not included, downloaded, or queried by this repository.** The six families above are historical references and future integration candidates. No asset-level data-use clearance is claimed for them. |
| Third-party software | Leaflet 1.9.4 is bundled with its [BSD-2-Clause license](viewer/vendor/leaflet/LICENSE), copyright Vladimir Agafonkin and CloudMade. The build produces Jupyter Book and JupyterLite/Pyodide assets, retaining upstream notices. See [requirements.txt](requirements.txt). RustGIS, GeoLibre, JupyterGIS, and FieldWork are references or future integrations. |

A citation to POPGRID Viewer, this repository, a methods paper, or a hosting mirror does **not** replace the citation and use terms of the dataset actually used. A reference year such as 2015 is not a publication date or release identifier. Keep the original producer's credit when data move to another host.

### Provider-specific citation and use guidance

The entries below record verified guidance and the remaining checks for future data selection. They are not statements that these datasets are currently used. Follow the terms attached to the exact downloaded asset or service, including its notices and any additional attribution parties.

| Candidate source | Citation and credit to carry with any future use | Use conditions and verification status |
| --- | --- | --- |
| **GPW / CIESIN / NASA SEDAC** | Cite CIESIN–Columbia University as creator, NASA SEDAC as the original distributor, the exact product and revision, its DOI, selected population year, and actual retrieval date. The historical unadjusted **Population Count, Revision 10** identifier is [10.7927/H4PG1PPM](https://doi.org/10.7927/H4PG1PPM), listed in [NASA's collection directory](https://cmr.earthdata.nasa.gov/search/site/collections/directory/ESDIS/gov.nasa.eosdis). Density, UN-adjusted counts, and Revision 11 have different identifiers. | The historical identifier is verified; the exact file's license/use-constraint text still needs to be captured from its collection metadata or accompanying documentation. No blanket Creative Commons or public-domain status is assigned here. |
| **LandScan Global / ORNL** | Credit Oak Ridge National Laboratory and use the selected annual release's author list, publication year, dataset title, DOI, and retrieval date. Keep ambient-population semantics in the output. | [ORNL's archive description](https://www.ornl.gov/project/geospatial-data-sets) states that its archive is available under a Creative Commons license, but does not identify the complete variant on that page. Capture the exact annual download's license and citation before bundling, caching, or redistribution; historical distributor terms must not be substituted for the current asset's terms. |
| **WorldPop** | Include [WorldPop](https://www.worldpop.org/) as the source and the selected dataset's recommended author/title/version citation and DOI. Include the relevant methods paper in addition when describing its modeling. Country, year, constrained/unconstrained status, and UN-adjustment variant belong in the provenance. | The [provider FAQ](https://www.worldpop.org/faq/) describes CC BY 4.0 and asks for dataset-specific citations. **Check the release statement:** the [Mali 2020 v1.0 release](https://data.worldpop.org/repo/wopr/MLI/population/v1.0/MLI_population_v1_0_README.pdf), for example, specifies **CC BY-SA 4.0**. This is an illustration of differing terms, not data used here. |
| **GHS-POP / European Commission JRC** | Credit the European Commission/JRC and retain the dataset's attribution parties, including CIESIN where specified. Cite the exact product/release DOI and the release publication requested by [GHSL's citation instructions](https://human-settlement.emergency.copernicus.eu/GHSLhowToCite.php). The R2023A dataset citation appears in reference 9; the requested 2024 GHSL publication appears in reference 10. Neither identifies an unselected historical 2015 asset. | Current GHSL guidance specifies **CC BY 4.0**, source acknowledgment, disclosure of modifications, and no implied endorsement. It explicitly asks for the release's peer-reviewed publication and applicable product citation; a generic website credit is insufficient. Retrieve the historical release's own metadata if reproducing the earlier viewer. |
| **Esri World Population Estimate (WPE)** | Credit Esri and every source named by the selected ArcGIS item's credits. Record its item ID, service URL, title, release/reference year, access date, and methodology. The [2016 WPE methodology](https://www.esri.com/content/dam/esrisites/en-us/media/technical-papers/2016-world-population-estimate-methodology.pdf) documents the historical product; it does not grant data redistribution rights. | **Exact item-level terms remain unverified.** Read the chosen item's Terms of Use, credits, service restrictions, and applicable [Esri data terms](https://www.esri.com/en-us/legal/terms/data-attributions). Confirm rights separately for display, querying, caching, downloads, and redistribution. Public visibility is not a license; another Esri layer's terms do not establish WPE's terms. |
| **HRSL / Facebook Connectivity Lab or Meta, and CIESIN** | Use the author names and publication year supplied by the selected release. The [Meta-managed AWS record](https://registry.opendata.aws/dataforgood-fb-hrsl/) provides its recommended citation, naming Meta and CIESIN–Columbia University, and the source-imagery notice **© 2016 Maxar**. Retain the imagery notice supplied with a historical file, which may name DigitalGlobe instead, and record country, version, and actual access date. | The linked AWS distribution specifies **CC BY 4.0**. Verify the particular historical or updated asset rather than silently replacing its citation with the current distribution's citation. Rights to the population product do not establish rights to redistribute its underlying commercial satellite imagery. |

For material actually supplied under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), retain supplied creator and attribution-party credits, copyright/license/disclaimer notices, a source link, and a license link; identify modifications and preserve earlier modification notices. Do not imply endorsement or add restrictions that conflict with that license. A **CC BY-SA** release also has adaptation-sharing conditions: retain its exact license and apply its requirements to shared adapted material. These summaries do not replace the [CC BY legal code](https://creativecommons.org/licenses/by/4.0/legalcode) or [CC BY-SA legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode).

### Boundaries, context layers, and basemaps

No providers have yet been selected for real administrative boundaries, settlement footprints, urbanisation, nighttime lights, or basemaps. The current viewer draws synthetic count cells locally without a basemap service. Their citations cannot be inferred from the population source or from the earlier POPGRID screenshot. Add the following when those layers are selected:

- **Administrative boundaries and census tables:** issuing statistical or mapping agency, collection/title, administrative level, vintage, version, source URL, and its actual use terms. Preserve the credits and notices of any boundary distributor as well as the underlying producer when required.
- **Settlement, built-up, and urbanisation layers:** cite the specific product, such as GHS-BUILT or GHS-SMOD, independently of GHS-POP; a population-product citation does not cover separate input layers downloaded for this project. Identify the actual World Settlement Footprint release if one is chosen.
- **Nighttime lights:** identify the particular VIIRS/DMSP/dLIGHT product, processing provider, version, years, DOI, and required notices. These product families are not interchangeable citations.
- **Basemaps and map services:** preserve all provider credits visibly on maps and in exported figures, including third-party imagery or tile credits. If OpenStreetMap is selected, follow the [OSM attribution and ODbL guidance](https://www.openstreetmap.org/copyright); using OSM data and using a particular tile service also require checking that service's terms. OpenStreetMap is not currently used by this repository.

### Requirements for future notebooks and exports

Before adding a file, enabling a live source, or publishing a derived result, maintainers must:

1. Record the exact asset's creator, title, publication date, product/reference year, version, country/extent, variable/units, DOI or stable source URL, and actual retrieval date. Preserve its provider-supplied citation, license URL/text, notices, and attribution parties; include a checksum for committed or prepared data files.
2. State whether the source is bundled, fetched remotely, or used only as a reference. Verify the permissions needed for that use, including browser caching and redistribution. Keep asset-level license records with the data; a repository software license must not be presented as relicensing third-party data.
3. Add the dataset citation and applicable methods/software citations to the notebook, corresponding Book page, and this README. Document changes such as clipping, resampling, density conversion, aggregation, or modified classifications.
4. Keep credits on maps and figures. Include citations, license links/notices, selected versions/years, and processing provenance with CSV, GeoJSON, raster, and project exports, using a companion metadata file where necessary. A result exported to FieldWork or another GIS must retain this information.
5. Mark synthetic fixtures explicitly. Record the actual source of real teaching data; do not relabel an observed dataset as synthetic. A source that is unselected or whose required terms remain unverified stays a candidate rather than a bundled example.

## Read, run, and explore

The learning route has three connected parts:

1. **Read the Book.** Follow the three rendered notebooks and the method, coverage, import and provenance explanations.
2. **Run the same notebooks in JupyterLite Lab.** Choose **Run → Run All Cells**. The introductory notebook asserts the shared teaching totals; the export notebook creates downloadable files in `outputs`.
3. **Explore the standalone viewer.** Select independent grids, define a rectangle, inspect coverage, import supported count cells and export results.

The first Lab kernel start needs a connection to retrieve its pinned Pyodide runtime and kernel packages. Population calculations use bundled files and do not call remote population services. Browser storage holds your Lab changes and outputs; download files to keep them. The current site does not promise a prepared offline Lab environment. RustGIS Web, GeoLibre, JupyterGIS and FieldWork handoffs remain future validation work.

### Build and verify locally

Use Python 3.12 or 3.13. Native Node/npm are not required.

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m unittest discover -s tests -v
python scripts/build_site.py
python scripts/check_browser.py
python -m http.server 8000 --directory _site
```

Open `http://localhost:8000/` for the local workspace. The browser check mounts it at `/JupyterLite-Population-Data-Comparison/` to verify GitHub Pages prefix handling, exercises viewer interactions and downloads, and executes the actual introductory JupyterLite notebook in Chromium. The Book build also executes all three canonical notebooks. On Windows, kernel/browser subprocesses may need an environment that permits launching child processes.

`scripts/build_site.py` copies approved course assets into `_site` and excludes development metadata and machine configuration. It builds the Book and Lab from canonical `notebooks/` and `data/` files; `_site/publication.json` records their hashes. `.github/workflows/deploy.yml` repeats checks and builds, uploads `_site`, and deploys GitHub Pages on pushes to `main`. Set the repository's Pages source to **GitHub Actions**. The Lab runtime is served by the installed pinned Pyodide extension; initial runtime downloads require network access.

## Browser GIS ecosystem and related repositories

Two companion repositories inform the approach:

- **[JupyterLite-GeoLibre-GeoAI](https://github.com/jltobias/JupyterLite-GeoLibre-GeoAI)** demonstrates a paired Book/Lab learning environment, browser-oriented map adapters, data provenance, and exports between notebook and GIS interfaces.
- **[JupyterLite-RustGIS](https://github.com/jltobias/JupyterLite-RustGIS)** demonstrates notebook-to-RustGIS Web handoffs and distinguishes browser workflows from native Python integrations.

| Component | Proposed role here | Runtime considerations |
| --- | --- | --- |
| [RustGIS](https://github.com/opengeos/RustGIS) / [RustGIS Web](https://web.rustgis.app/) | Explore exported study boundaries and comparison layers in a browser GIS. | Begin with supported file and hosted-data handoffs. The companion course documents that the native Python binding cannot run in Pyodide; embedding and browser messaging need separate validation. |
| [GeoLibre](https://github.com/opengeos/GeoLibre) | Display supported population and boundary layers and exchange map projects. | Evaluate the companion repository's browser adapter and hosted-viewer approach. Its documentation distinguishes that approach from a Python widget requiring a kernel-side server. |
| [JupyterGIS](https://jupytergis.readthedocs.io/en/latest/) | Offer a GIS workspace alongside notebook analysis, using compatible layers and project formats. | Test the JupyterLite extension explicitly. The [upstream preview limitations](https://jupytergis.readthedocs.io/en/latest/user_guide/explanation/jupyter-lite-limitations.html) document unavailable server-dependent features; full JupyterGIS feature parity is not assumed. |
| [JupyterLite / Pyodide](https://jupyterlite.readthedocs.io/en/stable/) | Execute notebook calculations locally in the browser. | Package compatibility, memory, browser storage, and remote-data access constrain the supported workload. |

The intended default is a static site with browser-side computation. Initial loading, package retrieval, remote datasets, and external GIS viewers may still require connectivity. Offline workflows will need explicit preparation and testing. Fetching large rasters must account for CORS, HTTP range requests, and bounded data windows; a visible map tile is not a substitute for analytical population values.

## Comparing population products responsibly

The notebook design will make these analytical choices explicit:

- **Population definition and time:** record residential versus ambient population, product year, and input census dates. Cross-year differences can reflect both population change and changes in data or methods.
- **Counts and density:** sum counts; convert density to population using the corresponding cell area before aggregation. Apply shared density legends only to comparable units.
- **Spatial support:** preserve native analytical values and document reprojection, resampling, area calculation, and partial-cell treatment. Display zoom does not change source resolution.
- **Missing coverage:** distinguish zero population from NoData, masked areas, and unavailable coverage. Report the usable coverage of each comparison.
- **Difference calculations:** name the reference product and handle zero denominators explicitly. Retain per-product results when grids do not align.
- **Interpretation:** disagreement measures sensitivity to dataset choice; it does not by itself provide a confidence interval or identify a correct product. Record ancillary inputs that could make a proposed downstream analysis circular.

These principles extend the fitness-for-use framing of [Leyk et al. (2019)](https://doi.org/10.5194/essd-11-1385-2019) into the proposed notebook workflow. Product-specific citations and processing choices must travel with exported results.

## Toward a FieldWork widget

The larger goal is to make population comparison available inside **[FieldWork](https://digital-twin-ph.github.io/fieldwork/)** as a reusable workflow operation. FieldWork's [source documentation](https://github.com/digital-twin-ph/fieldwork) describes typed workflow widgets, browser-side computation, and provenance receipts. Its [widget registry](https://github.com/digital-twin-ph/fieldwork/blob/main/widgets/README.md) describes contracts and admission requirements; it is not a general executable plugin loader.

The proposed integration will therefore start with an inspectable exchange of inputs and results, followed by a host-compatible implementation. The following is a conceptual contract, not a registered widget or an existing FieldWork API:

| Proposed part | Information to carry |
| --- | --- |
| Inputs | Study-area geometry and CRS; selected product identifiers, versions, and years; prepared raster windows or asset references; aggregation settings. |
| Outputs | One result per area/product/year, with estimated population, units, usable coverage, and method; optional geometries for map display. |
| Provenance | Source citations and terms, asset identity, retrieval dates, processing choices, software versions, and comparison parameters. |
| Presentation | Linked maps, comparison tables and charts, plus a route to the explanatory Book chapter and executable notebook. |

Dataset acquisition should be separated from calculation so a run can use prepared, identified inputs. Independent notebook calculations will provide a way to check the future widget's results against stated tolerances and boundary rules. Mapping this proposal onto FieldWork's actual ports, ontology, release contracts, and validation process remains implementation work.

## Roadmap

- [x] Introduce the project, acknowledge prior work, and add the splash image.
- [x] Build the Jupyter Book and JupyterLite Lab from shared notebook sources and add GitHub Pages publication.
- [ ] Create a versioned source inventory for all six historical population families and verify access, terms, units, and browser compatibility for selected assets.
- [x] Add a small reproducible synthetic population-comparison example with source metadata and expected totals.
- [x] Implement linked panels, rectangular boundary input, coverage, and downloadable tables and charts.
- [ ] Add polygon boundaries and administrative district summaries.
- [ ] Verify browser workflows with RustGIS, GeoLibre, and JupyterGIS.
- [ ] Validate real-data comparisons across products, including coverage and boundary handling.
- [ ] Develop and validate the FieldWork integration against the host's current widget contracts.

Contributions are welcome in population-data sourcing, browser raster analysis, accessible cartography, teaching notebooks, GIS interoperability, and FieldWork integration. Each implemented feature should include an executable example, source attribution, and evidence of what was checked in the browser.

## References and credits

### POPGRID research, viewer, and institutional work

1. **Leyk, S., Gaughan, A. E., Adamo, S. B., de Sherbinin, A., Balk, D., Freire, S., Rose, A., Stevens, F. R., Blankespoor, B., Frye, C., Comenetz, J., Sorichetta, A., MacManus, K., Pistolesi, L., Levy, M., Tatem, A. J., and Pesaresi, M. (2019).** *The spatial allocation of population: a review of large-scale gridded population data products and their fitness for use.* Earth System Science Data, **11**, 1385–1409. [DOI: 10.5194/essd-11-1385-2019](https://doi.org/10.5194/essd-11-1385-2019).
2. **Smith, Joseph M. (2023, October 31).** *Data Tool in Focus: POPGRID Viewer.* NASA Earthdata. [Feature article](https://www.earthdata.nasa.gov/news/feature-articles/data-tool-focus-popgrid-viewer) · [Earlier article URL](https://www.earthdata.nasa.gov/learn/articles/popgrid-viewer-sedac). Documents the viewer's comparison workflows and the work of SEDAC, CIESIN, and POPGRID.
3. **NASA Earthdata / SEDAC (2020, July 3).** *SEDAC Updates Global COVID-19 Viewer and POPGRID Viewer.* [NASA announcement](https://www.earthdata.nasa.gov/news/sedac-updates-global-covid-19-viewer-popgrid-viewer).
4. **CIESIN / SEDAC (2022, July 27).** *POPGRID Viewer tool.* GEO Knowledge Hub, Earth Observations Toolkit for Sustainable Cities and Human Settlements. [Tool record](https://gkhub.earthobservations.org/records/5ar2q-as677).
5. **POPGRID Data Collaborative.** [Collaborative website](https://www.popgrid.org/) · [Dataset comparison resources](https://www.popgrid.org/compare-data). Credit the collaborative and each original producer when using its resources.
6. **SEDAC / CIESIN.** *POPGRID Viewer*, [historical application endpoint](https://sedac.ciesin.columbia.edu/mapping/popgrid/). For service history, see the [NASA Earthdata Forum response dated September 22, 2025](https://forum.earthdata.nasa.gov/viewtopic.php?t=7126), which reports SEDAC's contract termination, relocation of datasets, and the unresolved viewer link. Dataset relocation does not establish viewer availability.
7. **CIESIN / SEDAC (2022, July 27).** *POPGRID Viewer.* GEO Knowledge Hub knowledge package. [DOI: 10.60566/xxb7r-60d58](https://doi.org/10.60566/xxb7r-60d58) · [Package and historical six-dataset list](https://gkhub.earthobservations.org/packages/xxb7r-60d58).
8. **WorldPop Project.** *Methods.* [Producer methods guide](https://www.worldpop.org/methods/). For the random-forest method, see **Stevens, F. R., Gaughan, A. E., Linard, C., and Tatem, A. J. (2015).** *Disaggregating Census Data for Population Mapping Using Random Forests with Remotely-Sensed and Ancillary Data.* PLOS ONE, **10**(2), e0107042. [DOI: 10.1371/journal.pone.0107042](https://doi.org/10.1371/journal.pone.0107042).
9. **Schiavina, M., Freire, S., Carioli, A., and MacManus, K. (2023).** *GHS-POP R2023A — GHS population grid multitemporal (1975–2030).* European Commission, Joint Research Centre. [Producer documentation](https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php) · [DOI: 10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE](https://doi.org/10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE). An example of a later release, rather than a claim about the historical viewer's version.
10. **Pesaresi, M., Schiavina, M., Politis, P., Freire, S., et al. (2024).** *Advances on the Global Human Settlement Layer by joint assessment of Earth Observation and Population Survey data.* International Journal of Digital Earth, **17**(1). [DOI: 10.1080/17538947.2024.2390454](https://doi.org/10.1080/17538947.2024.2390454) · [JRC publication record and full author list](https://publications.jrc.ec.europa.eu/repository/handle/JRC136539). The current [GHSL use/citation instructions](https://human-settlement.emergency.copernicus.eu/GHSLhowToCite.php) request this release publication along with applicable product citations.

### Data citation and license records

These records document candidate sources and citation requirements. They are not an inventory of data already used:

- **CIESIN–Columbia University (2017).** *Gridded Population of the World, Version 4 (GPWv4): Population Count, Revision 10.* NASA Socioeconomic Data and Applications Center (SEDAC), Palisades, NY. [DOI: 10.7927/H4PG1PPM](https://doi.org/10.7927/H4PG1PPM). This identifier is for the historical count product, not every GPW variant; [NASA's directory](https://cmr.earthdata.nasa.gov/search/site/collections/directory/ESDIS/gov.nasa.eosdis) lists the variants separately. No retrieval date for a data file is claimed.
- **ORNL:** [LandScan archive description](https://www.ornl.gov/project/geospatial-data-sets) and [LandScan distribution portal](https://landscan.ornl.gov/). The annual file's recommended citation and complete license must be recorded when an asset is selected.
- **WorldPop:** [FAQ: citation and redistribution guidance](https://www.worldpop.org/faq/) and [methods guide](https://www.worldpop.org/methods/). The specific 2014 country/product asset remains unselected. **WorldPop and Institut National de la Statistique du Mali (2022),** *Census-cartography-based gridded population estimates for Mali (2020), version 1.0*, [DOI: 10.5258/SOTON/WP00745](https://doi.org/10.5258/SOTON/WP00745), is cited here only as an example whose [release statement](https://data.worldpop.org/repo/wopr/MLI/population/v1.0/MLI_population_v1_0_README.pdf) specifies CC BY-SA 4.0.
- **European Commission/JRC:** [GHSL use conditions and citation instructions](https://human-settlement.emergency.copernicus.eu/GHSLhowToCite.php), with the versioned dataset and publication references above.
- **Esri:** *2016 World Population Estimate Methodology*, [technical paper](https://www.esri.com/content/dam/esrisites/en-us/media/technical-papers/2016-world-population-estimate-methodology.pdf), and [data attributions and terms](https://www.esri.com/en-us/legal/terms/data-attributions). An exact count/density service item and its dataset citation/use terms remain to be verified.
- **Meta and CIESIN–Columbia University (2022).** *High Resolution Settlement Layer (HRSL).* [Meta-managed distribution record, recommended citation, and CC BY 4.0 notice](https://registry.opendata.aws/dataforgood-fb-hrsl/). That record also credits the source imagery to Maxar with a 2016 copyright notice. This is a later distribution record, not a substitute citation for the unselected 2015 historical asset; add the real file-access date when data are retrieved.
- **Creative Commons:** [CC BY 4.0 attribution conditions](https://creativecommons.org/licenses/by/4.0/) and [CC BY-SA 4.0 conditions](https://creativecommons.org/licenses/by-sa/4.0/).

### Software and related work

- **Project Jupyter and contributors:** [JupyterLite](https://jupyterlite.readthedocs.io/en/stable/) and [JupyterGIS / GeoJupyter](https://jupytergis.readthedocs.io/en/latest/).
- **Pyodide contributors:** [Pyodide documentation](https://pyodide.org/en/stable/) and [source](https://github.com/pyodide/pyodide), the browser Python runtime used by the teaching notebooks.
- **Jupyter Book and MyST contributors:** [Jupyter Book documentation](https://jupyterbook.org/stable/).
- **Wu, Q. (2026).** *GeoLibre.* [DOI: 10.5281/zenodo.20785400](https://doi.org/10.5281/zenodo.20785400) · [upstream recommended citation](https://github.com/opengeos/GeoLibre/blob/main/CITATION.cff). The citation file identifies MIT licensing; cite the version actually used when integrated.
- **Wu, Q., Rincón Albarracín, J. G., Filho, E., Hofbauer, D., Fitzgerald, M., and Strebel, D. (2026).** *RustGIS: A fast, free and open-source GIS in pure Rust for mapping, analyzing and sharing geospatial data.* [DOI: 10.5281/zenodo.23633281](https://doi.org/10.5281/zenodo.23633281) · [upstream recommended citation](https://github.com/opengeos/RustGIS/blob/main/CITATION.cff). The citation file identifies Apache-2.0 licensing; cite the version actually used when integrated.
- **James L. Tobias / jltobias:** [JupyterLite-GeoLibre-GeoAI](https://github.com/jltobias/JupyterLite-GeoLibre-GeoAI) and [JupyterLite-RustGIS](https://github.com/jltobias/JupyterLite-RustGIS), companion workflow and teaching references.
- **digital-twin-ph and FieldWork contributors:** [FieldWork application](https://digital-twin-ph.github.io/fieldwork/) and [source repository](https://github.com/digital-twin-ph/fieldwork), the proposed host integration.

Future notebooks and exports will cite the particular population datasets, administrative boundaries, basemaps, and software versions they actually use. Those materials retain their own licenses and attribution requirements. When incorporating upstream code, distributions, or artwork, preserve the relevant license files and notices in addition to these scholarly acknowledgments.
