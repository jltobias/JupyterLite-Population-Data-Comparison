# Credits and provenance

This independent project is inspired by POPGRID Viewer; it is not an official NASA, SEDAC, CIESIN or POPGRID release.

- Leyk, S., et al. (2019). *The spatial allocation of population: a review of large-scale gridded population data products and their fitness for use.* ESSD 11, 1385–1409. [DOI](https://doi.org/10.5194/essd-11-1385-2019).
- NASA Earthdata / Joseph M. Smith (2023). [Data Tool in Focus: POPGRID Viewer](https://www.earthdata.nasa.gov/news/feature-articles/data-tool-focus-popgrid-viewer). Credit its developers, researchers, data producers, SEDAC/CIESIN, NASA and the [POPGRID Data Collaborative](https://www.popgrid.org/).
- Historical [GEO Knowledge Hub knowledge package](https://doi.org/10.60566/xxb7r-60d58).

## Real source excerpts

All four are CC BY 4.0. Native-pixel spatial subsetting and lossless count/null serialization are modifications; there is no producer endorsement. Retrieval date: 2026-11-06. Preserve the full per-layer notices in <a href="../data/population.json">canonical metadata</a> and the <a href="../data/README.md">data provenance record</a>.

- **WorldPop / University of Southampton:** Bondarenko et al. (2025), *Estimates of 2015–2030 total number of people per grid square at 3 arcseconds, R2025A v1*, Global Demographic Data Project. [DOI](https://doi.org/10.5258/SOTON/WP00839). Gates Foundation INV-045237. The complete recommended author citation and source item/asset identity are retained. Alpha public release.
- **GRID3 Inc.; WorldPop; CIESIN / Columbia Climate School:** Nnanatu C.C., Gadiaga A., Abbott T.J., Chamberlain H., Lazar A.N., Tatem A.J. (2025), *Modelled gridded population estimates for Nigeria 2025 version 3.0*. [DOI](https://doi.org/10.5258/SOTON/WP00782). Gates Foundation INV-044979. Operational model estimates, not official government statistics; no warranties.
- **Oak Ridge National Laboratory:** Rose A., McKee J., Sims K., Bright E., Reith A., Urban M. (2021), *LandScan Global 2020*. [DOI](https://doi.org/10.48690/1523378), [producer licensing](https://landscan.ornl.gov/licensing). Native pixels were read from a pinned Hugging Face analytical mirror. Independent ORNL statistics match the prepared native window and a single cell; this does not establish full-file mirror bit identity.
- **European Commission/JRC:** Schiavina M., Freire S., Carioli A., MacManus K. (2023), *GHS-POP R2023A*. [DOI](https://doi.org/10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE). Also Pesaresi et al. (2024), [release paper](https://doi.org/10.1080/17538947.2024.2390454). `(c) European Union, 1995-2026`. Retain <a href="../data/real/ghsl_copyright.txt">the product copyright notice</a>, license, credits and no-endorsement statement. These excerpts use the official JRC source, not a lossy quantized mirror.

GPW historical citations remain in the repository README; no GPW pixels are bundled. GPW's current Harvard Dataverse access uses a guestbook. HRSL and Esri WPE are historical candidates; no pixels from them are included. Discovery resources such as STAC Index are not data producers or evidence of browser-readable numerical assets.

## Other bundled material

Explicit synthetic test/lesson fixtures in `demo.json` and `import-example.geojson`: JupyterLite-Population-Data-Comparison contributors (2026), *Invented comparison cells*, version 1.0, CC0-1.0. They never replace failed real-data loading.

Project Jupyter / JupyterLite, Pyodide, Jupyter Book / MyST and their contributors retain upstream notices. Viewer maps use <a href="../viewer/vendor/leaflet/LICENSE">Leaflet 1.9.4 / BSD-2-Clause</a>. Local TIFF reading uses <a href="../viewer/vendor/geotiff/README.md">GeoTIFF.js 3.0.5 / MIT with dependency notices</a>, reused from pinned JupyterLite-STAC-Browser revision `945d8b31c59e2cf93f9e51e855eb062fb1b4321c`; its MIT notice is retained. Project code is <a href="../LICENSE">MIT licensed</a>, without relicensing source data or third-party software.

The AI-generated splash remains an illustration with its <a href="../assets/README.md">generation record</a>; it is not an analytical screenshot. RustGIS, GeoLibre, JupyterGIS, JupyterLite-GeoLibre-GeoAI, JupyterLite-RustGIS and FieldWork remain acknowledged related work and future integrations.
