import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const js=readFileSync(new URL('../viewer/analysis.js',import.meta.url),'utf8');
const a=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const catalog=JSON.parse(readFileSync(new URL('../data/population-catalog.json',import.meta.url),'utf8'));
const expected=[[181,181,46,286702,354016],[181,181,46,202089,354016],[19,19,1,3849,8064],[19,19,2,11561,15680]];
for(const [i,source] of catalog.sources.entries()){
  assert.equal(Object.hasOwn(source.grid,'values'),false);
  const plan=a.planWindow(source,catalog.default_aoi);
  assert.deepEqual([plan.width,plan.height,plan.blocks,plan.compressed_bytes,plan.decoded_bytes],expected[i]);
  const narrow=a.planWindow(source,[3.34,6.49,3.35,6.50]);
  assert.ok(narrow.cells<plan.cells);
  assert.ok(narrow.compressed_bytes<=plan.compressed_bytes);
  assert.throws(()=>a.planWindow(source,[-74.05,40.68,-73.9,40.83]),/outside/);
  const [w,s,e,n]=a.gridBounds(source.grid);
  for(const touch of [[e,s,e+.01,n],[w,s-.01,e,s],[w-.01,s,w,n],[w,n,e,n+.01]])assert.throws(()=>a.planWindow(source,touch),/outside/);
  assert.ok(a.planWindow(source,[e-1e-9,s,e,n]).cells>0); // Retain real tiny overlaps.
}
const strip=catalog.sources[0],wide=a.planWindow(strip,[3.3,6.45,3.45,6.6]),narrow=a.planWindow(strip,[3.34,6.45,3.35,6.6]);
assert.ok(narrow.cells<wide.cells);assert.equal(narrow.compressed_bytes,wide.compressed_bytes);
const huge={grid:{width:1000,height:1000,west:0,north:1,dx:.001,dy:.001},layout:strip.layout};
assert.throws(()=>a.planWindow(huge,[0,0,1,1]),/262144/);
const cache=new a.WindowCache(40,2),value=n=>({grid:{values:Array(n).fill(0)}});
cache.set('asset-a:window',value(3));cache.set('asset-b:window',value(3));
assert.equal(cache.get('asset-a:window'),null);assert.equal(cache.bytes,24);
assert.equal(cache.get('changed-hash:window'),null);
cache.set('asset-b:window',value(1));assert.equal(cache.bytes,8);
cache.set('too-big',value(10));assert.equal(cache.bytes,8);
cache.set('second',value(1));cache.get('asset-b:window');cache.set('third',value(1));assert.equal(cache.get('second'),null);

