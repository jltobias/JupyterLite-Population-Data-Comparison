"""Generate three real-data lessons with fresh launch names for returning Lab users."""
from pathlib import Path
import nbformat as nb

ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = """## Sources and software

The complete citation, release, native geometry, source asset, NoData semantics, license, retrieval date (2026-11-06) and processing receipt travel in every layer's metadata. These are native-pixel Greater Lagos excerpts, spatially subset and losslessly serialized without resampling; no producer endorsement. All four products are CC BY 4.0. WorldPop: Bondarenko et al. (2025), https://doi.org/10.5258/SOTON/WP00839 (Global2 R2025A v1 alpha); GRID3: Nnanatu et al. (2025), https://doi.org/10.5258/SOTON/WP00782; LandScan: Rose et al. (2021), https://doi.org/10.48690/1523378; GHS-POP: Schiavina et al. (2023), https://doi.org/10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE and Pesaresi et al. (2024), https://doi.org/10.1080/17538947.2024.2390454. Credit WorldPop / University of Southampton; GRID3 Inc. and CIESIN / Columbia Climate School; Oak Ridge National Laboratory; European Commission/JRC, (c) European Union, 1995-2026. Gates Foundation WorldPop INV-045237 and GRID3 INV-044979. Preserve all producer notices when sharing.

LandScan pixels came from a pinned Hugging Face mirror, not an ORNL-hosted TIFF. Independent ORNL statistics matched one cell and the complete prepared window; they do not prove full mirror bit identity. GHS-POP uses the official JRC source, not a quantized third-party mirror. GPW is not bundled; current Harvard Dataverse access uses a guestbook. GRID3 and WorldPop file servers currently lack browser CORS/range support; download yourself and use the viewer's bounded local TIFF import for other areas.

Inspired by NASA Earthdata, SEDAC/CIESIN and POPGRID Viewer (https://www.earthdata.nasa.gov/news/feature-articles/data-tool-focus-popgrid-viewer). Fitness for use: Leyk et al. (2019), https://doi.org/10.5194/essd-11-1385-2019. Execution: Project Jupyter / JupyterLite, Pyodide, Jupyter Book / MyST. The viewer uses Leaflet 1.9.4 and GeoTIFF.js 3.0.5 with their notices. RustGIS, GeoLibre, JupyterGIS and FieldWork integration remain future work.
"""
SETUP = """import json
from pathlib import Path
from population_tools_real import load_population, compare, validate_layer
data = load_population()
oracle = json.loads(Path('independent_oracle.json').read_text(encoding='utf-8'))
for layer in data['layers']:
    validate_layer(layer)
"""


