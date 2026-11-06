"""Exercise the built workspace at its real GitHub Pages repository prefix.

Requires Playwright Chromium. Runs real JupyterLite notebook cells through its
JupyterLab command registry and checks the kernel model's computed outputs.
"""
import argparse
import csv
import hashlib
import io
import json
import threading
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
PREFIX = "/JupyterLite-Population-Data-Comparison/"


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = unquote(urlsplit(path).path)
        if not path.startswith(PREFIX):
            return str(SITE / "__outside_publication_prefix__")
        target = (SITE / path[len(PREFIX):]).resolve()
        if not target.is_relative_to(SITE.resolve()):
            return str(SITE / "__invalid_path__")
        return str(target)

    def log_message(self, *_):
        pass


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attributes):
        for key, value in attributes:
            if key in ("href", "src") and value:
                self.links.append(value)


def check_publication():
    manifest = json.loads((SITE / "publication.json").read_text(encoding="utf-8"))
    assert manifest["fixture_sha256"] == hashlib.sha256((ROOT / "data/demo.json").read_bytes()).hexdigest()
    assert (SITE / "data/demo.json").read_bytes() == (SITE / "lab/files/demo.json").read_bytes() == (ROOT / "data/demo.json").read_bytes()
    assert (SITE / "lab/files/population_tools.py").read_bytes() == (ROOT / "notebooks/population_tools.py").read_bytes()
    for relative, source in {"lab/files/population_tools.py": "notebooks/population_tools.py", "viewer/analysis.js": "viewer/analysis.js"}.items():
        assert manifest["calculation_sha256"][relative] == hashlib.sha256((SITE / relative).read_bytes()).hexdigest() == hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
    for name, digest in manifest["notebook_sha256"].items():
        assert hashlib.sha256((SITE / "lab/files" / name).read_bytes()).hexdigest() == digest
        canonical = json.loads((ROOT / "notebooks" / name).read_text(encoding="utf-8"))
        rendered = json.loads((SITE / "book/_sources" / name).read_text(encoding="utf-8"))
        assert [(c["cell_type"], c["source"]) for c in canonical["cells"]] == [(c["cell_type"], c["source"]) for c in rendered["cells"]]
    forbidden = {".git", ".agents", ".codex", ".aws", "_bmad", "_bmad-output", ".buildinfo", "rspack.config.js", "rspack.config.watch.js", "rspack.config.analyze.js"}
    for path in SITE.rglob("*"):
        assert not set(path.relative_to(SITE).parts) & forbidden, f"Development material in publication: {path}"
        assert path.relative_to(SITE).parts[0] not in {"tests","scripts"}
        assert not path.name.startswith(".jupyterlite.doit")
    for relative in ["index.html", "viewer/index.html", *[f"book/{name}.html" for name in ("intro", "methods", "credits", "01_introduction", "02_area_and_coverage", "03_import_and_export")]]:
        parser = Links()
        parser.feed((SITE / relative).read_text(encoding="utf-8"))
        for link in parser.links:
            if urlsplit(link).scheme or link.startswith(("#", "//")):
                continue
            destination = unquote(urlsplit(urljoin("https://example.org" + PREFIX + relative, link)).path)
            assert destination.startswith(PREFIX), (relative, link)
            assert (SITE / destination[len(PREFIX):]).exists(), f"Broken publication link: {relative}: {link}"
    print("Publication paths, canonical data/notebooks, and asset allowlist: PASS", flush=True)


def download_text(page, button):
    with page.expect_download() as pending:
        page.locator(button).click()
    return Path(pending.value.path()).read_text(encoding="utf-8")


def set_bounds(page, bounds):
    for key, value in zip(["west", "south", "east", "north"], bounds):
        page.locator("#" + key).fill(str(value))
    page.locator("#compare").click()


def csv_results(page):
    return list(csv.DictReader(io.StringIO(download_text(page, "#csv"))))


