import copy
import csv
import hashlib
import io
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))
from population_tools import area, compare, export_csv, import_geojson, validate_bounds, validate_layer


class PopulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo = json.loads((ROOT / "data/demo.json").read_text(encoding="utf-8"))
        cls.geo = json.loads((ROOT / "data/import-example.geojson").read_text(encoding="utf-8"))

    def test_known_counts_and_full_grid_totals(self):
        for result, expected in zip(compare(self.demo["layers"], self.demo["default_aoi"]), [400, 400, 800, 240]):
            self.assertAlmostEqual(result["population"], expected, places=7)
            self.assertIn("Spherical", result["method"])
        self.assertEqual([round(r["population"]) for r in compare(self.demo["layers"], self.demo["bounds"])], [1600,1600,1600,960])

    def test_partial_cell_fraction_independent_spherical_formula(self):
        layer = copy.deepcopy(self.demo["layers"][0])
        layer["cells"] = [{"bounds": [0, 30, 2, 60], "population": 1000}]
        result = compare([layer], [0, 30, 1, 45])[0]
        expected = 500 * (math.sin(math.pi/4) - .5) / (math.sin(math.pi/3) - .5)
        self.assertAlmostEqual(result["population"], expected)
        self.assertAlmostEqual(result["coverage"], 1)

    def test_polar_area_subnormal_counts_and_unrepresentable_bounds(self):
        polar = [0, 89.999999999, 1, 90]
        self.assertGreater(area(polar), 0)
        layer = {"metadata": self.demo["layers"][0]["metadata"], "cells": [{"bounds": polar, "population": 100}]}
        validate_layer(layer)
        self.assertEqual(compare([layer], polar)[0]["population"], 100)
        self.assertEqual(compare([layer], [0, polar[1], .5, 90])[0]["population"], 50)
        layer["cells"] = [{"bounds": [0,0,1,1], "population": 1e-320}]
        self.assertEqual(compare([layer], [0,0,1,1])[0]["population"], 1e-320)
        with self.assertRaisesRegex(ValueError, "representable"):
            validate_bounds([0,0,5e-324,1])

    def test_positive_overlap_has_no_tolerance(self):
        cell = {"bounds": [0,0,1e-11,1], "population": 10}
        layer = {"metadata": self.demo["layers"][0]["metadata"], "cells": [cell, copy.deepcopy(cell)]}
        with self.assertRaisesRegex(ValueError, "overlap"):
            validate_layer(layer)

    def test_zero_no_coverage_and_partial_coverage(self):
        zero = compare([self.demo["layers"][2]], [120,14,120.1,14.1])[0]
        missing = compare([self.demo["layers"][3]], [120.2,14.2,120.4,14.4])[0]
        self.assertEqual(zero["population"], 0)
        self.assertAlmostEqual(zero["coverage"], 1)
        self.assertIsNone(missing["population"])
        self.assertEqual(missing["coverage"], 0)
        result = compare([self.demo["layers"][0]], [119.9,14,120.1,14.1])[0]
        self.assertAlmostEqual(result["coverage"], .5)

    def test_boundary_touch_has_no_contribution(self):
        result = compare(self.demo["layers"], [120.4,14,120.5,14.4])[0]
        self.assertIsNone(result["population"])

    def test_invalid_bounds(self):
        for bounds in [[1,1,0,2], [0,0,0,1], [-181,0,1,1], [0,0,1,91], [0,0,float("nan"),1], [0,True,1,2], [0,1,2]]:
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                validate_bounds(bounds)

    def test_bundled_layers_have_provenance_and_no_overlap(self):
        for layer in self.demo["layers"]:
            validate_layer(layer)
            self.assertIs(layer["metadata"]["synthetic"], True)
            self.assertIn("SYNTHETIC", layer["metadata"]["notice"])
        checksum = hashlib.sha256((ROOT / "data/demo.json").read_bytes()).hexdigest()
        self.assertIn(checksum, (ROOT / "data/README.md").read_text(encoding="utf-8"))
        self.assertIn(hashlib.sha256((ROOT / "data/import-example.geojson").read_bytes()).hexdigest(), (ROOT / "data/README.md").read_text(encoding="utf-8"))

    def test_geojson_example_and_provenance_export(self):
        document = copy.deepcopy(self.geo)
        document["metadata"].update({"notice": "Additional provider copyright notice", "attribution_parties": ["Original producer", "Distributor"], "retrieval_date": "2026-11-06", "optional_object": {"toString": "provider value", "nested": [None, True, 4.5, "Valid Unicode: \U0001f30d"]}})
        results = compare([import_geojson(document)], self.demo["default_aoi"])
        self.assertAlmostEqual(results[0]["population"], 400)
        csv_row = next(csv.DictReader(io.StringIO(export_csv(results))))
        self.assertEqual(json.loads(csv_row["metadata_json"]), document["metadata"])
        self.assertEqual(csv_row["synthetic"], "True")
        self.assertEqual(json.loads(csv_row["bounds"]), self.demo["default_aoi"])
        self.assertEqual(json.loads(json.dumps(results))[0]["metadata"], document["metadata"])

    def test_csv_formula_escape(self):
        result = compare([self.demo["layers"][0]], self.demo["default_aoi"])[0]
        result["metadata"]["title"] = '  =HYPERLINK("bad")'
        row = next(csv.DictReader(io.StringIO(export_csv([result]))))
        self.assertTrue(row["title"].startswith("'"))

    def test_bad_count_types(self):
        for value in [-1, float("nan"), float("inf"), True, "10", None]:
            document = copy.deepcopy(self.geo)
            document["features"][0]["properties"]["population"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                import_geojson(document)

    def test_bad_geometry_and_coordinates(self):
        changes = [lambda d: d.update(type="GeometryCollection"),
                   lambda d: d.update(crs={"name": "EPSG:3857"}),
                   lambda d: d["features"][0]["geometry"].update(type="MultiPolygon"),
                   lambda d: d["features"][0]["geometry"]["coordinates"].append([[0,0],[1,0],[1,1],[0,0]]),
                   lambda d: d["features"][0]["geometry"]["coordinates"][0].__setitem__(1,[121,14.05]),
                   lambda d: d["features"][0]["geometry"]["coordinates"][0].__setitem__(0,[181,14])]
        for change in changes:
            document = copy.deepcopy(self.geo)
            change(document)
            with self.assertRaises(ValueError):
                import_geojson(document)

    def test_malformed_feature_objects_give_value_error(self):
        for key in ("geometry", "properties"):
            for value in (None, [], "scalar", 10, True):
                document = copy.deepcopy(self.geo)
                document["features"][0][key] = value
                with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                    import_geojson(document)

    def test_optional_metadata_rejects_nonfinite_and_invalid_xml(self):
        bad_values = [json.loads("1e400"), float("nan"), "control\x00", "control\x0b", "noncharacter\ufffe", "surrogate\ud800"]
        for value in bad_values:
            document = copy.deepcopy(self.geo)
            document["metadata"]["optional"] = {"nested": [value]}
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                import_geojson(document)
        document = copy.deepcopy(self.geo)
        document["metadata"]["bad\x00key"] = "value"
        with self.assertRaises(ValueError):
            import_geojson(document)

    def test_overlap_and_oversize(self):
        overlap = copy.deepcopy(self.geo)
        overlap["features"].append(copy.deepcopy(overlap["features"][0]))
        with self.assertRaisesRegex(ValueError, "overlap"):
            import_geojson(overlap)
        too_many = copy.deepcopy(self.geo)
        too_many["features"] = [too_many["features"][0]] * 2001
        with self.assertRaisesRegex(ValueError, "2000"):
            import_geojson(too_many)
        oversized = copy.deepcopy(self.geo)
        oversized["features"] = [{"type":"Feature", "geometry":{"type":"Polygon","coordinates":[[[0,0],[6,0],[6,1],[0,1],[0,0]]]},"properties":{"population":10}}]
        with self.assertRaisesRegex(ValueError, "5 degrees"):
            import_geojson(oversized)

    def test_metadata_rejects_unsupported_units(self):
        for key,value in [("units","people/km2"),("crs","EPSG:3857"),("synthetic","true"),("year",True),("source","")]:
            document = copy.deepcopy(self.geo)
            document["metadata"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                import_geojson(document)


if __name__ == "__main__":
    unittest.main()
