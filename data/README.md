# Real native population excerpts

Prepared Greater Lagos extent `[3.2,6.35,3.6,6.7]`; native edge cells retained. All values are people per native cell. No resampling, scale conversion or rounding. Numeric zero is valid; null preserves source NoData. All four products are CC BY 4.0 with attribution and modification disclosure; no endorsement. Retrieved 2026-11-06.

`population.json` SHA-256: `47af4721b74f64aa1b57a9ae01fb9d1780a8dda9060e140982e4d31e143efb59`

Each regular grid stores width/height, west/north, positive dx/dy and row-major counts/nulls. Canonical Book/Lab copies are exact. The viewer uses the same arrays. Detailed geometry, original dtype/NoData, source/output hashes and extraction windows appear in `real/preparation.json`. Independent source-derived expectations are in `real/independent_oracle.json`; tiny coverage excess is clamped to one by the analysis. Normal builds do not fetch sources. Explicit preparation uses `scripts/prepare_population.py` and optional `requirements-raster.txt`, preserving ignored source cache.


## WorldPop Global2 2025

Bondarenko M., Priyatikanto R., Tejedor-Garavito N., Zhang W., McKeen T., Cunningham A., Woods T., Hilton J., Cihan D., Nosatiuk B., Brinkhoff T., Tatem A., Sorichetta A.. 2025 Estimates of 2015-2030 total number of people per grid square at a resolution of 3 arc (approximately 100m at the equator) R2025A version v1. Global Demographic Data Project - Funded by The Bill and Melinda Gates Foundation (INV-045237). WorldPop - School of Geography and Environmental Science, University of Southampton.

 DOI:10.5258/SOTON/WP00839

Source: WorldPop, University of Southampton. WorldPop / University of Southampton. Gates Foundation INV-045237.

Release: R2025A v1 (alpha public release). Reference: 2025-01-01. Residential population estimate. Native 3 arcseconds (~100 m). -99999 denotes NoData, distinct from numeric zero.

Asset: https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2025/NGA/v1/100m/constrained/nga_pop_2025_CN_100m_R2025A_v1.tif

Spatial subset and lossless count/null serialization; no resampling. No producer endorsement. Retrieval: 2026-11-06.


## GRID3 Nigeria 2025

Nnanatu C.C., Gadiaga A., Abbott T.J., Chamberlain H., Lazar A.N., Tatem A.J. (2025). Modelled gridded population estimates for Nigeria 2025 version 3.0. WorldPop, University of Southampton. https://doi.org/10.5258/SOTON/WP00782

Source: GRID3 Inc.; WorldPop; CIESIN, Columbia Climate School. GRID3 Inc.; WorldPop; CIESIN / Columbia Climate School. Gates Foundation INV-044979. Operational estimates, not official government statistics; no warranties.

Release: Nigeria v3.0. Reference: 2025-07. Residential modelled population estimate. Native ~3 arcseconds (~100 m). NaN: mapped unsettled within Nigeria; outside national boundary: outside coverage. Not zero..

Asset: https://data.worldpop.org/repo/wopr/NGA/population/v3.0/NGA_population_v3_0_gridded.zip

Spatial subset and lossless count/null serialization; no resampling. No producer endorsement. Retrieval: 2026-11-06.


## LandScan Global 2020

Rose A., McKee J., Sims K., Bright E., Reith A., Urban M. (2021). LandScan Global 2020. Oak Ridge National Laboratory. https://doi.org/10.48690/1523378

Source: Oak Ridge National Laboratory (pixels retrieved from pinned Hugging Face mirror). Oak Ridge National Laboratory. https://landscan.ornl.gov/licensing

Release: LandScan Global 2020. Reference: 2020. Ambient population (24-hour average). Native 30 arcseconds (~1 km). -2147483647 denotes NoData; numeric zero valid.

Asset: https://huggingface.co/datasets/Daksh17440/global_population_data/resolve/404bde4c5b56347cbce2e1824890246872a89aef/landscan-global-2020.tif

Spatial subset and lossless count/null serialization; no resampling. No producer endorsement. Retrieval: 2026-11-06.


## GHS-POP 2025

Schiavina M., Freire S., Carioli A., MacManus K. (2023). GHS-POP R2023A: GHS population grid multitemporal (1975–2030). European Commission/JRC. https://doi.org/10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE; Pesaresi et al. (2024). https://doi.org/10.1080/17538947.2024.2390454

Source: European Commission, Joint Research Centre. (c) European Union, 1995-2026. CC BY 4.0. Spatial subset / serialization; no endorsement.

