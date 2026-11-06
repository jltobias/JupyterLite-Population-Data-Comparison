"""Optional preparation-only checks; CI needs no raster packages or raw cache."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import prepare_population as prep
except ImportError:
    prep = None


@unittest.skipIf(prep is None, "Optional NumPy/rasterio preparation dependencies unavailable")
class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "test-results").mkdir(exist_ok=True)

    def test_atomic_download_repair_and_interruption(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "test-results") as directory, patch.object(prep, "CACHE", Path(directory)):
            target = Path(directory) / "source.tif"
            expected = hashlib.sha256(b"complete").hexdigest()
            def interrupted(url, path):
                Path(path).write_bytes(b"partial")
                raise OSError("interrupted")
            with patch.object(prep.urllib.request, "urlretrieve", side_effect=interrupted), self.assertRaises(OSError):
                prep.acquire(target.name, "https://example.test/source", expected, True)
            self.assertFalse(target.exists())
            target.write_bytes(b"old incomplete")
            with self.assertRaises(ValueError):
                prep.acquire(target.name, "https://example.test/source", expected, False)
            with patch.object(prep.urllib.request, "urlretrieve", side_effect=lambda url,path: Path(path).write_bytes(b"wrong")), self.assertRaises(ValueError):
                prep.acquire(target.name, "https://example.test/source", expected, True)
            self.assertEqual(target.read_bytes(), b"old incomplete")
            with patch.object(prep.urllib.request, "urlretrieve", side_effect=lambda url,path: Path(path).write_bytes(b"complete")):
                prep.acquire(target.name, "https://example.test/source", expected, True)
            with patch.object(prep.urllib.request, "urlretrieve", side_effect=interrupted) as request:
                prep.acquire(target.name, "https://example.test/source", expected, True)
                request.assert_not_called()
            self.assertEqual(target.read_bytes(), b"complete")

    def test_manual_retrieval_date_is_explicit_and_receipts_win(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "test-results") as directory:
            path = Path(directory) / "manual.tif"
            path.touch()
            with self.assertRaisesRegex(ValueError, "retrieval-date"):
                prep.retrieval_date(path)
            self.assertEqual(prep.retrieval_date(path, "2026-11-06"), "2026-11-06")
            prep.write(path.with_suffix(".tif.retrieval.json"), {"retrieval_date":"2024-01-02"})
            self.assertEqual(prep.retrieval_date(path, "2026-11-06"), "2024-01-02")

    def test_later_source_failure_leaves_all_publication_inputs_unchanged(self):
        cache = ROOT / ".cache/population"
        if not (cache / "nga_pop_2025_CN_100m_R2025A_v1.tif").exists():
            self.skipTest("Raw preparation cache is intentionally not required in CI")
        with tempfile.TemporaryDirectory(dir=ROOT / "test-results") as directory:
            project = Path(directory)
            shutil.copytree(ROOT / "data", project / "data")
            snapshot = {p.relative_to(project):p.read_bytes() for p in (project / "data").rglob("*") if p.is_file()}
            actual_open = prep.rasterio.open
            def fail_late(path, *args, **kwargs):
                if Path(path).name == "GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0_R9_C19.tif":
                    raise ValueError("induced later source failure")
                return actual_open(path, *args, **kwargs)
            with patch.object(prep,"ROOT",project),patch.object(prep,"OUT",project / "data/real"),patch.object(prep,"CACHE",cache),patch.object(prep.rasterio,"open",side_effect=fail_late),patch.object(sys,"argv",["prepare_population.py","--retrieval-date","2026-11-06"]),self.assertRaisesRegex(ValueError,"induced later"):
                prep.main()
            self.assertEqual(snapshot,{p.relative_to(project):p.read_bytes() for p in (project / "data").rglob("*") if p.is_file()})
