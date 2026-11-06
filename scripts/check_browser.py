"""Verify real publication, actual local TIFF worker and all three Pyodide lessons."""
import argparse
import base64
import csv
import hashlib
import io
import json
import sys
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
NOTEBOOKS = ("01_real_population.ipynb", "02_real_coverage.ipynb", "03_real_exports.ipynb")
sys.path.insert(0, str(ROOT / "tests"))
from tiff_fixtures import tiff


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = unquote(urlsplit(path).path)
        if not path.startswith(PREFIX):
            return str(SITE / "__outside_publication_prefix__")
        target = (SITE / path[len(PREFIX):]).resolve()
        return str(target if target.is_relative_to(SITE.resolve()) else SITE / "__invalid_path__")

    def log_message(self, *_):
        pass


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attributes):
        self.links.extend(value for key, value in attributes if key in ("href", "src") and value)


def check_publication():
    manifest = json.loads((SITE / "publication.json").read_text(encoding="utf-8"))
    assert manifest["launch_notebook"] == NOTEBOOKS[0]
    for name, key in (("population.json", "population_sha256"), ("demo.json", "fixture_sha256")):
        canonical = (ROOT / "data" / name).read_bytes()
        assert canonical == (SITE / "data" / name).read_bytes() == (SITE / "lab/files" / name).read_bytes()
        assert hashlib.sha256(canonical).hexdigest() == manifest[key]
    for name, digest in manifest["real_assets_sha256"].items():
        assert hashlib.sha256((SITE / "data/real" / name).read_bytes()).hexdigest() == digest
    for name, digest in manifest["calculation_sha256"].items():
        assert hashlib.sha256((SITE / name).read_bytes()).hexdigest() == digest
    assert manifest["raster_reader_sha256"] == "8cfc01ffc945904766d8fb89f19da7afb799e342834454f5592fbcf0bcfe2db5"
    for name, digest in manifest["notebook_sha256"].items():
        assert hashlib.sha256((SITE / "lab/files" / name).read_bytes()).hexdigest() == digest
        canonical = json.loads((ROOT / "notebooks" / name).read_text(encoding="utf-8"))
        rendered = json.loads((SITE / "book/_sources" / name).read_text(encoding="utf-8"))
        assert [(c["cell_type"], c["source"]) for c in canonical["cells"]] == [(c["cell_type"], c["source"]) for c in rendered["cells"]]
    forbidden = {".git", ".agents", ".codex", ".aws", ".cache", "_bmad", "_bmad-output", ".buildinfo", "rspack.config.js", "rspack.config.watch.js", "rspack.config.analyze.js"}
    for path in SITE.rglob("*"):
        assert not set(path.relative_to(SITE).parts) & forbidden, path
        assert path.relative_to(SITE).parts[0] not in {"tests", "scripts"}
        assert not path.name.startswith(".jupyterlite.doit")
    for relative in ["index.html", "viewer/index.html", *[f"book/{name}.html" for name in ("intro", "methods", "credits", *(n[:-6] for n in NOTEBOOKS))]]:
        parser = Links()
        parser.feed((SITE / relative).read_text(encoding="utf-8"))
        for link in parser.links:
            if urlsplit(link).scheme or link.startswith(("#", "//")):
                continue
            destination = unquote(urlsplit(urljoin("https://example.org"+PREFIX+relative, link)).path)
            assert destination.startswith(PREFIX), (relative, link)
            assert (SITE / destination[len(PREFIX):]).exists(), (relative, link)
    print("Publication allowlist, real assets, canonical lessons and hashes: PASS", flush=True)


def download_text(page, button):
    with page.expect_download() as pending:
        page.locator(button).click()
    return Path(pending.value.path()).read_text(encoding="utf-8")


def set_bounds(page, bounds):
    for key, value in zip(("west", "south", "east", "north"), bounds):
        page.locator("#"+key).fill(str(value))
    page.locator("#compare").click()


