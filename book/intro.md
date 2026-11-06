# Population grids in the browser

Compare real estimates, inspect their assumptions, and reproduce the calculation in your browser.

**<a href="../viewer/index.html">Open the four-panel viewer</a>** · **<a href="../lab/lab/index.html?path=01_real_population.ipynb">Run the real-data notebook in JupyterLite Lab</a>** · **<a href="../index.html">Workspace home</a>**

The default layers contain genuine native-pixel Greater Lagos excerpts of **WorldPop Global2 2025 R2025A v1**, **GRID3 Nigeria 2025 v3.0**, **LandScan Global 2020**, and **GHS-POP R2023A E2025 V1.0**. Prepared extent is `[3.2, 6.35, 3.6, 6.7]`; whole native edge cells can extend slightly beyond it. No resampling or synthetic replacement is performed. All products are CC BY 4.0, with citations and modification notices in each layer and export.

Start with the introductory notebook, examine partial-cell assumptions and missing coverage, then export results with their provenance. Book and Lab use the same canonical `population.json` and standard-library Python helper as the viewer's JavaScript counterpart. The independent source-derived oracle checks the shared rectangle `[3.30, 6.45, 3.45, 6.60]`.

The four-panel viewer supports linked navigation, native-pixel inspection, rectangle drawing and coordinate entry, and CSV/JSON/SVG exports. Colors display comparable density; calculations always use native counts. Numeric zero and NoData remain distinct. Product years, dates, census vintages and residential versus ambient concepts differ. Disagreement does not establish accuracy.

In Lab, choose **Run → Run All Cells**. The first kernel start needs a connection to retrieve the pinned Pyodide runtime. Your notebook changes and generated files remain in browser storage; download work you want to keep. Fresh real-data launch filenames preserve older user notebooks. No population service is queried during lessons or normal builds.

For another supported area, download a source GeoTIFF and use the viewer's cancellable local-file native-window import. It accepts only single-band north-up WGS84 stored count TIFFs under explicit bounds and memory limits. This regional bundle does not provide global streaming. WorldPop and GRID3 downloads currently fail browser CORS and ignore byte ranges. GPW is not bundled; its present Harvard Dataverse access uses a guestbook, and no personal details are collected here.

Inspired by POPGRID Viewer and the research and stewardship of NASA, SEDAC, CIESIN and the POPGRID Data Collaborative. Leyk et al. (2019) explain fitness for use: select a product for the question, geography, period and source quality. Finer grids alone do not establish greater accuracy. See [methods](methods.md) and [credits](credits.md). Full GIS, district/polygon summaries, RustGIS, GeoLibre, JupyterGIS and FieldWork integration remain future work.
