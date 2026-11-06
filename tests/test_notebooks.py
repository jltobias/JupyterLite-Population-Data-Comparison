import asyncio
import json
import shutil
import tempfile
import sys
import unittest
from pathlib import Path
import nbformat
from nbclient import NotebookClient

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

ROOT = Path(__file__).resolve().parents[1]


class NotebookTests(unittest.TestCase):
    def test_all_canonical_notebooks_execute_and_export(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            shutil.copy2(ROOT / "data/demo.json", target / "demo.json")
            shutil.copy2(ROOT / "data/population.json", target / "population.json")
            shutil.copy2(ROOT / "data/real/independent_oracle.json", target / "independent_oracle.json")
            shutil.copy2(ROOT / "notebooks/population_tools.py", target / "population_tools_real.py")
            notebooks = sorted((ROOT / "notebooks").glob("*.ipynb"))
            self.assertEqual(len(notebooks), 3)
            for path in notebooks:
                with self.subTest(notebook=path.name):
                    notebook = nbformat.read(path, as_version=4)
                    executed = NotebookClient(notebook, timeout=120, kernel_name="python3", resources={"metadata":{"path":directory}}).execute()
                    self.assertFalse(any(output.output_type == "error" for cell in executed.cells if cell.cell_type == "code" for output in cell.outputs))
            exported = json.loads((target / "outputs/real-comparison.json").read_text(encoding="utf-8"))
            self.assertAlmostEqual(exported["results"][0]["population"], 3058259.422010836, places=4)
            self.assertIs(exported["results"][0]["metadata"]["synthetic"], False)
            self.assertTrue((target / "outputs/real-comparison.csv").exists())
            self.assertTrue((target / "outputs/real-count-cell.geojson").exists())
