# Synthetic teaching fixture

**Every bundled count is invented.** No observed population, census, imagery, boundary or basemap data are included. Coordinates define an arbitrary teaching rectangle, not a statement about actual population at that location. These are not GPW, WorldPop, LandScan, HRSL, GHS-POP, or Esri WPE data.

Creator/citation: JupyterLite-Population-Data-Comparison contributors (2026). *Invented comparison cells*, version 1.0. Generated locally on 2026-11-06 by `python scripts/generate_demo.py`, using deterministic arithmetic and no real inputs. Reference year 2020 is an invented scenario label; there is no input-census vintage or retrieval date. The generated teaching cells in `demo.json` and `import-example.geojson` are dedicated under **CC0-1.0**: https://creativecommons.org/publicdomain/zero/1.0/. This does not license any candidate third-party dataset.

`demo.json` SHA-256: `a5e1ea8866db3d1b98643ce7acbc67cd182c1bc9034aa82105cf488640040f1f`

`import-example.geojson` SHA-256: `d9a9f3e03c3a581729da1a96d3dbbe66e73623654f7f70f45084e101e046299c`

Both files are generated with UTF-8 and LF newlines so checksums are stable across Windows and Linux checkouts.

The fixture contract is `{schema_version, description, bounds, default_aoi, layers}`. Each layer contains a complete `metadata` record and nonoverlapping `{bounds: [west,south,east,north], population: count}` cells in EPSG:4326. Missing cells are NoData. Numeric zero is valid count coverage. Layer metadata record title, creator/source, citation, license and URL, version, year, synthetic status, units, CRS, resolution, population concept, allocation method, census vintage and generation history.

The four scenarios illustrate equal allocation, invented settlement weights, an invented daytime redistribution, and missing coverage. The first three have full-grid totals of 1,600; the fourth totals 960 over available cells. The shared example bounds `[120.1, 14.1, 120.3, 14.3]` give **400, 400, 800, 240** with spherical area weighting. The fourth has approximately 75% coverage; latitude affects the exact area fraction. There is no empirical claim that any scenario is more accurate.

`import-example.geojson` is a rectangular-cell FeatureCollection derived directly from the uniform synthetic layer, with a distinct import id. It is compatible with the viewer's documented import contract. The Python helper and viewer apply `cell_count × spherical_overlap_area / spherical_cell_area`, assuming uniform population within each cell. Exports retain all metadata. CSV's `metadata_json` column retains additional notices as well as the convenient core columns.

The Book and Lab receive exact copies of canonical notebooks, helper code and `demo.json` at build time. `_site/publication.json` records their hashes. The site builder copies only approved publication assets, excluding development tools and machine configuration.
