import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))
from population_tools import compare, validate_layer, layer_bounds, iter_cells


class RealPopulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "data/population.json").read_text(encoding="utf-8"))
        cls.oracle = json.loads((ROOT / "data/real/independent_oracle.json").read_text(encoding="utf-8"))

    def test_value_free_catalog_matches_prepared_bytes(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from create_population_catalog import serialized
        content=(ROOT / "data/population-catalog.json").read_text(encoding="utf-8")
        self.assertEqual(content, serialized(ROOT / "data"))
        self.assertLess(len(content.encode("utf-8")), 100000)
        self.assertTrue(all("values" not in source["grid"] for source in json.loads(content)["sources"]))

    def test_real_source_expectations_and_masks(self):
        results = compare(self.data["layers"], self.data["default_aoi"])
        for layer, result in zip(self.data["layers"], results):
            validate_layer(layer)
            metadata, g = layer["metadata"], layer["grid"]
            expected = self.oracle["sources"][metadata["id"]]
            self.assertIs(metadata["synthetic"], False)
            self.assertEqual(metadata["license"], "CC BY 4.0")
            self.assertEqual(sum(v is not None for v in g["values"]), expected["valid_cells"])
            self.assertEqual(sum(v is None for v in g["values"]), expected["nodata_cells"])
            self.assertAlmostEqual(result["population"], expected["aoi_population"], delta=.0001)
            self.assertAlmostEqual(result["coverage"], min(1, expected["aoi_coverage"]), delta=1e-10)
            self.assertEqual(result["intersected_cells"], expected["aoi_intersected_cells"])
            total = compare([layer], layer_bounds(layer))[0]
            self.assertAlmostEqual(total["population"], expected["native_sum"], delta=.001)
            receipt = metadata["processing_receipt"]
            self.assertEqual(hashlib.sha256((ROOT / "data/real" / receipt["output_file"]).read_bytes()).hexdigest(), receipt["output_sha256"])

    def test_source_native_half_pixel_zero_and_outside(self):
        ghs = self.data["layers"][3]
        cell = next(c for c in iter_cells(ghs) if c["population"] > 0)
        w, s, e, n = cell["bounds"]
        result = compare([ghs], [w, s, (w+e)/2, n])[0]
        self.assertAlmostEqual(result["population"], cell["population"]/2, delta=1e-6)
        zero = next(c for c in iter_cells(ghs) if c["population"] == 0)
        self.assertEqual(compare([ghs], zero["bounds"])[0]["population"], 0)
        outside = compare([ghs], [0, 0, 1, 1])[0]
        self.assertIsNone(outside["population"])
        self.assertEqual(outside["coverage"], 0)
        self.assertEqual(outside["prepared_coverage"], 0)

    def test_grid_rejections_and_representability(self):
        base = {"metadata": self.data["layers"][0]["metadata"], "grid": {"width":2, "height":2, "west":3, "north":7, "dx":.1, "dy":.1, "values":[0, None, 1, 2]}}
        validate_layer(base)
        changes = [lambda l: l.update(cells=None), lambda l: l.update(grid=None), lambda l: l["grid"].update(width=True), lambda l: l["grid"].update(width=262145), lambda l: l["grid"].update(values=[0, 1]), lambda l: l["grid"].update(values=[0, -1, 1, 2]), lambda l: l["grid"].update(values=[0, math.inf, 1, 2]), lambda l: l["grid"].update(values=[False,None,1,2]), lambda l: l["grid"].update(west=100, dx=1e-14), lambda l: l["grid"].update(north=80, dy=1e-14)]
        for change in changes:
            layer = copy.deepcopy(base)
            change(layer)
            with self.subTest(layer=layer["grid"]), self.assertRaises(ValueError):
                validate_layer(layer)

    def test_portable_tiff_credits_and_unchanged_native_values(self):
        try:
            import rasterio
        except ImportError:
            self.skipTest("Optional rasterio preparation dependency unavailable")
        for layer in self.data["layers"]:
            m = layer["metadata"]
            with rasterio.open(ROOT / "data/real" / (m["id"]+".tif")) as source:
                tags = source.tags()
                for key, field in (("SOURCE_CITATION","citation"),("LICENSE","license"),("LICENSE_URL","license_url"),("PRODUCER_NOTICES","notices"),("SOURCE_ASSET","source_asset"),("RETRIEVAL_DATE","retrieval_date"),("MODIFICATION","modification")):
                    self.assertEqual(tags[key], m[field])
                receipt = json.loads(tags["NATIVE_PROVENANCE"])
                self.assertEqual(receipt["source_file_sha256"],m["processing_receipt"]["source_file_sha256"])
                self.assertNotIn("output_sha256",receipt)
                values = source.read(1,masked=True)
                mask = values.mask
                native = [None if bool(mask[row,col]) else float(values.data[row,col]) for row in range(source.height) for col in range(source.width)] if hasattr(mask,"shape") and mask.shape else [float(v) for v in values.data.flat]
                self.assertEqual(native,layer["grid"]["values"])
                if m["id"] == "worldpop-2025":
                    self.assertEqual(source.compression.value,"LZW")


if __name__ == "__main__":
    unittest.main()