await import('data:text/javascript;base64,'+Buffer.from(readFileSync(new URL('../viewer/range-source.js',import.meta.url),'utf8')).toString('base64'));
const {RangeSource,BlobSource}=globalThis.PopulationSources;
const options={headers:{'Content-Range':'bytes 0-3/100','Content-Length':'4',ETag:'"v1"'}};
const response=(body=new Uint8Array([1,2,3,4]),headers=options.headers)=>new Response(body,{status:206,headers});
const source=new RangeSource('https://example.test/count.tif',{fetcher:async(url,request)=>{assert.equal(request.headers.Range,'bytes=0-3');assert.equal(request.credentials,'omit');assert.equal(request.headers['If-Match'],undefined);return response();}});
assert.deepEqual([...new Uint8Array(await source.read(0,4))],[1,2,3,4]);assert.equal(source.fileSize,100);assert.equal(source.stats.actual_bytes,4);
let consumed=false,cancelled=false;
const ignored=new RangeSource('https://example.test/count.tif',{fetcher:async()=>({status:200,body:{getReader(){consumed=true;},async cancel(){cancelled=true;}}})});
await assert.rejects(()=>ignored.read(0,4),/206/);assert.equal(consumed,false);assert.equal(cancelled,true);assert.equal(ignored.stats.actual_bytes,0);
for(const headers of [{ETag:'"v1"'}, {...options.headers,'Content-Range':'bytes 1-4/100'}, {...options.headers,ETag:'W/"v1"'}, {...options.headers,'Content-Length':'5'}]){
  const bad=new RangeSource('https://example.test/count.tif',{fetcher:async()=>response(undefined,headers)});await assert.rejects(()=>bad.read(0,4));
}
for(const length of [3,5]){
  const bad=new RangeSource('https://example.test/count.tif',{fetcher:async()=>response(new Uint8Array(length),{...options.headers})});await assert.rejects(()=>bad.read(0,4),/Truncated|exceeded/);
}
let calls=0;
const changed=new RangeSource('https://example.test/count.tif',{fetcher:async()=>response(undefined,{...options.headers,ETag:++calls===1?'"v1"':'"v2"'})});
await changed.read(0,4);await assert.rejects(()=>changed.read(0,4),/changed/);
const changedSize=new RangeSource('https://example.test/count.tif',{fetcher:async()=>response(undefined,{...options.headers,'Content-Range':`bytes 0-3/${++calls===3?100:101}`})});
await changedSize.read(0,4);await assert.rejects(()=>changedSize.read(0,4),/changed/);
const modified=new RangeSource('https://example.test/count.tif',{fetcher:async()=>response(undefined,{'Content-Range':'bytes 0-3/9000000000','Last-Modified':'Fri, 06 Nov 2026 12:00:00 GMT'})});
await modified.read(0,4);assert.equal(modified.fileSize,9000000000);assert.match(modified.stats.validator_strength,/weaker/);
for(const url of ['http://example.test/a.tif','https://user:secret@example.test/a.tif','https://example.test/a.tif?token=secret'])assert.throws(()=>new RangeSource(url));
await assert.rejects(()=>source.read(0,16*1024*1024+1),/excessive/);
source.stats.requests=4096;await assert.rejects(()=>source.read(0,4),/4096/);
const local=new BlobSource(new Blob([new Uint8Array([0,1,2,3])]));const abort=new AbortController();abort.abort();await assert.rejects(()=>local.read(0,1,abort.signal),/cancelled/);
const large=new BlobSource(new Blob([new Uint8Array(18000000)])),chunks=[];
const localRead=large.read.bind(large);large.read=async(offset,length,signal)=>{chunks.push(length);return localRead(offset,length,signal);};
assert.equal((await large.fetch([{offset:0,length:18000000}]))[0].byteLength,18000000);assert.deepEqual(chunks,[16*1024*1024,18000000-16*1024*1024]);
await assert.rejects(()=>large.read(0,18000000),/16 MiB/);
for(const limits of [{bytes:4,requests:1},{bytes:4,requests:4096},{bytes:128*1024*1024,requests:1}]){
 let issued=0;const remaining=new RangeSource('https://example.test/count.tif',{limits,fetcher:async()=>{issued++;return response();}});
 await remaining.read(0,4);await assert.rejects(()=>remaining.read(0,4),/remaining/);assert.equal(issued,1);
}
const clamped=new RangeSource('https://example.test/count.tif',{limits:{bytes:2**40,requests:99999}});assert.equal(clamped.maxBytes,128*1024*1024);assert.equal(clamped.maxRequests,4096);
assert.throws(()=>new RangeSource('https://example.test/count.tif',{limits:{bytes:-1}}),/Invalid/);
let concurrent=0,peak=0;
const serial=new RangeSource('https://example.test/count.tif',{fetcher:async()=>{peak=Math.max(peak,++concurrent);await new Promise(r=>setTimeout(r,5));concurrent--;return response();}});
await Promise.all([serial.fetch([{offset:0,length:4}]),serial.fetch([{offset:0,length:4}])]);assert.equal(peak,1);
const originalTimeout=globalThis.setTimeout;
try{
 globalThis.setTimeout=(callback)=>originalTimeout(callback,5);
 const timed=new RangeSource('https://example.test/count.tif',{fetcher:async(_,request)=>await new Promise((resolve,reject)=>request.signal.addEventListener('abort',()=>reject(Error('abort'))))});
 await assert.rejects(()=>timed.read(0,4),/20 second timeout/);
}finally{globalThis.setTimeout=originalTimeout;}
console.log('BBox catalog/plans, strip costs, bounded cache and strict206 identity/body/timeout/serial scheduling: PASS');
