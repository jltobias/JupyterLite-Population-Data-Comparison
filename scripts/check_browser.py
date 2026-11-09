"""Verify real publication, actual local TIFF worker and all three Pyodide lessons."""
import argparse
import base64
import csv
import hashlib
import io
import json
import re
import struct
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
    def send_head(self):
        fixture = urlsplit(self.path).path.startswith(PREFIX+"__range__/")
        path = Path(self.translate_path(self.path))
        if not fixture and (not self.headers.get("Range") or not path.is_file()):
            return super().send_head()
        mode = path.name if fixture else "normal"
        content = tiff(west=-74.1,north=40.9,dx=.15,dy=.15) if fixture else None
        size = len(content) if fixture else path.stat().st_size
        match = re.fullmatch(r"bytes=(\d+)-(\d+)", self.headers["Range"])
        if not match or not 0 <= int(match[1]) <= int(match[2]) < size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        start, end = map(int, match.groups())
        self.send_response(200 if mode=="ignored.tif" else 206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Range", "malformed" if mode=="malformed.tif" else f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(size if mode=="ignored.tif" else end-start+1))
        self.send_header("Accept-Ranges", "bytes")
        if mode!="no-identity.tif":
            self.send_header("ETag", f'"{size:x}-{self.headers.get("Range") if mode=="changed.tif" else "fixture" if fixture else path.stat().st_mtime_ns}"')
        if mode!="no-cors.tif":
            self.send_header("Access-Control-Allow-Origin", "*")
        if mode!="unexposed.tif":
            self.send_header("Access-Control-Expose-Headers", "Content-Range, ETag, Last-Modified")
        self.end_headers()
        source = io.BytesIO(content) if fixture else path.open("rb")
        source.seek(0 if mode=="ignored.tif" else start)
        self._range_remaining = size if mode=="ignored.tif" else end-start if mode=="truncated.tif" else end-start+1
        if mode=="truncated.tif":
            self.close_connection=True
        return source

    def copyfile(self, source, outputfile):
        remaining = getattr(self, "_range_remaining", None)
        if remaining is None:
            return super().copyfile(source, outputfile)
        while remaining:
            block = source.read(min(65536, remaining))
            if not block:
                break
            outputfile.write(block)
            remaining -= len(block)
        self._range_remaining = None

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
    canonical_catalog=(ROOT / "data/population-catalog.json").read_bytes()
    assert canonical_catalog==(SITE / "data/population-catalog.json").read_bytes()
    assert hashlib.sha256(canonical_catalog).hexdigest()==manifest["population_catalog_sha256"]
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
    page.locator("#compare-loaded").click()


def worker(page, content, bounds=(10, 19.8, 10.2, 20)):
    return page.evaluate("""async({encoded,bounds})=>{
      const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
      return await new Promise(resolve=>{
        const w=new Worker(new URL('raster-worker.js',location.href));
        const timer=setTimeout(()=>{w.terminate();resolve({error:'Worker timeout'});},15000);
        w.onmessage=({data})=>{if(data.progress)return;clearTimeout(timer);w.terminate();resolve(data);};
        w.onerror=e=>{clearTimeout(timer);w.terminate();resolve({error:e.message});};
        w.postMessage({file:new File([bytes],'fixture.tif'),bounds});
      });
    }""", {"encoded":base64.b64encode(content).decode(), "bounds":list(bounds)})


def tiff_entries(content):
    offset=struct.unpack_from('<I',content,4)[0]
    return {struct.unpack_from('<H',content,offset+2+12*i)[0]:offset+2+12*i for i in range(struct.unpack_from('<H',content,offset)[0])}


def check_bbox_workflow(page, base):
    page.goto(base+"viewer/index.html")
    page.wait_for_function("window.populationViewer?.results.length===4")
    snapshot = "JSON.stringify({bounds:populationViewer.bounds,results:populationViewer.results,classification:populationViewer.classification,legends:[...document.querySelectorAll('.legend')].map(l=>l.textContent),images:[...document.querySelectorAll('.native-grid')].map(i=>i.src),views:populationViewer.maps.map(m=>[m.getCenter().lat,m.getCenter().lng,m.getZoom()])})"
    initial = page.evaluate(snapshot)
    initial_cells = page.evaluate("populationViewer.layers.slice(0,4).map(l=>l.grid.values.length)")
    def draft(region):
        for key, value in zip(("west","south","east","north"),region):
            page.locator("#"+key).fill(str(value))
    small = [3.32,6.48,3.40,6.56]
    draft(small)
    assert page.evaluate(snapshot)==initial
    page.locator("#compare").click()
    page.wait_for_function("b=>!populationViewer.loading&&JSON.stringify(populationViewer.bounds)===JSON.stringify(b)",arg=small)
    assert all(a<b for a,b in zip(page.evaluate("populationViewer.layers.slice(0,4).map(l=>l.grid.values.length)"),initial_cells))
    assert page.evaluate("populationViewer.maps.every(m=>{const a=m.latLngToContainerPoint([6.48,3.32]),b=m.latLngToContainerPoint([6.56,3.4]);return Math.abs(a.y-b.y)>150&&m.getBounds().contains([[6.48,3.32],[6.56,3.4]])})")
    assert "selected compressed" in page.locator("#load-plan").inner_text()
    expected = page.evaluate("populationViewer.results.map(r=>[r.population,r.coverage])")
    # The identical snapped windows reuse pixels, while exact-box fractions change.
    shifted=[v+1e-9 for v in small]
    draft(shifted);page.locator("#compare").click()
    page.wait_for_function("!populationViewer.loading")
    assert "4/4 windows reused" in page.locator("#status").inner_text()
    assert page.evaluate("populationViewer.results.map(r=>[r.population,r.coverage])")!=expected
    assert page.evaluate("populationViewer.results.every(r=>r.metadata.acquisition.actual_bytes===0)")
    assert page.evaluate("b=>populationViewer.results.every(r=>JSON.stringify(r.metadata.acquisition.requested_bounds)===JSON.stringify(b)&&r.metadata.acquisition.original_acquisition.actual_bytes>0)",small)
    assert page.evaluate("b=>populationViewer.results.every(r=>JSON.stringify(r.metadata.comparison_context.requested_bounds)===JSON.stringify(b)&&!r.metadata.comparison_context.new_pixels_read)",shifted)
    assert page.evaluate("populationViewer.cache.bytes<=16*1024*1024&&populationViewer.cache.entries<=16")
    # A later source fails after earlier layers stage; nothing visible is replaced.
    retained = page.evaluate(snapshot)
    page.route("**/data/real/landscan-2020.tif",lambda route:route.abort())
    draft([3.34,6.49,3.38,6.54]);page.locator("#compare").click()
    page.wait_for_function("!populationViewer.loading")
    assert page.evaluate(snapshot)==retained
    assert "rejected" in page.locator("#error").inner_text()
    page.unroute("**/data/real/landscan-2020.tif")
    # A same-size decoding-field mutation cannot replace a valid comparison.
    mutated=bytearray((ROOT/'data/real/worldpop-2025.tif').read_bytes())
    struct.pack_into('<H',mutated,tiff_entries(mutated)[339]+8,1)
    def changed_sample(route):
        lo,hi=map(int,re.fullmatch(r'bytes=(\d+)-(\d+)',route.request.headers['range']).groups())
        route.fulfill(status=206,headers={'Content-Range':f'bytes {lo}-{hi}/{len(mutated)}','ETag':'"changed-sample"','Content-Type':'image/tiff'},body=bytes(mutated[lo:hi+1]))
    page.route('**/data/real/worldpop-2025.tif',changed_sample)
    draft([3.356,6.506,3.376,6.526]);page.locator('#compare').click();page.wait_for_function('!populationViewer.loading')
    assert page.evaluate(snapshot)==retained and 'pinned catalog' in page.locator('#error').inner_text()
    page.unroute('**/data/real/worldpop-2025.tif')
    # Simulate exhaustion in the preceding worker; the next worker issues no range.
    next_requests=[]
    observer=lambda request:next_requests.append(request.url) if request.url.endswith('/grid3-2025.tif') else None
    page.on('request',observer)
    page.evaluate("""()=>{window.nativeBudgetWorker=Worker;window.Worker=class extends nativeBudgetWorker{set onmessage(handler){super.onmessage=event=>{if(event.data.progress)event.data.progress.actual_bytes=128*1024*1024;handler(event);};}};}""")
    draft([3.357,6.507,3.377,6.527]);page.locator('#compare').click();page.wait_for_function('!populationViewer.loading')
    page.evaluate('()=>{window.Worker=window.nativeBudgetWorker;}')
    page.remove_listener('request',observer)
    assert not next_requests and page.evaluate(snapshot)==retained
    assert 'remaining transfer budget' in page.locator('#error').inner_text()
    # Cancel and edits terminate workers synchronously before any commit.
    draft([3.345,6.495,3.385,6.545])
    page.evaluate("document.getElementById('compare').click();document.getElementById('load-cancel').click()")
    assert page.evaluate(snapshot)==retained
    page.evaluate("document.getElementById('compare').click();const e=document.getElementById('west');e.value='3.346';e.dispatchEvent(new Event('input',{bubbles:true}))")
    page.wait_for_timeout(200)
    assert page.evaluate(snapshot)==retained and not page.evaluate("populationViewer.loading")
    # The first-map action edits the draft only.
    page.locator("#use-map").click()
    assert page.evaluate(snapshot)==retained
    assert page.evaluate("JSON.stringify(populationViewer.draftBounds)===JSON.stringify((()=>{const b=populationViewer.maps[0].getBounds();return [b.getWest(),b.getSouth(),b.getEast(),b.getNorth()]})())")
    # A genuine local fixture server exercises rejected HTTP bodies and identity.
    fixture_server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    threading.Thread(target=fixture_server.serve_forever,daemon=True).start()
    fixture_base=f"http://127.0.0.1:{fixture_server.server_port}"+PREFIX+"__range__/"
    try:
        # Forward the test HTTPS endpoint to genuine exact-range server responses.
        # No test bypass is present in the application's HTTPS policy.
        remote="https://range-fixture.example.test/count.tif"
        ranges=[]
        def fulfill_range(route):
            header=route.request.headers.get("range")
            response=page.request.get(fixture_base+"normal.tif",headers={"Range":header})
            ranges.append(header)
            route.fulfill(status=response.status,headers=response.headers,body=response.body())
        page.route(remote,fulfill_range)
        nyc=[-74.05,40.68,-73.90,40.83]
        for key,value in zip(('west','south','east','north'),nyc):
            page.locator('#'+key).fill('');page.locator('#'+key).press_sequentially(str(value))
            assert float(page.locator('#'+key).input_value())==value
        assert page.evaluate('populationViewer.draftBounds')==nyc
        assert page.locator("#compare").is_disabled() and "outside" in page.locator("#load-plan").inner_text()
        page.locator("#raster-source").select_option("remote")
        page.locator("#raster-use-area").click()
        assert [float(page.locator('#'+key).input_value()) for key in ('rw','rs','re','rn')]==nyc
        page.locator("#raster-url").fill(remote)
        metadata=json.loads(page.locator("#raster-metadata").input_value())
        metadata.update(id="remote-synthetic-nyc",title="Explicit synthetic HTTPS transport fixture",synthetic=True,source_asset=remote)
        page.locator("#raster-metadata").fill(json.dumps(metadata));page.locator("#raster-declaration").check()
        page.locator("#raster-plan").click();page.locator("#raster-submit").wait_for(state="visible")
        page.wait_for_function("!document.getElementById('raster-submit').disabled")
        assert page.evaluate(snapshot)==retained
        assert "Headers only" in page.locator("#raster-status").inner_text()
        fixture=tiff(west=-74.1,north=40.9,dx=.15,dy=.15)
        entries=tiff_entries(fixture)
        pixel_start=struct.unpack_from('<I',fixture,entries[273]+8)[0]
        pixel_end=pixel_start+struct.unpack_from('<I',fixture,entries[279]+8)[0]
        assert ranges
        assert all((lambda a,b:b<pixel_start or a>=pixel_end)(*map(int,re.fullmatch(r'bytes=(\d+)-(\d+)',header).groups())) for header in ranges),ranges
        page.locator("#raster-submit").click()
        page.wait_for_function("populationViewer.layers.length===5")
        assert page.evaluate("populationViewer.bounds")==nyc
        imported=page.evaluate("populationViewer.layers.at(-1)")
        assert imported["grid"]["values"]==[0,None,10,20]
        assert imported["metadata"]["acquisition"]["actual_bytes"]>0
        assert "validation" not in imported["metadata"] and "processing_receipt" not in imported["metadata"]
        assert imported["metadata"]["file_declarations"]["url"]==remote
        assert any(int(re.fullmatch(r'bytes=(\d+)-(\d+)',header)[1])==pixel_start for header in ranges)
        assert 'LOCAL FILE' not in page.locator('#results').inner_text()
        assert 'verified HTTP 206 ranges' in page.locator('#results').inner_text()
        assert 'LOCAL FILE' not in download_text(page,'#svg')
        page.unroute(remote)
        # Worker failures use real HTTP206 error fixtures, with the same UI retained.
        committed=page.evaluate(snapshot)
        for mode in ('ignored','malformed','truncated','changed','no-cors','unexposed','no-identity'):
            bad_remote=f"https://range-fixture.example.test/{mode}.tif"
            def fulfill_bad(route,mode=mode):
                try:
                    response=page.request.get(fixture_base+mode+'.tif',headers={"Range":route.request.headers['range']})
                    route.fulfill(status=response.status,headers=response.headers,body=response.body())
                except Exception:
                    route.abort()
            page.route(bad_remote,fulfill_bad)
            page.locator('#raster-url').fill(bad_remote)
            metadata['id']=mode;page.locator('#raster-metadata').fill(json.dumps(metadata))
            page.locator('#raster-plan').click()
            page.wait_for_function("document.getElementById('raster-status').textContent==='Import rejected.'")
            assert page.evaluate(snapshot)==committed
            page.unroute(bad_remote)
    finally:
        fixture_server.shutdown()
    print("BBox planning, reduced acquisition, exact-box cache, staged failure/cancel/stale, map bounds and HTTPS import: PASS",flush=True)


def check_first_imports_and_deadlines(page,base):
    for scenario in ('failure','cancel'):
        held=[]
        page.route('**/data/real/worldpop-2025.tif',lambda route:route.abort() if scenario=='failure' else held.append(route))
        page.goto(base+'viewer/index.html')
        page.wait_for_function('!!window.populationViewer')
        if scenario=='cancel':
            page.locator('#load-cancel').click()
            for route in held:
                try:route.abort()
                except Exception:pass
        page.wait_for_function('!populationViewer.loading')
        page.unroute('**/data/real/worldpop-2025.tif')
        assert page.evaluate('populationViewer.layers.length')==0 and page.evaluate('populationViewer.bounds') is None
        if scenario=='failure':
            document=json.loads((ROOT/'data/import-example.geojson').read_text(encoding='utf-8'))
            document['metadata']['id']='worldpop-2025'
            page.locator('#import').set_input_files({'name':'reserved.geojson','mimeType':'application/json','buffer':json.dumps(document).encode()})
            page.wait_for_function("document.getElementById('error').textContent.includes('reserved')")
            assert page.evaluate('populationViewer.layers.length')==0
            document['metadata']['id']='first-vector'
            page.locator('#import').set_input_files({'name':'first.geojson','mimeType':'application/json','buffer':json.dumps(document).encode()})
            page.wait_for_function('populationViewer.layers.length===1')
            assert len(page.evaluate('populationViewer.bounds'))==4 and len(page.evaluate('populationViewer.results'))==1
            retained=page.evaluate('populationViewer.bounds')
            document['metadata']['id']='second-vector'
            for feature in document['features']:
                for coordinate in feature['geometry']['coordinates'][0]:coordinate[1]+=1
            page.locator('#import').set_input_files({'name':'second.geojson','mimeType':'application/json','buffer':json.dumps(document).encode()})
            page.wait_for_function('populationViewer.layers.length===2')
            assert page.evaluate('populationViewer.bounds')==retained
        else:
            # An inactive malformed URL must never participate in local form validity.
            page.locator('#raster-source').select_option('remote');page.locator('#raster-url').fill('invalid url')
            page.locator('#raster-source').select_option('local')
            assert page.locator('#raster-url').is_disabled()
            assert page.locator('#raster-file').get_attribute('required') is not None
            page.locator('#raster-file').set_input_files({'name':'initial.tif','mimeType':'image/tiff','buffer':tiff()})
            for key,value in zip(('rw','rs','re','rn'),(10,19.8,10.2,20)):page.locator('#'+key).fill(str(value))
            metadata=json.loads(page.locator('#raster-metadata').input_value());metadata['id']='worldpop-2025'
            page.locator('#raster-metadata').fill(json.dumps(metadata));page.locator('#raster-declaration').check();page.locator('#raster-plan').click()
            assert 'reserved' in page.locator('#error').inner_text() and page.evaluate('populationViewer.layers.length')==0
            metadata['id']='initial-tiff';page.locator('#raster-metadata').fill(json.dumps(metadata));page.locator('#rw').fill('');page.locator('#raster-plan').click()
            assert 'four finite coordinates' in page.locator('#error').inner_text() and page.evaluate('populationViewer.layers.length')==0
            page.locator('#rw').press_sequentially('10')
            # Control only main-thread phase timers, leaving worker transport intact.
            page.evaluate("""()=>{window.phaseTimers=new Map();window.timerSerial=1000000000;window.realSetTimeout=setTimeout;window.realClearTimeout=clearTimeout;window.realImportWorker=Worker;
              window.setTimeout=(callback,delay,...args)=>{if(delay!==120000)return realSetTimeout(callback,delay,...args);const id=++timerSerial;phaseTimers.set(id,callback);return id;};
              window.clearTimeout=id=>{if(!phaseTimers.delete(id))realClearTimeout(id);};
              window.Worker=class extends realImportWorker{postMessage(data,...args){if(data.action==='read'){window.releasePlannedRead=()=>super.postMessage(data,...args);return;}return super.postMessage(data,...args);}};}""")
            page.locator('#raster-plan').click();page.wait_for_function("!document.getElementById('raster-submit').disabled")
            assert page.evaluate('phaseTimers.size')==0
            page.evaluate('[...phaseTimers.values()].forEach(callback=>callback())') # Simulated idle review elapsed.
            assert page.locator('#raster-submit').is_enabled()
            page.locator('#raster-submit').click()
            assert page.evaluate('phaseTimers.size')==1 and page.evaluate('populationViewer.layers.length')==0
            page.evaluate('releasePlannedRead()');page.wait_for_function('populationViewer.layers.length===1')
            assert page.evaluate('phaseTimers.size')==0 and page.evaluate('populationViewer.bounds')==[10,19.8,10.2,20]
            assert '2 x 2' in page.locator('#raster-status').inner_text()
            page.evaluate('()=>{window.setTimeout=realSetTimeout;window.clearTimeout=realClearTimeout;window.Worker=realImportWorker;}')
        imported_count=page.evaluate('populationViewer.layers.length')
        page.locator('#example').click();page.locator('#compare').click();page.wait_for_function('!populationViewer.loading')
        assert page.evaluate('populationViewer.layers.length')==4+imported_count
        ids=page.evaluate('populationViewer.layers.map(l=>l.metadata.id)')
        assert len(ids)==len(set(ids)) and len(page.evaluate('populationViewer.results'))==4
    print('First imports after startup failure/cancel, reserved IDs, raw coordinates, source validity and independent phase deadlines: PASS',flush=True)


def check_viewer(page, base):
    errors = []
    requests = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: requests.append(request.url))
    page.goto(base+"viewer/index.html")
    page.wait_for_function("window.populationViewer?.results.length===4")
    oracle = json.loads((ROOT / "data/real/independent_oracle.json").read_text(encoding="utf-8"))
    original = page.evaluate("populationViewer.results")
    assert not any(urlsplit(url).path.endswith("/data/population.json") for url in requests)
    assert all(result["grid"]["width"] < 200 for result in original)
    assert all(result["metadata"]["acquisition"]["transport"] == "verified HTTP 206 ranges" for result in original)
    assert all(result["metadata"]["acquisition"]["full_file_sha256_verified"] is False for result in original)
    for result in original:
        receipt=result["metadata"]["acquisition"]
        assert receipt["requested_bounds"]==[3.3,6.45,3.45,6.6]
        assert receipt["source_url"].endswith('/data/real/'+result["metadata"]["id"]+'.tif')
        assert receipt["completed_at"]>=receipt["started_at"]
        assert len(receipt["native_extent"])==4 and receipt["source_grid"]["width"]>result["grid"]["width"]
    for result in original:
        expected = oracle["sources"][result["metadata"]["id"]]
        assert result["metadata"]["synthetic"] is False
        assert abs(result["population"]-expected["aoi_population"])<.0001
        assert abs(result["coverage"]-min(1,expected["aoi_coverage"]))<1e-10
        assert result["intersected_cells"]==expected["aoi_intersected_cells"]
    assert page.locator(".native-grid").count()==4
    # One shared classifier drives discrete legends, images and export metadata.
    shared=page.evaluate("populationViewer.classification")
    assert len(shared["thresholds"])==4 and shared["bounds"]==[3.3,6.45,3.45,6.6]
    assert shared["colors"]==['#ffffd4','#fed98e','#fe9929','#d95f0e','#993404']
    assert all(result["metadata"]["display_classification"]==shared for result in original)
    legends=page.locator('.legend').all_text_contents()
    assert len(set(legends))==1 and 'Shared modified quantiles' in legends[0]
    colors=page.locator('#legend-0 .legend-swatch').evaluate_all('(nodes)=>nodes.map(n=>getComputedStyle(n).backgroundColor)')
    assert colors==['rgb(255, 255, 212)','rgb(254, 217, 142)','rgb(254, 153, 41)','rgb(217, 95, 14)','rgb(153, 52, 4)','rgb(238, 238, 238)']
    original_images=page.locator('.native-grid').evaluate_all('(nodes)=>nodes.map(n=>n.src)')
    page.locator('#layer-0').select_option('grid3-2025')
    changed=page.evaluate('populationViewer.classification')
    assert changed['layer_ids']==['grid3-2025','landscan-2020','ghspop-2025']
    assert changed['thresholds']!=shared['thresholds']
    assert len(set(page.locator('.legend').all_text_contents()))==1
    changed_images=page.locator('.native-grid').evaluate_all('(nodes)=>nodes.map(n=>n.src)')
    assert any(a!=b for a,b in zip(original_images[1:],changed_images[1:]))
    # Moving the duplicate panel leaves the same distinct source set and breaks.
    page.locator('#layer-0').select_option('landscan-2020')
    assert page.evaluate('populationViewer.classification.thresholds')==changed['thresholds']
    page.locator('#layer-0').select_option('worldpop-2025')
    assert page.evaluate('populationViewer.classification.thresholds')==shared['thresholds']
    assert page.locator('.native-grid').evaluate_all('(nodes)=>nodes.map(n=>n.src)')==original_images
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
    assert page.locator("#compare").is_disabled()
    assert page.locator("#error").is_visible() and page.evaluate("populationViewer.bounds")==before
    page.locator("#example").click()
    page.locator("#draw").click()
    page.locator("#map-0").click(position={"x":160,"y":100})
    page.locator("#map-0").click(position={"x":300,"y":180})
    assert page.evaluate("populationViewer.draftBounds")!=before
    assert page.evaluate("populationViewer.bounds")==before
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
        page.locator("#raster-plan").click()
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
    page.evaluate("document.getElementById('raster-plan').click();document.getElementById('raster-cancel').click()")
    assert "cancelled" in page.locator("#raster-status").inner_text()
    assert page.evaluate("populationViewer.layers.length")==8
    # Literal TIFF masks/NoData, validation, metadata and decompression limits.
    supported=worker(page,tiff())
    assert supported.get("grid",{}).get("values")==[0,None,10,20],supported
    # One supported native strip exceeds a transport request but fits block budgets.
    large=bytearray(tiff(width=1500,height=3000,dx=.001,dy=.001,values=(0,0,0,0)))
    entries=tiff_entries(large);pixel_start=struct.unpack_from('<I',large,entries[273]+8)[0]
    struct.pack_into('<I',large,entries[279]+8,18000000)
    large=large[:pixel_start]+bytearray(18000000)
    large_result=worker(page,large,(10,19.998,10.002,20))
    assert large_result.get('grid',{}).get('values') and all(value==0 for value in large_result['grid']['values']),large_result.get('error')
    assert large_result['plan']['compressed_bytes']==18000000
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
    for touch in ((10.2,19.8,10.3,20),(10,19.7,10.2,19.8),(9.9,19.8,10,20),(10,20,10.2,20.1)):
        assert "outside" in worker(page,tiff(),touch).get("error","")
    state=page.evaluate("({layers:populationViewer.layers.length,bounds:populationViewer.bounds,results:populationViewer.results})")
    page.locator("#raster-file").set_input_files({"name":"negative.tif","mimeType":"image/tiff","buffer":cases["negative"]})
    for key,value in zip(("rw","rs","re","rn"),(10,19.8,10.2,20)):
        page.locator("#"+key).fill(str(value))
    page.locator("#raster-plan").click()
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
    page.locator("#raster-plan").click()
    page.locator("#raster-submit").click()
    page.wait_for_function("populationViewer.layers.length===10")
    pixels=page.evaluate("""async()=>{const img=document.querySelector('#map-0 .native-grid');await img.decode();const c=document.createElement('canvas');c.width=img.naturalWidth;c.height=img.naturalHeight;const x=c.getContext('2d');x.drawImage(img,0,0);return {width:c.width,height:c.height,rgba:Array.from(x.getImageData(0,0,c.width,c.height).data)};}""")
    assert (pixels["width"],pixels["height"])==(3,2),pixels
    expected=[238,238,238,255,255,255,212,255,0,0,0,0,254,153,41,255,217,95,14,255,254,217,142,255]
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
    page.locator("#raster-plan").click()
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
    page.route("**/data/population-catalog.json",lambda route:route.abort())
    page.reload()
    page.locator("#error").wait_for(state="visible")
    assert "Unable to start" in page.locator("#error").inner_text()
    assert page.evaluate("!window.populationViewer")
    page.unroute("**/data/population-catalog.json")
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
                    check_bbox_workflow(page,base)
                    check_first_imports_and_deadlines(page,base)
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
                check_bbox_workflow(page,base)
                check_first_imports_and_deadlines(page,base)
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
