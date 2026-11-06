"""Build a publication tree from an explicit allowlist, never the repo root."""
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
STAGE = ROOT / "_build"
NOTEBOOKS = ("01_introduction.ipynb", "02_area_and_coverage.ipynb", "03_import_and_export.ipynb")


def clean(path):
    if path.resolve().parent != ROOT or path.name not in ("_site", "_build"):
        raise ValueError("Build cleanup is restricted to the workspace's _site and _build directories.")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def run(arguments, cwd):
    subprocess.run(arguments, cwd=cwd, check=True)


def main():
    clean(SITE)
    clean(STAGE)
    book = STAGE / "book"
    lab = STAGE / "lite"
    content = lab / "content"
    book.mkdir()
    content.mkdir(parents=True)
    for name in ("_config.yml", "_toc.yml", "intro.md", "methods.md", "credits.md"):
        copy(ROOT / "book" / name, book / name)
    for name in NOTEBOOKS + ("population_tools.py",):
        for destination in (book, content):
            copy(ROOT / "notebooks" / name, destination / name)
    for destination in (book, content):
        copy(ROOT / "data/demo.json", destination / "demo.json")
    for name in ("README.md", "import-example.geojson"):
        copy(ROOT / "data" / name, content / name)
    # The runtime URL and package versions are pinned; Lab has no population-service dependency.
    (lab / "jupyter-lite.json").write_text(json.dumps({"jupyter-config-data": {"appName": "Population Comparison Lab", "exposeAppInBrowser": True}}, indent=2), encoding="utf-8")
    run(["jupyter-book", "build", str(book), "--warningiserror", "--keep-going"], ROOT)
    shutil.copytree(book / "_build/html", SITE / "book")
    distribution = importlib.metadata.distribution("jupyterlite-pyodide-kernel")
    extension = next(Path(distribution.locate_file(path)).resolve().parent for path in distribution.files if str(path).endswith("pyodide-kernel-extension/package.json"))
    # Keep the doit cache inside the freshly recreated staging directory.
    run(["jupyter", "lite", "build", "--lite-dir", str(lab), "--contents", str(content), "--output-dir", str(SITE / "lab"), "--apps", "lab", "--no-sourcemaps", "--no-unused-shared-packages", "--ignore-sys-prefix", "--LiteBuildConfig.federated_extensions=" + str(extension)], lab)
    runtime = json.loads((SITE / "lab/jupyter-lite.json").read_text(encoding="utf-8"))["jupyter-config-data"]
    if not runtime.get("exposeAppInBrowser") or not any(ext["name"] == "@jupyterlite/pyodide-kernel-extension" for ext in runtime["federated_extensions"]):
        raise RuntimeError("Lab runtime configuration or its Python kernel is missing.")
    # Upstream source/build helpers are not runtime assets or course content.
    for name in (".buildinfo",):
        (SITE / "book" / name).unlink(missing_ok=True)
    for name in ("package.json", "jupyter-lite.ipynb", "rspack.config.js", "rspack.config.analyze.js", "rspack.config.watch.js", "lab/package.json", "lab/jupyter-lite.ipynb"):
        (SITE / "lab" / name).unlink(missing_ok=True)
    # Publish JSON runtime settings only; avoid requests for removed config notebooks.
    bootstrap = SITE / "lab/config-utils.js"
    bootstrap_text = bootstrap.read_text(encoding="utf-8")
    old = "const LITE_FILES = ['jupyter-lite.json', 'jupyter-lite.ipynb'];"
    if old not in bootstrap_text:
        raise RuntimeError("Pinned JupyterLite configuration loader changed; recheck publication cleanup.")
    bootstrap.write_text(bootstrap_text.replace(old, "const LITE_FILES = ['jupyter-lite.json'];"), encoding="utf-8", newline="\n")
    # Explicit project assets only: never publish _bmad, config, tests, credentials, or Git metadata.
    for name in ("index.html", "app.js", "analysis.js", "style.css"):
        copy(ROOT / "viewer" / name, SITE / "viewer" / name)
    for name in ("leaflet.js", "leaflet.css", "LICENSE", "images/layers.png", "images/layers-2x.png", "images/marker-icon.png", "images/marker-icon-2x.png", "images/marker-shadow.png"):
        copy(ROOT / "viewer/vendor/leaflet" / name, SITE / "viewer/vendor/leaflet" / name)
    for name in ("demo.json", "import-example.geojson", "README.md"):
        copy(ROOT / "data" / name, SITE / "data" / name)
    for name in ("population-comparison-splash.png", "README.md"):
        copy(ROOT / "assets" / name, SITE / "assets" / name)
    copy(ROOT / "LICENSE", SITE / "LICENSE")
    copy(ROOT / "site/index.html", SITE / "index.html")
    (SITE / ".nojekyll").touch()
    manifest = {"fixture_sha256": hashlib.sha256((ROOT / "data/demo.json").read_bytes()).hexdigest(), "notebook_sha256": {name: hashlib.sha256((ROOT / "notebooks" / name).read_bytes()).hexdigest() for name in NOTEBOOKS}, "calculation_sha256": {"lab/files/population_tools.py": hashlib.sha256((ROOT / "notebooks/population_tools.py").read_bytes()).hexdigest(), "viewer/analysis.js": hashlib.sha256((ROOT / "viewer/analysis.js").read_bytes()).hexdigest()}, "destinations": ["book/intro.html", "lab/lab/index.html", "viewer/index.html"]}
    (SITE / "publication.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Built Book, Lab, and viewer in _site. Only approved publication assets were copied.")


if __name__ == "__main__":
    main()
