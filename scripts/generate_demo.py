"""Deterministically regenerate invented teaching counts, never observed data."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
layers = []
names = [("uniform", "Synthetic uniform allocation", 4, "Equal allocation within each invented census zone"), ("settlement", "Synthetic settlement weighting", 8, "Invented settlement weights; conserved overall total"), ("ambient", "Synthetic daytime scenario", 4, "Invented redistribution toward a central activity area"), ("partial", "Synthetic incomplete coverage", 4, "Invented counts with the northeast quadrant omitted as NoData")]
for identifier, title, size, allocation in names:
    cells = []
    for row in range(size):
        for col in range(size):
            if identifier == "partial" and row >= 2 and col >= 2:
                continue
            if identifier == "uniform":
                count = 100
            elif identifier == "settlement":
                count = 10 + (row % 4) * 5 + (col % 4) * 5
            elif identifier == "ambient":
                count = 200 if row in (1, 2) and col in (1, 2) else (0 if row == 0 else 100)
            else:
                count = 80
            step = 0.4 / size
            cells.append({"bounds": [round(120 + col * step, 6), round(14 + row * step, 6), round(120 + (col + 1) * step, 6), round(14 + (row + 1) * step, 6)], "population": count})
    layers.append({"metadata": {"id": identifier, "title": title, "source": "JupyterLite-Population-Data-Comparison project; generated teaching fixture", "citation": "JupyterLite-Population-Data-Comparison contributors (2026). Invented comparison cells, version 1.0. No observed population data.", "license": "CC0-1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/", "year": 2020, "version": "1.0", "synthetic": True, "units": "people/cell", "crs": "EPSG:4326", "resolution": f"{0.4/size:g} degree rectangular cells (invented)", "population_concept": "Invented daytime scenario" if identifier == "ambient" else "Invented residential scenario", "allocation": allocation, "census_vintage": "None; no census inputs", "retrieval_date": "Not applicable; generated locally", "publication_date": "2026-11-06", "modifications": "Generated from deterministic arithmetic; no real data inputs", "notice": "SYNTHETIC: not GPW, WorldPop, LandScan, HRSL, GHS-POP or Esri WPE."}, "cells": cells})
document = {"schema_version": "1.0", "description": "SYNTHETIC teaching grids on an invented study rectangle. These are not observed population estimates.", "bounds": [120, 14, 120.4, 14.4], "default_aoi": [120.1, 14.1, 120.3, 14.3], "layers": layers}
path = ROOT / "data/demo.json"
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
print(f"demo.json SHA-256: {hashlib.sha256(path.read_bytes()).hexdigest()}")
layer = layers[0]
features = []
for cell in layer["cells"]:
    w, s, e, n = cell["bounds"]
    features.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[w,s],[e,s],[e,n],[w,n],[w,s]]]}, "properties": {"population": cell["population"]}})
metadata = dict(layer["metadata"], id="synthetic-import-example", title="Synthetic imported uniform grid")
example = ROOT / "data/import-example.geojson"
example.write_text(json.dumps({"type":"FeatureCollection", "metadata":metadata, "features":features}, indent=2) + "\n", encoding="utf-8", newline="\n")
print(f"import-example.geojson SHA-256: {hashlib.sha256(example.read_bytes()).hexdigest()}")
