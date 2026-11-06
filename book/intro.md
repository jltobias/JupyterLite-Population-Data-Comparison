# Population grids in the browser

Compare estimates, inspect their assumptions, and reproduce the calculation in your browser.

**<a href="../viewer/index.html">Open the four-panel viewer</a>** · **<a href="../lab/lab/index.html?path=01_introduction.ipynb">Run the introductory notebook in JupyterLite Lab</a>** · **<a href="../index.html">Workspace home</a>**

```{important}
All bundled population cells are **synthetic teaching data**: invented counts on an arbitrary study rectangle. They are not GPW, WorldPop, LandScan, HRSL, GHS-POP, or Esri WPE data. The viewer's map is drawn locally without an external basemap.
```

Start with the introductory notebook, then examine partial-cell assumptions and missing coverage, and finish by exporting a comparison with its provenance. The Book renders the same canonical notebooks copied into Lab at build time. Their calculations use Python's standard library and the bundled `demo.json`, with no remote population services.

The standalone viewer reproduces the useful core of POPGRID's four-panel comparison workflow: choose layers independently, link map navigation, inspect cells, draw or enter one rectangular study area, and compare totals with their coverage and metadata. The four scenarios deliberately disagree while sharing the same example bounds.

In Lab, choose **Run → Run All Cells**. The first Python kernel start needs a network connection to retrieve the pinned Pyodide runtime and kernel packages. Your notebook changes and generated files live in browser storage; download work you want to keep. The viewer's maps and calculations use only local site assets after the page has loaded. This project does not promise a fully offline Lab setup.

The work builds on POPGRID Viewer and the research and stewardship of NASA, SEDAC, CIESIN, and the POPGRID Data Collaborative. Leyk et al. (2019) explain the central principle: choose a population product for its fitness for the question, geography, period, and source quality. A smaller cell does not establish greater accuracy. See the [credits](credits.md) and the repository README for the historical source inventory and provider-specific requirements.

Real population services, native RustGIS in Pyodide, GeoTIFF analysis, a JupyterGIS extension, GeoLibre messaging, and a FieldWork widget are future work. The current workspace provides validated rectangular count-cell GeoJSON and provenance-rich text exports.