def check_viewer(page, base):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base + "viewer/index.html")
    page.wait_for_function("window.populationViewer?.results.length === 4")
    results = page.evaluate("populationViewer.results")
    assert all(abs(r["population"]-expected)<1e-7 for r,expected in zip(results,[400,400,800,240]))
    assert not page.locator("#error").is_visible()
    assert page.locator(".map .leaflet-control-attribution").count() == 4
    page.screenshot(path=str(ROOT / "test-results/viewer-default.png"), full_page=True)
    js_edges = page.evaluate("""async()=>{
      const a=await import('./analysis.js');
      const metadata=populationViewer.layers[0].metadata;
      const layer={metadata,cells:[{bounds:[0,30,2,60],population:1000}]};
      return [a.compare([layer],[0,30,1,45])[0],a.compare([{metadata,cells:[{bounds:[0,0,1,1],population:0}]}],[0,0,1,1])[0],a.compare([layer],[3,30,4,40])[0]];
    }""")
    import math
    expected = 500*(math.sin(math.pi/4)-.5)/(math.sin(math.pi/3)-.5)
    assert abs(js_edges[0]["population"]-expected)<1e-8
    assert js_edges[1]["population"] == 0 and js_edges[1]["coverage"] == 1
    assert js_edges[2]["population"] is None and js_edges[2]["coverage"] == 0
    page.evaluate("populationViewer.maps[0].setView([14.25,120.25], 11, {animate:false})")
    assert page.evaluate("populationViewer.maps.every(m=>m.getCenter().distanceTo(populationViewer.maps[0].getCenter())<.01 && m.getZoom()===11)")
    page.locator("#sync").uncheck()
    page.evaluate("populationViewer.maps[1].panTo([14.1,120.1],{animate:false})")
    assert page.evaluate("populationViewer.maps[0].getCenter().distanceTo(populationViewer.maps[1].getCenter())>1000")
    page.locator("#sync").check()
    page.locator("#reset").click()
    cell = page.locator('#map-0 path[role="button"]').first
    assert cell.get_attribute("tabindex") == "0" and "Inspect native cell" in cell.get_attribute("aria-label")
    cell.focus()
    cell.press("Enter")
    assert "Native cell:" in page.locator("#inspection").inner_text()
    page.locator("#map-0 path.leaflet-interactive").first.click(force=True)
    assert "Native cell:" in page.locator("#inspection").inner_text()
    # Invalid rectangle keeps previously valid results and bounds.
    before = page.evaluate("populationViewer.bounds")
    page.locator("#west").fill("121")
    page.locator("#compare").click()
    assert page.locator("#error").is_visible()
    assert page.evaluate("populationViewer.bounds") == before
    page.locator("#example").click()
    # A real two-click map drawing interaction changes the analytical bounds.
    page.locator("#draw").click()
    page.locator("#map-0").click(position={"x":180,"y":100})
    page.locator("#map-0").click(position={"x":300,"y":180})
    assert page.evaluate("populationViewer.bounds") != before
    assert page.locator("#draw").get_attribute("aria-pressed") == "false"
    page.locator("#example").click()
    # Downloaded values and complete provenance survive outside the app.
    exported = json.loads(download_text(page,"#json"))
    assert exported["bounds"] == before and len(exported["results"]) == 4
    rows = csv_results(page)
    row = rows[0]
    assert json.loads(row["metadata_json"])["notice"].startswith("SYNTHETIC")
    for row, result in zip(rows, exported["results"]):
        assert abs(float(row["population"]) - result["population"]) < 1e-7
        assert abs(float(row["coverage"]) - result["coverage"]) < 1e-12
        assert int(row["intersected_cells"]) == result["intersected_cells"]
    svg = download_text(page,"#svg")
    assert "Source:" in svg and "CC0-1.0" in svg and "&quot;bounds&quot;" in svg
    svg_root = ET.fromstring(svg)
    visible_text = " ".join(node.text or "" for node in svg_root.iter("{http://www.w3.org/2000/svg}text"))
    for result in exported["results"]:
        assert f"Coverage: {result['coverage']*100:.1f}%" in visible_text
        assert result["metadata"]["population_concept"] in visible_text
    assert "Population concept:" in visible_text and "Source:" in visible_text
    # The same UI and exports must distinguish covered zero from missing data.
    set_bounds(page, [120,14,120.1,14.1])
    assert page.locator("#results tr").nth(2).locator("td").nth(1).inner_text() == "0"
    assert page.locator("#chart .bar-row").nth(2).locator("strong").inner_text() == "0"
    zero_json = json.loads(download_text(page,"#json"))
    zero = next(r for r in zero_json["results"] if r["metadata"]["id"] == "ambient")
    zero_csv = next(r for r in csv_results(page) if r["id"] == "ambient")
    assert zero["population"] == 0 and abs(zero["coverage"]-1) < 1e-12
    assert zero_csv["population"] != "" and float(zero_csv["population"]) == 0 and int(zero_csv["intersected_cells"]) == 1
    set_bounds(page, [120.2,14.2,120.4,14.4])
    assert page.locator("#results tr").nth(3).locator("td").nth(1).inner_text() == "No coverage"
    assert page.locator("#chart .bar-row").nth(3).locator("strong").inner_text() == "No coverage"
    missing_json = json.loads(download_text(page,"#json"))
    missing = next(r for r in missing_json["results"] if r["metadata"]["id"] == "partial")
    missing_csv = next(r for r in csv_results(page) if r["id"] == "partial")
    assert missing["population"] is None and missing["coverage"] == 0 and missing["intersected_cells"] == 0
    assert missing_csv["population"] == "" and float(missing_csv["coverage"]) == 0 and int(missing_csv["intersected_cells"]) == 0
    page.locator("#example").click()
    # Selectors are independent; duplicate layers produce one comparison row.
    page.locator("#layer-0").select_option("settlement")
    assert page.locator("#layer-1").input_value() == "settlement"
    assert page.locator("#results tr").count() == 3
    # Import far from the teaching extent; the grid must become visible.
    imported = json.loads((ROOT / "data/import-example.geojson").read_text(encoding="utf-8"))
    imported["metadata"].update(id="far-grid", title="Synthetic distant import", notice="KEEP THIS OPTIONAL PROVIDER NOTICE", attribution_parties=["Original producer", "Distributor"], optional_object={"toString":"provider value"})
    for feature in imported["features"]:
        for point in feature["geometry"]["coordinates"][0]:
            point[0] -= 110
    page.locator("#import").set_input_files({"name":"far.geojson","mimeType":"application/geo+json","buffer":json.dumps(imported).encode()})
    page.wait_for_function("populationViewer.layers.length===5")
    assert page.evaluate("Math.abs(populationViewer.maps[0].getCenter().lng-10.2)<.1")
    assert '"toString":"provider value"' in page.locator("#metadata-0").text_content()
    for key,value in zip(["west","south","east","north"],[10.1,14.1,10.3,14.3]):
        page.locator("#"+key).fill(str(value))
    page.locator("#compare").click()
    far = page.evaluate("populationViewer.results.find(r=>r.metadata.id==='far-grid')")
    assert abs(far["population"]-400)<1e-7
    far_rows = list(csv.DictReader(io.StringIO(download_text(page,"#csv"))))
    metadata = json.loads(next(r["metadata_json"] for r in far_rows if r["id"]=="far-grid"))
    assert metadata["notice"] == "KEEP THIS OPTIONAL PROVIDER NOTICE" and metadata["attribution_parties"] == ["Original producer","Distributor"]
    old = page.evaluate("({ids:populationViewer.layers.map(l=>l.metadata.id),bounds:populationViewer.bounds,results:populationViewer.results})")
    for invalid in ("negative", "people/km2", "EPSG:3857"):
        rejected = json.loads(json.dumps(imported))
        rejected["metadata"]["id"] = "rejected-" + invalid
        if invalid == "negative":
            rejected["features"][0]["properties"]["population"] = -1
        elif invalid == "people/km2":
            rejected["metadata"]["units"] = invalid
        else:
            rejected["metadata"]["crs"] = invalid
        page.locator("#error").evaluate("el=>el.hidden=true")
        page.locator("#import").set_input_files({"name":"bad.geojson","mimeType":"application/json","buffer":json.dumps(rejected).encode()})
        page.locator("#error").wait_for(state="visible")
        assert "Import rejected" in page.locator("#error").inner_text()
        assert page.evaluate("({ids:populationViewer.layers.map(l=>l.metadata.id),bounds:populationViewer.bounds,results:populationViewer.results})") == old
    polar = {"type":"FeatureCollection", "metadata":{**imported["metadata"],"id":"polar","title":"Synthetic polar grid"}, "features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[0,88],[1,88],[1,90],[0,90],[0,88]]]},"properties":{"population":50}}]}
    page.locator("#import").set_input_files({"name":"polar.geojson","mimeType":"application/json","buffer":json.dumps(polar).encode()})
    page.wait_for_function("populationViewer.layers.length===6")
    assert page.evaluate("populationViewer.maps[0].getCenter().lat>87")
    assert page.locator("#map-0 path.leaflet-interactive").first.get_attribute("d") != "M0 0"
    assert not errors, errors
    page.screenshot(path=str(ROOT / "test-results/viewer-desktop.png"), full_page=True)
    page.set_viewport_size({"width":390,"height":844})
    page.reload()
    page.wait_for_function("window.populationViewer?.results.length===4")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    long_title = json.loads((ROOT / "data/import-example.geojson").read_text(encoding="utf-8"))
    long_title["metadata"].update(id="long-mobile-title", title="X"*4000)
    page.locator("#import").set_input_files({"name":"long-title.geojson","mimeType":"application/json","buffer":json.dumps(long_title).encode()})
    page.wait_for_function("populationViewer.layers.length===5 && populationViewer.results.some(r=>r.metadata.id==='long-mobile-title')")
    assert not page.locator("#error").is_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(ROOT / "test-results/viewer-mobile.png"), full_page=True)
    page.set_viewport_size({"width":1440,"height":1000})
    # Required-data failure gives a visible explanatory error.
    page.route("**/data/demo.json", lambda route: route.abort())
    page.reload()
    page.locator("#error").wait_for(state="visible")
    assert "Unable to start" in page.locator("#error").inner_text()
    page.unroute("**/data/demo.json")
    page.route("**/viewer/app.js", lambda route: route.abort())
    page.reload()
    page.locator("#error").wait_for(state="visible")
    assert "required asset" in page.locator("#error").inner_text()
    page.unroute("**/viewer/app.js")
    print("Viewer navigation, inspection, drawing, imports, exports, mobile, and load failure: PASS", flush=True)


