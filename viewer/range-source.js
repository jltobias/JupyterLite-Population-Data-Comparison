/* Strict bounded sources adapted from the MIT companion raster-clip.js,
 * jltobias/JupyterLite-STAC-Browser @ 945d8b31c59e2cf93f9e51e855eb062fb1b4321c.
 * See vendor/geotiff/LICENSE-companion. No GeoTIFF vendor changes. */
(function(root){
  const MiB=1024*1024;
  const boundedLimit=(value,maximum)=>{if(value===undefined)return maximum;if(!Number.isSafeInteger(value)||value<0)throw Error('Invalid TIFF acquisition budget.');return Math.min(value,maximum);};
  class BoundedSource {
    constructor(onProgress=()=>{},limits={}){this.size=null;this.maxBytes=boundedLimit(limits.bytes,128*MiB);this.maxRequests=boundedLimit(limits.requests,4096);this.stats={requests:0,actual_bytes:0,transport:'',validator:null};this.onProgress=onProgress;this.queue=Promise.resolve();}
    get fileSize(){return this.size;}
    budget(length,requests=1){if(this.stats.actual_bytes+length>this.maxBytes)throw Error('TIFF exceeds its remaining transfer budget (maximum 128 MiB).');if(this.stats.requests+requests>this.maxRequests)throw Error('TIFF exceeds its remaining request budget (maximum 4096 requests).');}
    check(offset,length){if(!Number.isSafeInteger(offset)||!Number.isSafeInteger(length)||offset<0||length<=0||length>16*MiB||!Number.isSafeInteger(offset+length)||(this.size!==null&&offset+length>this.size))throw Error('Invalid or excessive bounded TIFF read (16 MiB/request).');this.budget(length);this.stats.requests++;}
    record(length){this.stats.actual_bytes+=length;if(this.stats.actual_bytes>this.maxBytes)throw Error('TIFF exceeds its remaining transfer budget (maximum 128 MiB).');this.onProgress({...this.stats});}
    fetch(slices,signal){const task=this.queue.then(async()=>{const result=[];for(const {offset,length} of slices){let bounded=Math.min(length,this.metadataSpans?.get(offset)??length);if(this.size!==null)bounded=Math.min(bounded,this.size-offset);if(!Number.isSafeInteger(bounded)||bounded<=0||bounded>64*MiB)throw Error('TIFF fetch slice exceeds the 64 MiB compressed allocation limit.');this.budget(bounded,Math.ceil(bounded/(16*MiB)));if(bounded<=16*MiB){result.push(await this.read(offset,bounded,signal));continue;}const output=new Uint8Array(bounded);for(let at=0;at<bounded;at+=16*MiB)output.set(new Uint8Array(await this.read(offset+at,Math.min(16*MiB,bounded-at),signal)),at);result.push(output.buffer);}return result;});this.queue=task.catch(()=>{});return task;}
  }
  class BlobSource extends BoundedSource {
    constructor(file,onProgress,limits){super(onProgress,limits);if(!(file instanceof Blob)||file.size>2**31)throw Error('Choose a TIFF file of at most 2 GiB.');this.file=file;this.size=file.size;this.stats.transport='local Blob slices';}
    async read(offset,length,signal){this.check(offset,length);if(signal?.aborted)throw Error('TIFF read cancelled.');const result=await this.file.slice(offset,offset+length).arrayBuffer();if(signal?.aborted)throw Error('TIFF read cancelled.');if(result.byteLength!==length)throw Error('Truncated local TIFF slice.');this.record(length);return result;}
  }
  class RangeSource extends BoundedSource {
    constructor(input,{allowSameOrigin=false,onProgress,fetcher=fetch,limits}={}){
      super(onProgress,limits);const url=new URL(input,root.location?.href);
      if(url.username||url.password||url.search||url.hash)throw Error('Use a stable public TIFF URL without credentials, query tokens or fragments.');
      if(url.protocol!=='https:'&&!(allowSameOrigin&&url.origin===root.location?.origin))throw Error('Remote TIFFs require public HTTPS.');
      this.url=url.href;this.fetcher=fetcher;this.stats.transport='verified HTTP 206 ranges';this.identity=null;
    }
    async read(offset,length,signal){
      this.check(offset,length);
      const controller=new AbortController(),abort=()=>controller.abort();signal?.addEventListener('abort',abort,{once:true});
      if(signal?.aborted)controller.abort();
      const timer=setTimeout(()=>controller.abort(),20000);let response,reader;
      try{
        response=await this.fetcher.call(root,this.url,{headers:{Range:`bytes=${offset}-${offset+length-1}`},credentials:'omit',referrerPolicy:'no-referrer',cache:'no-store',signal:controller.signal});
        if(response.url&&new URL(this.url).protocol==='https:'&&new URL(response.url).protocol!=='https:')throw Error('TIFF redirects must retain HTTPS.');
        if(response.status!==206){response.body?.cancel().catch(()=>{});throw Error(`TIFF server must return HTTP 206; received ${response.status}. No full-file fallback is allowed.`);}
        const match=/^bytes (\d+)-(\d+)\/(\d+)$/.exec(response.headers.get('Content-Range')||'');
        const start=Number(match?.[1]),end=Number(match?.[2]),total=Number(match?.[3]);
        const etag=response.headers.get('ETag'),modified=response.headers.get('Last-Modified');
        const identity=etag&&/^"[^"\r\n]*"$/.test(etag)?`ETag: ${etag}`:modified&&Number.isFinite(Date.parse(modified))?`Last-Modified: ${modified}`:null;
        if(!match||start!==offset||end!==offset+length-1||!Number.isSafeInteger(total)||total<=end||!identity)throw Error('TIFF needs exposed exact Content-Range and a strong ETag or Last-Modified validator (CORS).');
        if(this.size!==null&&(this.size!==total||this.identity!==identity))throw Error('TIFF source changed during the read; no mixed-source window is accepted.');
        this.size=total;this.identity=identity;this.stats.validator=identity;this.stats.validator_strength=identity.startsWith('ETag')?'strong ETag':'Last-Modified (weaker, second-level precision)';
        const declared=response.headers.get('Content-Length');
        if(declared!==null&&Number(declared)!==length)throw Error('TIFF range Content-Length mismatch.');
        if(response.headers.get('Content-Encoding')&&!/^identity$/i.test(response.headers.get('Content-Encoding')))throw Error('Encoded HTTP range bodies are unsupported.');
        reader=response.body?.getReader();if(!reader)throw Error('TIFF range has no readable body.');
        const result=new Uint8Array(length);let at=0;
        while(true){const {done,value}=await reader.read();if(done)break;this.record(value.byteLength);if(at+value.byteLength>length)throw Error('TIFF range body exceeded the requested length.');result.set(value,at);at+=value.byteLength;}
        if(at!==length)throw Error('Truncated TIFF range body.');
        return result.buffer;
      }catch(error){if(reader)await reader.cancel().catch(()=>{});else response?.body?.cancel().catch(()=>{});if(controller.signal.aborted)throw Error('TIFF request cancelled or exceeded its 20 second timeout.');throw error;}
      finally{clearTimeout(timer);signal?.removeEventListener('abort',abort);}
    }
  }
  root.PopulationSources={BlobSource,RangeSource};
})(globalThis);
