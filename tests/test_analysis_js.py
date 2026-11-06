import subprocess
import unittest
from pathlib import Path
from playwright._impl._driver import compute_driver_executable

ROOT = Path(__file__).resolve().parents[1]


class JavaScriptAnalysisTests(unittest.TestCase):
    def test_numerical_and_metadata_regressions(self):
        node, _ = compute_driver_executable()
        subprocess.run([str(node), str(ROOT / "tests/analysis_regressions.mjs")], check=True, cwd=ROOT)
        subprocess.run([str(node), str(ROOT / "tests/bbox_regressions.mjs")], check=True, cwd=ROOT)
