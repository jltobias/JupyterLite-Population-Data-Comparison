"""Dependency-free teaching calculations shared by CPython and JupyterLite.

Real source excerpts and explicitly synthetic teaching fixtures share this API.
Rectangular counts are allocated uniformly
within each cell using spherical area fractions; this is an assumption, not a
measurement of where people live inside the cell.
"""
import csv
import io
import json
import math
from pathlib import Path

METHOD = "Spherical area-weighted count allocation; uniform population within each rectangular cell"
REQUIRED_METADATA = ("id", "title", "source", "citation", "license", "license_url", "year", "version", "synthetic", "units", "crs", "resolution", "population_concept", "allocation", "census_vintage")
MAX_CELLS = 2000
MAX_GRID_CELLS = 262144


def finite_number(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def validate_bounds(bounds):
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 4 or not all(map(finite_number, bounds)):
        raise ValueError("Bounds must contain four finite numbers: west, south, east, north.")
    west, south, east, north = bounds
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Bounds must be ordered west < east, south < north within WGS84 longitude/latitude ranges; antimeridian areas are unsupported.")
    area(bounds)
    return list(bounds)


def area(bounds):
    """Spherical rectangle area in unit-sphere units (radius cancels in ratios)."""
    west, south, east, north = bounds
    polar_distance = ((90 - north) + (90 - south)) / 2 if south + north >= 0 else ((90 + north) + (90 + south)) / 2
    result = math.radians(east - west) * (2 * math.sin(math.radians(polar_distance)) * math.sin(math.radians(north - south) / 2))
    if not math.isfinite(result) or result <= 0:
        raise ValueError("Rectangle area must be positive and representable at floating-point precision.")
    return result


def intersection(a, b):
    result = [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]
    return result if result[0] < result[2] and result[1] < result[3] else None


def validate_json_metadata(value, depth=0, ancestors=None):
    """Require finite JSON data and strings representable in XML 1.0 exports."""
    if depth > 64:
        raise ValueError("Metadata nesting must not exceed 64 levels.")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        if any(not (ord(char) in (9, 10, 13) or 0x20 <= ord(char) <= 0xD7FF or 0xE000 <= ord(char) <= 0xFFFD or 0x10000 <= ord(char) <= 0x10FFFF) for char in value):
            raise ValueError("Metadata strings and keys must contain only XML-representable Unicode characters.")
        return
    if isinstance(value, (int, float)):
        if not finite_number(value):
            raise ValueError("Metadata numbers must be finite JSON-safe numbers.")
        return
    if not isinstance(value, (dict, list)):
        raise ValueError("Metadata must contain only JSON objects, arrays, strings, finite numbers, booleans, or null.")
    ancestors = set() if ancestors is None else ancestors
    if id(value) in ancestors:
        raise ValueError("Metadata must not contain circular references.")
    ancestors.add(id(value))
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("Metadata object keys must be strings.")
            validate_json_metadata(key, depth + 1, ancestors)
            validate_json_metadata(child, depth + 1, ancestors)
    else:
        for child in value:
            validate_json_metadata(child, depth + 1, ancestors)
    ancestors.remove(id(value))


def validate_metadata(metadata):
    if not isinstance(metadata, dict) or any(key not in metadata for key in REQUIRED_METADATA):
        raise ValueError("Layer metadata must provide: " + ", ".join(REQUIRED_METADATA))
    validate_json_metadata(metadata)
    for key in REQUIRED_METADATA:
        if key not in ("year", "synthetic") and (not isinstance(metadata[key], str) or not metadata[key].strip() or len(metadata[key]) > 4000):
            raise ValueError(f"Metadata {key} must be nonempty text (maximum 4000 characters).")
    if not isinstance(metadata["synthetic"], bool):
        raise ValueError("Metadata synthetic must be true or false.")
    if not isinstance(metadata["year"], int) or isinstance(metadata["year"], bool) or not 0 <= metadata["year"] <= 9999:
        raise ValueError("Metadata year must be an integer from 0 to 9999.")
    if metadata["units"] != "people/cell" or metadata["crs"] != "EPSG:4326":
        raise ValueError("Only people/cell counts in EPSG:4326 are supported; density requires conversion before import.")
    return metadata


def validate_layer(layer):
    validate_metadata(layer.get("metadata"))
    if "grid" in layer:
        g = layer["grid"]
        if not isinstance(g, dict) or any(not isinstance(g.get(k), int) or isinstance(g[k], bool) or g[k] < 1 for k in ("width", "height")) or g["width"] * g["height"] > MAX_GRID_CELLS:
            raise ValueError("A regular grid requires positive dimensions and at most 262144 cells.")
        if any(not finite_number(g.get(k)) for k in ("west", "north", "dx", "dy")) or not 0 < g["dx"] <= 5 or not 0 < g["dy"] <= 5:
            raise ValueError("Grid requires finite north-up coordinates and positive cell sizes of at most 5 degrees.")
        validate_bounds(grid_bounds(g))
        widths = [g["west"]+(x+1)*g["dx"] - (g["west"]+x*g["dx"]) for x in range(g["width"])]
        if min(widths) <= 0:
            raise ValueError("Native cell bounds must remain representable at floating-point precision.")
        for y in range(g["height"]):
            validate_bounds([g["west"], g["north"]-(y+1)*g["dy"], g["west"]+min(widths), g["north"]-y*g["dy"]])
        if not isinstance(g.get("values"), list) or len(g["values"]) != g["width"] * g["height"]:
            raise ValueError("Grid values must be a row-major array matching its dimensions.")
        if any(v is not None and (not finite_number(v) or v < 0) for v in g["values"]):
            raise ValueError("Grid values must be nonnegative finite counts or null NoData.")
        if not math.isfinite(sum(v or 0 for v in g["values"])):
            raise ValueError("Grid population sum exceeds finite numeric range.")
        if "cells" in layer:
            raise ValueError("Provide either a regular grid or rectangular cells.")
        return layer
    cells = layer.get("cells")
    if not isinstance(cells, list) or not 1 <= len(cells) <= MAX_CELLS:
        raise ValueError(f"A layer must have between 1 and {MAX_CELLS} cells.")
    for index, cell in enumerate(cells):
        bbox = validate_bounds(cell.get("bounds"))
        if bbox[2] - bbox[0] > 5 or bbox[3] - bbox[1] > 5:
            raise ValueError("Each cell must span at most 5 degrees in either direction.")
        if not finite_number(cell.get("population")) or cell["population"] < 0:
            raise ValueError("Cell populations must be finite, nonnegative counts; omit NoData cells.")
        for previous in cells[:index]:
            overlap = intersection(bbox, previous["bounds"])
            if overlap:
                raise ValueError("Cells may touch at their edges but must not overlap.")
    if not finite_number(sum(cell["population"] for cell in cells)):
        raise ValueError("Layer population sum exceeds finite numeric range.")
    return layer


def grid_bounds(g):
    return [g["west"], g["north"] - g["height"] * g["dy"], g["west"] + g["width"] * g["dx"], g["north"]]


def layer_bounds(layer):
    if "grid" in layer:
        return grid_bounds(layer["grid"])
    cells = layer["cells"]
    return [min(c["bounds"][0] for c in cells), min(c["bounds"][1] for c in cells), max(c["bounds"][2] for c in cells), max(c["bounds"][3] for c in cells)]


def native_window(g, bounds):
    return [max(0, min(g["width"], math.floor((bounds[0]-g["west"])/g["dx"]))), max(0, min(g["height"], math.floor((g["north"]-bounds[3])/g["dy"]))), max(0, min(g["width"], math.ceil((bounds[2]-g["west"])/g["dx"]))), max(0, min(g["height"], math.ceil((g["north"]-bounds[1])/g["dy"])))]


def iter_cells(layer, bounds=None):
    if "grid" not in layer:
        yield from layer["cells"]
        return
    g = layer["grid"]
    x0, y0, x1, y1 = native_window(g, bounds or grid_bounds(g))
    for y in range(y0, y1):
        for x in range(x0, x1):
            value = g["values"][y*g["width"]+x]
            if value is not None:
                yield {"population": value, "bounds": [g["west"]+x*g["dx"], g["north"]-(y+1)*g["dy"], g["west"]+(x+1)*g["dx"], g["north"]-y*g["dy"]]}


def import_geojson(document):
    """Accept a FeatureCollection of axis-aligned Polygon count cells.

    Metadata is at the collection's `metadata`; each feature has the numeric
    property `population`. No holes, antimeridian cells, or other CRS supported.
    """
    if not isinstance(document, dict) or document.get("type") != "FeatureCollection" or "crs" in document:
        raise ValueError("Import a WGS84 GeoJSON FeatureCollection without a crs override.")
    features = document.get("features")
    if not isinstance(features, list) or not 1 <= len(features) <= MAX_CELLS:
        raise ValueError(f"Import requires between 1 and {MAX_CELLS} features.")
    cells = []
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError("Every cell must be a GeoJSON Feature.")
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            raise ValueError("Feature geometry must be a GeoJSON object.")
        rings = geometry.get("coordinates")
        if geometry.get("type") != "Polygon" or not isinstance(rings, list) or len(rings) != 1:
            raise ValueError("Only rectangular Polygon cells without holes are supported.")
        ring = rings[0]
        if not isinstance(ring, list) or len(ring) != 5 or any(not isinstance(p, list) or len(p) != 2 or not all(map(finite_number, p)) for p in ring):
            raise ValueError("A rectangle needs five [longitude, latitude] positions, including closure.")
        bounds = validate_bounds([min(p[0] for p in ring), min(p[1] for p in ring), max(p[0] for p in ring), max(p[1] for p in ring)])
        corners = {(bounds[x], bounds[y]) for x, y in ((0, 1), (2, 1), (2, 3), (0, 3))}
        if ring[0] != ring[-1] or set(map(tuple, ring[:4])) != corners or any(ring[i][0] != ring[i+1][0] and ring[i][1] != ring[i+1][1] for i in range(4)):
            raise ValueError("Cells must be closed, axis-aligned rectangles with no crossing edges.")
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            raise ValueError("Feature properties must be an object containing population.")
        cells.append({"bounds": bounds, "population": properties.get("population")})
    return validate_layer({"metadata": document.get("metadata"), "cells": cells})


def compare(layers, bounds):
    bounds = validate_bounds(bounds)
    results = []
    for layer in layers:
        total, covered, intersected = 0.0, 0.0, 0
        for cell in iter_cells(layer, bounds):
            overlap = intersection(bounds, cell["bounds"])
            if overlap:
                overlap_area = area(overlap)
                total += cell["population"] * min(1.0, overlap_area / area(cell["bounds"]))
                covered += overlap_area
                intersected += 1
        support = intersection(bounds, layer_bounds(layer))
        grid = {k: layer["grid"][k] for k in ("width", "height", "west", "north", "dx", "dy")} if "grid" in layer else None
        results.append({"metadata": json.loads(json.dumps(layer["metadata"])), "population": total if intersected else None, "coverage": min(1.0, covered / area(bounds)), "intersected_cells": intersected, "bounds": list(bounds), "method": METHOD, "grid": grid, "prepared_coverage": min(1, area(support)/area(bounds)) if support else 0})
    return results


def export_csv(results):
    output = io.StringIO(newline="")
    fields = [*REQUIRED_METADATA, "population", "coverage", "intersected_cells", "bounds", "method", "grid", "prepared_coverage", "metadata_json"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for result in results:
        row = {**result["metadata"], **{k: v for k, v in result.items() if k != "metadata"}}
        row["metadata_json"] = json.dumps(result["metadata"], ensure_ascii=False)
        row = {key: row[key] for key in fields}
        row["bounds"] = json.dumps(row["bounds"])
        row["grid"] = json.dumps(row["grid"])
        # Spreadsheet programs must not interpret supplied metadata as formulas.
        row = {k: "'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v for k, v in row.items()}
        writer.writerow(row)
    return output.getvalue()


def load_demo(path="demo.json"):
    """The build places the canonical demo next to all Lab notebooks."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_population(path="population.json"):
    """Load the canonical native-pixel real population excerpts."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