def check_lab(page, base):
    print("Opening the actual JupyterLite application...", flush=True)
    page.goto(base + "lab/lab/index.html?path=01_introduction.ipynb")
    page.wait_for_function("window.jupyterapp?.started", timeout=120000)
    for name in ("01_introduction.ipynb", "02_area_and_coverage.ipynb", "03_import_and_export.ipynb"):
        if name != "01_introduction.ipynb":
            page.evaluate("async name=>{await jupyterapp.commands.execute('docmanager:open',{path:name,factory:'Notebook'});}", name)
        page.wait_for_function("name=>jupyterapp.shell.currentWidget?.context?.path===name && jupyterapp.shell.currentWidget.context.isReady", arg=name, timeout=120000)
        print(f"JupyterLite {name} loaded; waiting for browser kernel...", flush=True)
        page.wait_for_function("jupyterapp.shell.currentWidget.sessionContext?.session?.kernel?.status==='idle'", timeout=120000)
        # Track the real command completion; inspect model outputs rather than source text.
        page.evaluate("""()=>{
          window.notebookRunState={done:false};
          window.notebookRun=jupyterapp.commands.execute('notebook:run-all-cells');
          window.notebookRun.then(result=>{window.notebookRunState={done:true,result};},error=>{window.notebookRunState={done:true,error:String(error)};});
        }""")
        page.wait_for_function("window.notebookRunState.done", timeout=240000)
        assert page.evaluate("window.notebookRunState") == {"done": True, "result": True}
        outputs = page.evaluate("Array.from(jupyterapp.shell.currentWidget.content.model.cells).map(c=>c.toJSON()).filter(c=>c.cell_type==='code').map(c=>({execution_count:c.execution_count,outputs:c.outputs}))")
        assert outputs and all(cell["execution_count"] is not None for cell in outputs), outputs
        assert not any(output.get("output_type")=="error" for cell in outputs for output in cell["outputs"]), outputs
        if name == "01_introduction.ipynb":
            assert "BROWSER_COMPUTATION_OK: 400, 400, 800, 240" in json.dumps(outputs)
        elif name == "02_area_and_coverage.ipynb":
            assert "Covered zero: 0.0" in json.dumps(outputs) and "Missing: None" in json.dumps(outputs)
        else:
            assert "Validated SYNTHETIC cells:" in json.dumps(outputs) and "synthetic-comparison.csv" in json.dumps(outputs)
        print(f"Actual browser execution and model outputs: {name}: PASS", flush=True)
    # Read files actually created by lesson 3 from JupyterLite's contents manager.
    page.wait_for_function("""async()=>{
      try{
        const contents=jupyterapp.serviceManager.contents;
        const csv=await contents.get('outputs/synthetic-comparison.csv',{content:true,format:'text'});
        const json=await contents.get('outputs/synthetic-comparison.json',{content:true,format:'text'});
        window.labExports={csv:csv.content,json:json.content};
        return typeof csv.content==='string' && typeof json.content==='string';
      }catch{return false;}
    }""", timeout=30000)
    files = page.evaluate("window.labExports")
    exported = json.loads(files["json"])
    row = next(csv.DictReader(io.StringIO(files["csv"])))
    result = exported["results"][0]
    assert abs(result["population"]-400) < 1e-7 and abs(float(row["population"])-400) < 1e-7
    assert abs(result["coverage"]-1) < 1e-12 and abs(float(row["coverage"])-1) < 1e-12
    assert result["intersected_cells"] == int(row["intersected_cells"]) == 4
    assert exported["bounds"] == [120.1,14.1,120.3,14.3] and exported["method"] == result["method"] == row["method"]
    assert result["metadata"]["synthetic"] is True and json.loads(row["metadata_json"]) == result["metadata"]
    assert result["metadata"]["id"] == "notebook-import" and "SYNTHETIC" in exported["notice"]
    page.screenshot(path=str(ROOT / "test-results/lab-executed.png"), full_page=True)
    print("All three JupyterLite notebooks and lesson 3 generated CSV/JSON: PASS", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", help="Verify an already-served site, including its repository prefix")
    args = parser.parse_args()
    check_publication()
    (ROOT / "test-results").mkdir(exist_ok=True)
    server = None
    if args.base_url:
        base = args.base_url.rstrip("/") + "/"
    else:
        server = ThreadingHTTPServer(("127.0.0.1",0), Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        base = f"http://127.0.0.1:{server.server_port}" + PREFIX
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width":1440,"height":1000})
            page.goto(base)
            assert page.locator("nav.cards a").count() == 3
            served_manifest = page.request.get(base + "publication.json").json()
            for relative in ("lab/files/population_tools.py", "viewer/analysis.js"):
                response = page.request.get(base + relative)
                assert response.ok and hashlib.sha256(response.body()).hexdigest() == served_manifest["calculation_sha256"][relative]
                assert served_manifest["calculation_sha256"][relative] == json.loads((SITE / "publication.json").read_text(encoding="utf-8"))["calculation_sha256"][relative]
            page.goto(base + "book/intro.html")
            assert page.get_by_role("heading",name="Population grids in the browser",exact=True).is_visible()
            try:
                check_viewer(page,base)
                check_lab(page,base)
            except Exception:
                page.screenshot(path=str(ROOT / "test-results/browser-failure.png"), full_page=True)
                print("Browser failure state:", page.evaluate("({url:location.href,body:document.body.innerText.slice(-3000),kernel:window.jupyterapp?.shell.currentWidget?.sessionContext?.session?.kernel?.status})"), flush=True)
                raise
            finally:
                browser.close()
    finally:
        if server:
            server.shutdown()


if __name__ == "__main__":
    main()