def worker(page, content, bounds=(10, 19.8, 10.2, 20)):
    return page.evaluate("""async({encoded,bounds})=>{
      const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
      return await new Promise(resolve=>{
        const w=new Worker(new URL('raster-worker.js',location.href));
        const timer=setTimeout(()=>{w.terminate();resolve({error:'Worker timeout'});},15000);
        w.onmessage=({data})=>{clearTimeout(timer);w.terminate();resolve(data);};
        w.onerror=e=>{clearTimeout(timer);w.terminate();resolve({error:e.message});};
        w.postMessage({file:new File([bytes],'fixture.tif'),bounds});
      });
    }""", {"encoded":base64.b64encode(content).decode(), "bounds":list(bounds)})


def check_viewer(page, base):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base+"viewer/index.html")
    page.wait_for_function("window.populationViewer?.results.length===4")
    oracle = json.loads((ROOT / "data/real/independent_oracle.json").read_text(encoding="utf-8"))
    original = page.evaluate("populationViewer.results")
    for result in original:
        expected = oracle["sources"][result["metadata"]["id"]]
        assert result["metadata"]["synthetic"] is False
        assert abs(result["population"]-expected["aoi_population"])<.0001
        assert abs(result["coverage"]-min(1,expected["aoi_coverage"]))<1e-10
        assert result["intersected_cells"]==expected["aoi_intersected_cells"]
    assert page.locator(".native-grid").count()==4
    assert page.locator(".map path").count()<20  # Native pixels do not become individual SVG nodes.
    assert not page.locator("#error").is_visible()
    assert "01_real_population.ipynb" in page.get_by_role("link",name="Run the notebooks").get_attribute("href")
    page.locator("#inspect-lon").fill("3.35")
    page.locator("#inspect-lat").fill("6.5")
    page.locator("#inspect-lat").press("Enter")
    assert "Native cell:" in page.locator("#inspection").inner_text()
    page.locator("#map-1").click(position={"x":200,"y":130})
    assert "GRID3" in page.locator("#inspection").inner_text()
    page.evaluate("populationViewer.maps[0].setView([6.55,3.4],11,{animate:false})")
    assert page.evaluate("populationViewer.maps.every(m=>m.getCenter().distanceTo(populationViewer.maps[0].getCenter())<.01&&m.getZoom()===11)")
    page.locator("#sync").uncheck()
    page.evaluate("populationViewer.maps[1].panTo([6.4,3.2],{animate:false})")
    assert page.evaluate("populationViewer.maps[0].getCenter().distanceTo(populationViewer.maps[1].getCenter())>1000")
    page.locator("#sync").check()
    page.locator("#reset").click()
    before = page.evaluate("populationViewer.bounds")
    page.locator("#west").fill("10")
    page.locator("#compare").click()
    assert page.locator("#error").is_visible() and page.evaluate("populationViewer.bounds")==before
    page.locator("#example").click()
    page.locator("#draw").click()
    page.locator("#map-0").click(position={"x":160,"y":100})
    page.locator("#map-0").click(position={"x":300,"y":180})
    assert page.evaluate("populationViewer.bounds")!=before
    page.locator("#example").click()
    exported = json.loads(download_text(page,"#json"))
    rows = list(csv.DictReader(io.StringIO(download_text(page,"#csv"))))
    for row,result in zip(rows,exported["results"]):
        assert float(row["population"])==result["population"]
        assert float(row["coverage"])==result["coverage"]
        assert json.loads(row["metadata_json"])==result["metadata"]
        assert json.loads(row["grid"])==result["grid"]
    svg=ET.fromstring(download_text(page,"#svg"))
    description=json.loads(svg.find("{http://www.w3.org/2000/svg}desc").text)
    assert description["results"]==exported["results"]
    assert "CC BY 4.0" in " ".join(svg.itertext())
    set_bounds(page,[0,0,1,1])
    assert all(r["population"] is None and r["coverage"]==0 for r in page.evaluate("populationViewer.results"))
    assert "outside" in page.locator("#comparison-warnings").inner_text()
    page.locator("#example").click()
    page.screenshot(path=str(ROOT/"test-results/viewer-default.png"),full_page=True)
    # All four real prepared TIFFs exercise the shipped reader through the actual UI.
    for index,id_ in enumerate(oracle["sources"]):
        page.locator("#raster-preset").select_option(str(index))
        page.locator("#raster-file").set_input_files(str(ROOT/"data/real"/(id_+".tif")))
        page.locator("#raster-declaration").check()
        page.locator("#raster-submit").click()
        page.wait_for_function("n=>populationViewer.layers.length===n",arg=5+index)
        result=page.evaluate("populationViewer.results[0]")
        assert abs(result["population"]-oracle["sources"][id_]["aoi_population"])<.0001
        assert "processing_receipt" not in result["metadata"] and "validation" not in result["metadata"]
        assert result["metadata"]["file_declarations"]["native_window"]
        assert result["metadata"]["provenance_status"].startswith("User-declared")
    # Re-select a different area inside the local native window; values stay native.
    set_bounds(page,[3.32,6.48,3.40,6.56])
    parity=page.evaluate("""async()=>{const a=await import('./analysis.js');const local=populationViewer.layers.at(-1),source=populationViewer.layers[3];return [a.compare([local],populationViewer.bounds)[0].population,a.compare([source],populationViewer.bounds)[0].population];}""")
    assert abs(parity[0]-parity[1])<.0001
    # Cancel synchronously before a worker result; valid session remains intact.
    page.locator("#raster-preset").select_option("0")
    metadata=json.loads(page.locator("#raster-metadata").input_value());metadata["id"]="cancelled"
    page.locator("#raster-metadata").fill(json.dumps(metadata))
    page.evaluate("document.getElementById('raster-submit').click();document.getElementById('raster-cancel').click()")
    assert "cancelled" in page.locator("#raster-status").inner_text()
    assert page.evaluate("populationViewer.layers.length")==8
    # Literal TIFF masks/NoData, validation, metadata and decompression limits.
    supported=worker(page,tiff())
    assert supported.get("grid",{}).get("values")==[0,None,10,20],supported
    sparse=worker(page,tiff(sparse=True))
    assert sparse.get("grid",{}).get("values")==[None,None,10,20],sparse
    deflated=worker(page,tiff(compression=8))
    assert deflated.get("grid",{}).get("values")==[0,None,10,20],deflated
    lzw=worker(page,tiff(compression=5))
    assert lzw.get("grid",{}).get("values")==[0,None,10,20],lzw
    cases={"CRS":tiff(epsg=3857),"mask":tiff(kind=4),"scale":tiff(metadata='<GDALMetadata><Item name="SCALE" sample="0" role="scale">2</Item></GDALMetadata>'),"negative":tiff(values=(-1,0,1,2)),"undeclared NaN":tiff(nodata=None),"big endian":tiff(big_endian=True),"IFD loop":tiff(loop=True),"IFD entry budget":tiff(large_entries=True),"decompression bound":tiff(bomb=True)}
    cases.update({"zero TileWidth":tiff(tile_width=0),"zero TileLength":tiff(tile_height=0),"zero RowsPerStrip":tiff(rows_per_strip=0),"garbage NoData":tiff(nodata="garbage"),"role scale":tiff(metadata='<GDALMetadata><Item name="x" role="scale">2</Item></GDALMetadata>'),"role offset":tiff(metadata='<GDALMetadata><Item name="x" role="offset">0</Item></GDALMetadata>')})
    for name,content in cases.items():
        result=worker(page,content)
        assert result.get("error") and "timeout" not in result["error"].lower(),(name,result)
    oversized=worker(page,tiff(width=600,height=600),(10,-40,70,20))
    assert "262144" in oversized.get("error",""),oversized
    state=page.evaluate("({layers:populationViewer.layers.length,bounds:populationViewer.bounds,results:populationViewer.results})")
    page.locator("#raster-file").set_input_files({"name":"negative.tif","mimeType":"image/tiff","buffer":cases["negative"]})
    for key,value in zip(("rw","rs","re","rn"),(10,19.8,10.2,20)):
        page.locator("#"+key).fill(str(value))
    page.locator("#raster-submit").click()
    page.locator("#error").wait_for(state="visible")
    assert "TIFF import rejected" in page.locator("#error").inner_text()
    assert page.evaluate("({layers:populationViewer.layers.length,bounds:populationViewer.bounds,results:populationViewer.results})")==state
    # The retained small-cell GeoJSON path still validates, fits and exports metadata.
    vector=json.loads((ROOT/"data/import-example.geojson").read_text(encoding="utf-8"))
    vector["metadata"].update(id="browser-vector-fixture", notice="EXPLICIT SYNTHETIC FIXTURE", optional_object={"provider":"retained"},processing_receipt={"false_bundle_hash":"forged"},validation="forged",source_asset_sha256_locally_verified=True)
    page.locator("#import").set_input_files({"name":"fixture.geojson","mimeType":"application/geo+json","buffer":json.dumps(vector).encode()})
    page.wait_for_function("populationViewer.layers.length===9")
    set_bounds(page,[120.1,14.1,120.3,14.3])
    assert abs(page.evaluate("populationViewer.results[0].population")-400)<1e-7
    assert page.evaluate("populationViewer.results[0].metadata.optional_object.provider")=="retained"
    cleaned=json.loads(download_text(page,"#json"))["results"][0]["metadata"]
    assert all(key not in cleaned for key in ("processing_receipt","validation","source_asset_sha256_locally_verified"))
    assert cleaned["citation"]==vector["metadata"]["citation"] and cleaned["notice"]=="EXPLICIT SYNTHETIC FIXTURE"
    assert cleaned["file_declarations"]["name"]=="fixture.geojson"
    previous=page.evaluate("populationViewer.results")
    vector["metadata"]["id"]="rejected-vector"
    vector["features"][0]["properties"]["population"]=-1
    page.locator("#import").set_input_files({"name":"bad.geojson","mimeType":"application/json","buffer":json.dumps(vector).encode()})
    page.locator("#error").wait_for(state="visible")
    assert page.evaluate("populationViewer.results")==previous
    # A real File/worker import produces a tiny asymmetric native image, never transposed.
    page.locator("#raster-preset").select_option("0")
    metadata=json.loads(page.locator("#raster-metadata").input_value())
    metadata.update(id="asymmetric",title="Asymmetric local fixture",synthetic=True,population_concept="Fixture custom concept",reference_date="2001-02-03")
    page.locator("#raster-metadata").fill(json.dumps(metadata))
    for key,value in zip(("rw","rs","re","rn"),(10,19.8,10.3,20)):
        page.locator("#"+key).fill(str(value))
    page.locator("#raster-file").set_input_files({"name":"asymmetric.tif","mimeType":"image/tiff","buffer":tiff(values=(0,1000,float('nan'),100000,10000000,10000),width=3,compression=5)})
    page.locator("#raster-submit").click()
    page.wait_for_function("populationViewer.layers.length===10")
    pixels=page.evaluate("""async()=>{const img=document.querySelector('#map-0 .native-grid');await img.decode();const c=document.createElement('canvas');c.width=img.naturalWidth;c.height=img.naturalHeight;const x=c.getContext('2d');x.drawImage(img,0,0);return {width:c.width,height:c.height,rgba:Array.from(x.getImageData(0,0,c.width,c.height).data)};}""")
    assert (pixels["width"],pixels["height"])==(3,2),pixels
    expected=[238,243,223,235,179,215,174,235,0,0,0,0,37,133,119,235,16,52,69,235,102,183,158,235]
    assert all(abs(actual-wanted)<=1 for actual,wanted in zip(pixels["rgba"],expected)),pixels
    for key,value in (("inspect-panel","0"),("inspect-lon","10.05"),("inspect-lat","19.85")):
        (page.locator('#'+key).select_option(value) if key=="inspect-panel" else page.locator('#'+key).fill(value))
    page.locator("#inspect-lat").press("Enter")
    inspection=page.locator("#inspection").inner_text()
    assert "row 1, column 0" in inspection and "100,000" in inspection and "10, 19.8, 10.1, 19.9" in inspection,inspection
    for index in range(4):
        page.locator(f"#layer-{index}").select_option("asymmetric")
    warning=page.locator("#comparison-warnings").inner_text()
    assert "Fixture custom concept" in warning and "2001-02-03" in warning
    assert not any(name in warning for name in ("WorldPop","GRID3","LandScan","GHS-POP")),warning
    neutral=json.loads(download_text(page,"#json"))
    assert "Real source excerpts" not in neutral["notice"] and neutral["results"][0]["metadata"]["synthetic"] is True
    state=page.evaluate("({layers:populationViewer.layers.length,bounds:populationViewer.bounds,results:populationViewer.results,src:document.querySelector('#map-0 .native-grid').src})")
    metadata["id"]="wide-display"
    page.locator("#raster-metadata").fill(json.dumps(metadata))
    for key,value in zip(("rw","rs","re","rn"),(10,19.8,23.1072,20)):
        page.locator("#"+key).fill(str(value))
    page.locator("#raster-file").set_input_files({"name":"wide.tif","mimeType":"image/tiff","buffer":tiff(values=(0,)*262144,width=131072,height=2,dx=.0001)})
    page.locator("#raster-submit").click()
    page.wait_for_function("document.getElementById('raster-status').textContent==='Import rejected.'")
    assert "32767" in page.locator("#error").inner_text()
    assert page.evaluate("({layers:populationViewer.layers.length,bounds:populationViewer.bounds,results:populationViewer.results,src:document.querySelector('#map-0 .native-grid').src})")==state
    assert not errors,errors
    page.set_viewport_size({"width":390,"height":844})
    page.reload()
    page.wait_for_function("window.populationViewer?.results.length===4")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.screenshot(path=str(ROOT/"test-results/viewer-mobile.png"),full_page=True)
    page.set_viewport_size({"width":1440,"height":1000})
    page.route("**/data/population.json",lambda route:route.abort())
    page.reload()
    page.locator("#error").wait_for(state="visible")
    assert "Unable to start" in page.locator("#error").inner_text()
    assert page.evaluate("!window.populationViewer")
    page.unroute("**/data/population.json")
    page.route("**/viewer/app.js",lambda route:route.abort())
    page.reload()
    page.locator("#error").wait_for(state="visible")
    assert "required asset" in page.locator("#error").inner_text()
    page.unroute("**/viewer/app.js")
    print("Actual browser: real totals, native TIFFs, masks/sparse NoData, rejection/limits, cancel, exports, mobile and failure: PASS",flush=True)