Release: R2023A E2025 WGS84 30ss V1.0. Reference: 2025 projection. Residential population projection. Native 30 arcseconds (~1 km), distinct grid offset. No declared NoData; zero remains valid, including water.

Asset: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/GHS_POP_E2025_GLOBE_R2023A_4326_30ss/V1-0/tiles/GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0_R9_C19.zip

Spatial subset and lossless count/null serialization; no resampling. No producer endorsement. Retrieval: 2026-11-06.


LandScan is from a pinned mirror; the mirror-published full hash was not independently recalculated. Independently retrieved ORNL one-cell and snapped-window statistics match mirrored native counts, not full-file bit identity. Preserve `real/comparison_source_provenance.json` and the two ORNL receipts. GHS-POP uses official JRC pixels; retain `real/ghsl_copyright.txt` and the 2024 release-paper citation. WorldPop and GRID3 share producers/inputs; GHS-POP uses GPWv4.11. Different reference dates and residential/ambient concepts limit comparisons; agreement is not independent validation.

GPW is not bundled. Its current Harvard Dataverse access has a guestbook; this project collects no personal information. WorldPop/GRID3 file servers currently lack browser CORS/range support. The bundled regional excerpts and local-file native-window import do not promise global streaming. User-file provenance remains a declaration; file geometry and selected window are checked locally.

# Synthetic teaching fixture

**The two fixture files in this section contain invented counts.** No observed population, census, imagery, boundary or basemap data are included. Coordinates define an arbitrary teaching rectangle, not a statement about actual population at that location. These are not GPW, WorldPop, LandScan, HRSL, GHS-POP, or Esri WPE data.

Creator/citation: JupyterLite-Population-Data-Comparison contributors (2026). *Invented comparison cells*, version 1.0. Generated locally on 2026-11-06 by `python scripts/generate_demo.py`, using deterministic arithmetic and no real inputs. Reference year 2020 is an invented scenario label; there is no input-census vintage or retrieval date. The generated teaching cells in `demo.json` and `import-example.geojson` are dedicated under **CC0-1.0**: https://creativecommons.org/publicdomain/zero/1.0/. This does not license any candidate third-party dataset.

`demo.json` SHA-256: `a5e1ea8866db3d1b98643ce7acbc67cd182c1bc9034aa82105cf488640040f1f`

`import-example.geojson` SHA-256: `d9a9f3e03c3a581729da1a96d3dbbe66e73623654f7f70f45084e101e046299c`

Both files are generated with UTF-8 and LF newlines so checksums are stable across Windows and Linux checkouts.

The fixture contract is `{schema_version, description, bounds, default_aoi, layers}`. Each layer contains a complete `metadata` record and nonoverlapping `{bounds: [west,south,east,north], population: count}` cells in EPSG:4326. Missing cells are NoData. Numeric zero is valid count coverage. Layer metadata record title, creator/source, citation, license and URL, version, year, synthetic status, units, CRS, resolution, population concept, allocation method, census vintage and generation history.

The four scenarios illustrate equal allocation, invented settlement weights, an invented daytime redistribution, and missing coverage. The first three have full-grid totals of 1,600; the fourth totals 960 over available cells. The shared example bounds `[120.1, 14.1, 120.3, 14.3]` give **400, 400, 800, 240** with spherical area weighting. The fourth has approximately 75% coverage; latitude affects the exact area fraction. There is no empirical claim that any scenario is more accurate.

`import-example.geojson` is a rectangular-cell FeatureCollection derived directly from the uniform synthetic layer, with a distinct import id. It is compatible with the viewer's documented import contract. The Python helper and viewer apply `cell_count × spherical_overlap_area / spherical_cell_area`, assuming uniform population within each cell. Exports retain all metadata. CSV's `metadata_json` column retains additional notices as well as the convenient core columns.

The Book and Lab receive exact copies of canonical real-data notebooks, helper code and `population.json`; `demo.json` remains an explicitly labelled fixture. `_site/publication.json` records their hashes. The site builder copies only approved publication assets, excluding development tools and machine configuration.

Manual cache inputs without acquisition receipts require their actual `--retrieval-date YYYY-MM-DD`; no date is inferred. The preserved source inputs here were acquired 2026-11-06. Existing acquisition receipts take precedence over that declaration. Downloads use temporary verified files before replacement, and all publication outputs are staged and validated before promotion. Standalone TIFF GDAL tags retain complete credit and native geometry/source-hash provenance; output hashes live in external receipts to avoid a circular self-hash.

ORNL validation receipts retain the POST endpoint, application/json, payloads, known retrieval date and reproducible Python request commands. The original request time was not retained and remains unknown. Enriched published receipts take precedence over stale cache copies.
