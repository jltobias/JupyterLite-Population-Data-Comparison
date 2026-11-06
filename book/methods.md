# Method and import contract

## Count aggregation

For each nonoverlapping count cell, estimate the people in the study rectangle as `cell population × spherical overlap area / spherical cell area`, then sum the contributions. The spherical area of a WGS84 longitude/latitude rectangle is proportional to `(east − west) × (sin(north) − sin(south))`, using radians. The sphere radius cancels in the fraction. This is a spherical approximation, not an ellipsoidal geodesic calculation.

The method assumes uniform population inside a cell. It does not locate people precisely. No resampling changes the analytical values, and display zoom does not change native cell size. Inputs must already be counts in **people/cell**; density is unsupported until converted with the appropriate area and source semantics.

The tile-free viewer uses Leaflet's EPSG:4326 equirectangular display, including polar latitudes up to ±90°. This display stretches area with latitude; the calculations use spherical areas independently of map appearance.

Coverage is the summed spherical overlap area with data divided by the spherical study area. Valid zero-count cells contribute coverage. Absent cells represent NoData; when no cells intersect, population is `null` in JSON and blank in CSV, while coverage is zero. The UI says **No coverage**. Areas outside the grids can have partial coverage. Counts and coverage are exported at full numeric precision; display values are rounded.

The shared rectangle `[120.1, 14.1, 120.3, 14.3]` yields **400, 400, 800, 240** for the four bundled scenarios. The complete first three grids each sum to 1,600 over the full study rectangle; the fourth contains 960 people over its available cells. Its default-area coverage is approximately 75%, with the exact value accounting for latitude.

## Import contract

<a href="../data/import-example.geojson">Download a complete synthetic example</a>. Imported files stay in the current browser session and are not uploaded to a server.

Use a GeoJSON `FeatureCollection` in WGS84 longitude/latitude with a top-level `metadata` object. Every feature must contain one axis-aligned `Polygon` rectangle: one ring, five two-dimensional positions with the first repeated at the end, four distinct corners, and no crossing edges. Features have numeric `properties.population` counts. Cells may share edges but must not overlap. Omit NoData cells; a numeric zero is valid coverage.

The import limit is **2 MB**, **2,000 cells per layer**, at most **5 degrees per cell in either direction**, and **16 layers in a browser session**. Coordinates must be finite and within longitude −180…180 and latitude −90…90. West must be less than east; south less than north. Antimeridian-crossing cells, holes, multipolygons, CRS overrides, negative/nonfinite counts, and density inputs are rejected. Invalid imports and area inputs leave existing valid analysis intact.

Metadata fields (all required):

| Field | Value |
| --- | --- |
| `id`, `title`, `version` | Nonempty strings; id must be unique in the session |
| `source`, `citation` | Actual creator/distributor and full source citation |
| `license`, `license_url` | Exact applicable license and its reference |
| `year` | Integer reference year from 0 to 9999 |
| `synthetic` | Boolean, `true` for invented data |
| `units`, `crs` | Exactly `people/cell`, `EPSG:4326` |
| `resolution` | Native cell support description |
| `population_concept` | Residential, ambient, or other declared concept |
| `allocation`, `census_vintage` | Source method and actual census vintage, or explicit non-applicability |

Add retrieval and publication dates, notices, provider credits, checksums, and processing history as additional metadata fields. Required text fields are limited to 4,000 characters. The importer validates structure, not the authenticity or legal sufficiency of supplied provenance. Metadata are displayed as text. Full metadata are preserved in JSON results, the CSV `metadata_json` field, and the downloaded chart SVG's description. The CSV's core columns are convenient for spreadsheets, and formula-like metadata are escaped to avoid accidental evaluation.

## Interpretation and exports

Do not interpret disagreement as a confidence interval. Compare year, concept, census inputs, coverage, allocation methods and appropriate spatial support. The synthetic daytime scenario represents a different concept; the incomplete scenario has missing coverage. These are intentional examples of why raw totals alone do not establish accuracy.

JSON and CSV include source, citation, exact license, synthetic status, reference year, active bounds, method, population estimate, coverage, and intersected-cell count. JSON and CSV retain all optional metadata. Chart SVGs embed the same full result in their description for standalone reuse. Keep that metadata and all producer notices with derived files.