def check_lab(page,base):
    page.goto(base+"lab/lab/index.html?path="+NOTEBOOKS[0])
    page.wait_for_function("window.jupyterapp?.started",timeout=120000)
    for name,marker in zip(NOTEBOOKS,("REAL_POPULATION_BROWSER_OK","REAL_COVERAGE_BROWSER_OK","REAL_EXPORT_BROWSER_OK")):
        if name!=NOTEBOOKS[0]:
            page.evaluate("async name=>{await jupyterapp.commands.execute('docmanager:open',{path:name,factory:'Notebook'});}",name)
        page.wait_for_function("name=>jupyterapp.shell.currentWidget?.context?.path===name&&jupyterapp.shell.currentWidget.context.isReady",arg=name,timeout=120000)
        page.wait_for_function("jupyterapp.shell.currentWidget.sessionContext?.session?.kernel?.status==='idle'",timeout=120000)
        page.evaluate("""()=>{window.notebookRunState={done:false};jupyterapp.commands.execute('notebook:run-all-cells').then(result=>window.notebookRunState={done:true,result},error=>window.notebookRunState={done:true,error:String(error)});} """)
        page.wait_for_function("window.notebookRunState.done",timeout=240000)
        assert page.evaluate("window.notebookRunState")=={"done":True,"result":True}
        outputs=page.evaluate("Array.from(jupyterapp.shell.currentWidget.content.model.cells).map(c=>c.toJSON()).filter(c=>c.cell_type==='code').map(c=>({execution_count:c.execution_count,outputs:c.outputs}))")
        assert outputs and all(cell["execution_count"] is not None for cell in outputs)
        assert not any(output.get("output_type")=="error" for cell in outputs for output in cell["outputs"]),outputs
        assert marker in json.dumps(outputs)
        print("Actual Pyodide model outputs: "+name+": PASS",flush=True)
    page.wait_for_function("""async()=>{try{const contents=jupyterapp.serviceManager.contents;const csv=await contents.get('outputs/real-comparison.csv',{content:true,format:'text'}),json=await contents.get('outputs/real-comparison.json',{content:true,format:'text'});window.labExports={csv:csv.content,json:json.content};return true;}catch{return false;}}""",timeout=30000)
    files=page.evaluate("labExports")
    exported=json.loads(files["json"])
    rows=list(csv.DictReader(io.StringIO(files["csv"])))
    oracle=json.loads((ROOT/"data/real/independent_oracle.json").read_text(encoding="utf-8"))
    for row,result in zip(rows,exported["results"]):
        assert abs(result["population"]-oracle["sources"][result["metadata"]["id"]]["aoi_population"])<.0001
        assert float(row["population"])==result["population"]
        assert json.loads(row["metadata_json"])==result["metadata"] and result["metadata"]["synthetic"] is False
    assert exported["bounds"]==[3.3,6.45,3.45,6.6]
    page.screenshot(path=str(ROOT/"test-results/lab-executed.png"),full_page=True)
    print("Actual Pyodide real CSV/JSON source-oracle exports: PASS",flush=True)