def write(name, cells):
    notebook = nb.v4.new_notebook(cells=[nb.v4.new_markdown_cell(text) if kind == "md" else nb.v4.new_code_cell(text) for kind, text in cells])
    notebook.metadata = {"kernelspec": {"display_name": "Python (Pyodide)", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3"}}
    for index, cell in enumerate(notebook.cells):
        cell.id = name.split(".")[0] + "-" + str(index)
    (ROOT / "notebooks" / name).write_text(nb.writes(notebook), encoding="utf-8", newline="\n")


write("01_real_population.ipynb", [("md", """# 1. Compare real population products

Run **Run → Run All Cells** in JupyterLite/Pyodide. The first kernel start retrieves the pinned Python runtime. Population calculations use bundled local source pixels and Python's standard library. New real-data notebook names and a versioned helper alias preserve returning users' older synthetic notebooks in browser storage.

We compare native Greater Lagos excerpts of WorldPop Global2 2025, GRID3 Nigeria 2025, LandScan Global 2020 and GHS-POP 2025. Prepared extent: `[3.2, 6.35, 3.6, 6.7]`; edge pixels extend to native boundaries. This is a regional excerpt, not global streaming. Density is only a map display; stored values are people per native cell.
"""), ("code", SETUP + """for layer in data['layers']:
    m = layer['metadata']
    print(m['title'], m['version'], m['reference_date'], m['population_concept'], m['license'])
"""), ("md", """## Reproduce the viewer rectangle

The shared WGS84 rectangle is `[3.30, 6.45, 3.45, 6.60]`. Independent NumPy/rasterio calculations from source pixels give approximately 3,058,259.42 WorldPop, 2,375,656.06 GRID3, 7,422,967.00 LandScan and 5,013,773.99 GHS-POP people, with different numeric-cell coverage. The code checks full precision against the separate source oracle.
"""), ("code", """results = compare(data['layers'], data['default_aoi'])
for result in results:
    expected = oracle['sources'][result['metadata']['id']]
    assert abs(result['population'] - expected['aoi_population']) < .0001
    assert abs(result['coverage'] - min(1, expected['aoi_coverage'])) < 1e-10
    assert result['intersected_cells'] == expected['aoi_intersected_cells']
    print(result['metadata']['id'], round(result['population'], 2), f"coverage={result['coverage']:.2%}")
print('REAL_POPULATION_BROWSER_OK')
"""), ("md", """WorldPop refers to January 1, 2025; GRID3 is scaled to July 2025. LandScan is 2020 ambient (24-hour average) population; the others are residential estimates/projection. GHS-POP 2025 is a projection using GPWv4.11 demographic inputs. GRID3 and WorldPop share producers/inputs. Agreement is not independent validation, and disagreement does not determine accuracy.

Change the rectangle below; areas outside prepared grids reduce coverage instead of inventing values.
"""), ("code", """my_bounds = [3.32, 6.48, 3.40, 6.56]
[(r['metadata']['title'], r['population'], r['coverage']) for r in compare(data['layers'], my_bounds)]
"""), ("md", PROVENANCE)])

write("02_real_coverage.ipynb", [("md", """# 2. Native cells, area weighting and NoData

Native counts are allocated by `cell_count × spherical_overlap_area / spherical_cell_area`. This assumes uniform population within each cell; it cannot recover unknown settlement patterns. Counts are not densities. The calculation preserves different grid offsets and null masks.
"""), ("code", SETUP), ("md", """## Independently inspect a native pixel

A longitude half-cell has half the spherical area. This checks a real GHS-POP pixel. Each layer's own native extent also reproduces its independently calculated source sum.
"""), ("code", """from population_tools_real import iter_cells, layer_bounds
ghs = data['layers'][3]
cell = next(c for c in iter_cells(ghs) if c['population'] > 0)
w, s, e, n = cell['bounds']
half = compare([ghs], [w, s, (w+e)/2, n])[0]
assert abs(half['population'] - cell['population']/2) < 1e-6
for layer in data['layers']:
    result = compare([layer], layer_bounds(layer))[0]
    expected = oracle['sources'][layer['metadata']['id']]
    assert abs(result['population'] - expected['native_sum']) < .001
    print(layer['metadata']['id'], result['population'], result['coverage'])
"""), ("md", """## Zero remains distinct from missing

GHS-POP declares no NoData; valid zeros include water. GRID3 NaN denotes mapped unsettled inside Nigeria and outside coverage outside the boundary. It is preserved as null, not zero. Numeric-cell coverage is a data-support measure, not a confidence or accuracy score.
"""), ("code", """zero_cell = next(c for c in iter_cells(ghs) if c['population'] == 0)
zero = compare([ghs], zero_cell['bounds'])[0]
assert zero['population'] == 0 and abs(zero['coverage']-1) < 1e-10
missing = compare(data['layers'], [0, 0, 1, 1])[0]
assert missing['population'] is None and missing['coverage'] == 0
assert any(v is None for v in data['layers'][1]['grid']['values'])
print('Covered zero:', zero['population'], 'Missing:', missing['population'])
print('REAL_COVERAGE_BROWSER_OK')
"""), ("md", PROVENANCE)])

write("03_real_exports.ipynb", [("md", """# 3. Export real comparisons with provenance

Create CSV and JSON matching the viewer, plus one native real GHS-POP count cell as a supported rectangular GeoJSON import. The viewer also imports local count GeoTIFF windows using a cancellable browser worker; this standard-library notebook does not decode TIFF files. Keep source attribution, bounds, grid identity, coverage and method with every result.
"""), ("code", SETUP + """from population_tools_real import export_csv, METHOD, iter_cells, import_geojson
results = compare(data['layers'], data['default_aoi'])
for result in results:
    assert abs(result['population'] - oracle['sources'][result['metadata']['id']]['aoi_population']) < .0001
cell = next(c for c in iter_cells(data['layers'][3]) if c['population'] > 0)
w, s, e, n = cell['bounds']
metadata = dict(data['layers'][3]['metadata'], id='notebook-ghs-cell', title='GHS-POP native cell export', notebook_subset_bounds=cell['bounds'])
document = {'type':'FeatureCollection', 'metadata':metadata, 'features':[{'type':'Feature', 'geometry':{'type':'Polygon', 'coordinates':[[[w,s],[e,s],[e,n],[w,n],[w,s]]]}, 'properties':{'population':cell['population']}}]}
imported = import_geojson(document)
assert compare([imported], cell['bounds'])[0]['population'] == cell['population']
print('Validated real count cell:', cell['population'])
"""), ("code", """output = Path('outputs')
output.mkdir(exist_ok=True)
(output / 'real-count-cell.geojson').write_text(json.dumps(document, indent=2), encoding='utf-8')
(output / 'real-comparison.json').write_text(json.dumps({'notice':'Real native source counts; CC BY 4.0; spatial subsets, no endorsement', 'bounds':data['default_aoi'], 'method':METHOD, 'results':results}, indent=2), encoding='utf-8')
(output / 'real-comparison.csv').write_text(export_csv(results), encoding='utf-8')
print('Created real-comparison.csv, real-comparison.json, real-count-cell.geojson')
print('REAL_EXPORT_BROWSER_OK')
"""), ("md", """Download files from the Lab `outputs` folder. JSON contains complete metadata and grid identity. CSV's `metadata_json` column preserves every supplied source notice and processing receipt. The viewer's SVG embeds the same data in its description and shows visible source credits. User-supplied provenance describes a declaration; structural validation does not independently prove an uploaded file's source identity.
"""), ("md", PROVENANCE)])