def main():
    global SITE
    parser=argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--source-viewer-only",action="store_true",help="Focused source viewer/worker tests; skips build/publication and Lab checks")
    args=parser.parse_args()
    if args.source_viewer_only:
        SITE=ROOT
    else:
        check_publication()
    (ROOT/"test-results").mkdir(exist_ok=True)
    server=None
    if args.base_url:
        base=args.base_url.rstrip("/")+"/"
    else:
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f"http://127.0.0.1:{server.server_port}"+PREFIX
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch()
            page=browser.new_page(viewport={"width":1440,"height":1000})
            if args.source_viewer_only:
                try:
                    check_viewer(page,base)
                finally:
                    browser.close()
                return
            page.goto(base)
            assert page.locator("nav.cards a").count()==3
            assert "01_real_population.ipynb" in page.get_by_role("link",name="Open JupyterLite Lab").get_attribute("href")
            served=page.request.get(base+"publication.json").json()
            for relative,digest in served["calculation_sha256"].items():
                assert hashlib.sha256(page.request.get(base+relative).body()).hexdigest()==digest
            page.goto(base+"book/intro.html")
            assert page.get_by_role("heading",name="Population grids in the browser",exact=True).is_visible()
            try:
                check_viewer(page,base)
                check_lab(page,base)
            except Exception:
                page.screenshot(path=str(ROOT/"test-results/browser-failure.png"),full_page=True)
                print("Browser failure:",page.evaluate("({url:location.href,body:document.body.innerText.slice(-3000),kernel:window.jupyterapp?.shell.currentWidget?.sessionContext?.session?.kernel?.status})"),flush=True)
                raise
            finally:
                browser.close()
    finally:
        if server:
            server.shutdown()


if __name__=="__main__":
    main()
