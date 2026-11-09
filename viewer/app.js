import {METHOD,validateBounds,validateLayer,importGeoJSON,compare,exportCSV,layerBounds,area,inspectCell,planWindow,WindowCache,cellDensity,classifyDensity,densityColor,DENSITY_COLORS,ZERO_DENSITY_COLOR} from './analysis.js';
const $=id=>document.getElementById(id), fmt=value=>value===null?'No coverage':value.toLocaleString(undefined,{maximumFractionDigits:2});
const ll=b=>[[b[1],b[0]],[b[3],b[2]]];
function inputBounds(ids){return validateBounds(ids.map(id=>{const input=$(id);if(!input.value.trim()||input.validity.badInput||!Number.isFinite(input.valueAsNumber))throw Error('Enter all four finite coordinates.');return input.valueAsNumber;}));}
function idTaken(id){return demo.sources.some(source=>source.metadata.id===id)||layers.some(layer=>layer.metadata.id===id);}
let layers=[], maps=[], grids=[], rectangles=[], draftRectangles=[], results=[], bounds, draftBounds, classification, demo, overview, overviewFrame, overviewAOI, moving=false, drawing=false, firstCorner=null,job=null,cancelImport=()=>{},comparisonUse='load';
const cache=new WindowCache(),bytes=n=>`${(n/1024).toLocaleString(undefined,{maximumFractionDigits:1})} KiB`;
let acquiredIds=new Set();
let editGeneration=0;
const bundledLayers=new WeakSet(),rasterImages=new WeakMap();
function removeBundleClaims(metadata){
  for(const key of Object.keys(metadata))if(['prepared_extent','processing_receipt','validation','acquisition','comparison_context'].includes(key)||/verified/i.test(key))delete metadata[key];
  return metadata;
}
const fail=message=>{ $('error').textContent=message; $('error').hidden=false; };
const clearError=()=>{ if(!window.populationAssetError)$('error').hidden=true; };
function panelLayers(){return maps.map((_,i)=>layers.find(l=>l.metadata.id===$(`layer-${i}`).value)).filter(Boolean);}
function selectedLayers(){return [...new Set(panelLayers())];}
function extent(layersToFit){return layersToFit.map(layerBounds).reduce((a,b)=>[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[2],b[2]),Math.max(a[3],b[3])],[Infinity,Infinity,-Infinity,-Infinity]);}
function textNode(tag,text){const node=document.createElement(tag);node.textContent=text;return node;}
function prepareDisplay(selected,region){
  const next=classifyDensity(selected,region);
  for(const layer of new Set(selected)){
    if(layer.grid)gridImage(layer,next);
    else for(const cell of layer.cells)cellDensity(cell.population,cell.bounds);
  }
  return next;
}
function renderLegend(index){
  const legend=$(`legend-${index}`),breaks=classification.thresholds;
  legend.replaceChildren(textNode('strong','Shared modified quantiles · people/km²'));
  const entries=document.createElement('div');entries.className='legend-classes';
  const rounded=value=>value.toLocaleString(undefined,{maximumSignificantDigits:8});
  const format=value=>breaks.some(other=>other!==value&&rounded(other)===rounded(value))?String(value):rounded(value);
  DENSITY_COLORS.forEach((color,i)=>{
    let label;
    if(!breaks.length)label=i===0?'Positive cells outside study bounds':'No positive study data';
    else if(i===0)label=`> 0 – ≤ ${format(breaks[0])}`;
    else if(i===4)label=`> ${format(breaks[3])}`;
    else label=breaks[i]===breaks[i-1]?'Empty (tied break)':`> ${format(breaks[i-1])} – ≤ ${format(breaks[i])}`;
    const entry=textNode('span',label),swatch=document.createElement('span');entry.className='legend-class';swatch.className='legend-swatch';swatch.style.backgroundColor=color;swatch.setAttribute('aria-hidden','true');entry.prepend(swatch);entries.append(entry);
  });
  const zero=textNode('span','0 (valid count)'),swatch=document.createElement('span');zero.className='legend-class';swatch.className='legend-swatch legend-zero';swatch.style.backgroundColor=ZERO_DENSITY_COLOR;swatch.setAttribute('aria-hidden','true');zero.prepend(swatch);entries.append(zero);
  legend.append(entries,textNode('span',breaks.length?'Area-weighted across selected sources in study bounds; ties stay together. Unshaded: NoData / outside grid.':'No positive density in study bounds; positive cells outside use the lightest color. Unshaded: NoData / outside grid.'));
}
function inspect(index,lon,lat){
  const layer=layers.find(l=>l.metadata.id===$(`layer-${index}`).value);if(!layer)return;const cell=inspectCell(layer,lon,lat);
  $('inspection').textContent=cell?`${layer.metadata.title} · ${layer.metadata.year} · ${layer.metadata.population_concept}\nNative cell: ${cell.bounds.join(', ')} (west, south, east, north)${cell.row===undefined?'':` · row ${cell.row}, column ${cell.column}`}\nCount: ${cell.population===null?'NoData (not zero)':fmt(cell.population)+' people/cell'}\n${cell.population===null?layer.metadata.nodata_semantics:`Density for display: ${fmt(cell.population/(area(cell.bounds)*6371.0088**2))} people/km²`}\nSource: ${layer.metadata.source}\n${layer.metadata.citation} · License: ${layer.metadata.license}`:`${layer.metadata.title}: outside the loaded native window. Choose bounds and acquire another compatible window.`;
}
function gridImage(layer,display){
  const key=JSON.stringify(display.thresholds),cached=rasterImages.get(layer);
  if(cached?.key===key)return cached.url;
  if(layer.grid){
    if(layer.grid.width>32767||layer.grid.height>32767)throw Error('Native display axes are limited to 32767 pixels. Choose a smaller native window; no resampling is performed.');
    const g=layer.grid,canvas=document.createElement('canvas');canvas.width=g.width;canvas.height=g.height;
    const ctx=canvas.getContext('2d'),image=ctx.createImageData(g.width,g.height);
    for(let y=0;y<g.height;y++){
      for(let x=0;x<g.width;x++){
        const value=g.values[y*g.width+x];if(value===null)continue;
        const color=densityColor(cellDensity(value,[g.west+x*g.dx,g.north-(y+1)*g.dy,g.west+(x+1)*g.dx,g.north-y*g.dy]),display),offset=(y*g.width+x)*4;
        image.data[offset]=parseInt(color.slice(1,3),16);image.data[offset+1]=parseInt(color.slice(3,5),16);image.data[offset+2]=parseInt(color.slice(5,7),16);image.data[offset+3]=255;
      }
    }
    ctx.putImageData(image,0,0);
    const url=canvas.toDataURL('image/png');if(!url.startsWith('data:image/png'))throw Error('The native grid cannot be serialized for display. Choose a smaller window.');
    rasterImages.set(layer,{key,url});return url;
  }
}
function renderLayer(index){
  const layer=layers.find(l=>l.metadata.id===$(`layer-${index}`).value),url=gridImage(layer,classification);
  if(grids[index])grids[index].remove();
  if(layer.grid){
    grids[index]=L.imageOverlay(url,ll(layerBounds(layer)),{interactive:false,className:'native-grid',alt:`${layer.metadata.title}, native count grid shown as people per square kilometre`}).addTo(maps[index]);
  }else{
    grids[index]=L.layerGroup(layer.cells.map(cell=>L.rectangle(ll(cell.bounds),{stroke:false,fillColor:densityColor(cellDensity(cell.population,cell.bounds),classification),fillOpacity:1,interactive:false}))).addTo(maps[index]);
  }
  $(`layer-${index}`).dataset.committed=layer.metadata.id;
  renderLegend(index);
  const metadata=$(`metadata-${index}`);metadata.replaceChildren();
  for (const [key,value] of Object.entries(layer.metadata)){metadata.append(textNode('dt',key.replaceAll('_',' ')),textNode('dd',value!==null&&typeof value==='object'?JSON.stringify(value):String(value)));}
  if(rectangles[index]) rectangles[index].bringToFront();
}
function updateOverview(){if(overviewFrame){overviewFrame.setBounds(maps[0].getBounds());const frame=maps[0].getBounds();overview.fitBounds(L.latLngBounds(ll(layers.length?extent(selectedLayers()):demo.bounds)).extend(frame),{padding:[6,6],animate:false});}}
function updateBounds(next,display){
  const valid=validateBounds(next); // Validate completely before changing the active analysis.
  const prepared=display||prepareDisplay(panelLayers(),valid);
  bounds=valid;classification=prepared;maps.forEach((_,i)=>renderLayer(i));
  maps.forEach((map,i)=>{if(rectangles[i])rectangles[i].setBounds(ll(valid));else rectangles[i]=L.rectangle(ll(valid),{color:'#176bc0',weight:2.5,fill:false,interactive:false}).addTo(map);});
  if(overviewAOI)overviewAOI.setBounds(ll(valid));
  else overviewAOI=L.rectangle(ll(valid),{color:'#176bc0',weight:2,fill:false,interactive:false}).addTo(overview);
  clearError();renderResults();
}
function cancelLoad(message='Load cancelled. Previous valid comparison retained.'){
  editGeneration++;
  if(!job)return;
  const previous=job;job=null;clearTimeout(previous.timer);previous.workers.forEach(worker=>worker.terminate());previous.reject?.(Error(message));$('load-cancel').disabled=true;$('status').textContent=message;
}
function planText(plan){return `${plan.width} × ${plan.height} = ${plan.cells.toLocaleString()} cells; output counts ${bytes(plan.output_bytes)}; ${plan.blocks} ${plan.layout}; selected compressed ${bytes(plan.compressed_bytes)}, decoded blocks ${bytes(plan.decoded_bytes)}`;}
function showPlan(){
  const list=$('load-plan');list.replaceChildren();let valid=!!draftBounds;
  if(draftBounds)for(const source of demo.sources){
    try{const plan=planWindow(source,draftBounds);list.append(textNode('li',`${source.metadata.title}: ${planText(plan)}${plan.partial_coverage?'; outside-source area has no coverage':''}.`));}
    catch(error){valid=false;list.append(textNode('li',`${source.metadata.title}: ${error.message}`));}
  }
  $('compare').disabled=!valid;
  $('compare-loaded').disabled=!draftBounds||!layers.length;
}
function updateDraft(next,writeFields=true){
  cancelLoad('Study bounds changed. Previous valid comparison retained.');cancelImport('Study bounds changed; plan the TIFF again.');
  draftBounds=validateBounds(next);
  if(writeFields)['west','south','east','north'].forEach((id,i)=>$(id).value=draftBounds[i]);
  maps.forEach((map,i)=>{if(draftRectangles[i])draftRectangles[i].setBounds(ll(draftBounds));else draftRectangles[i]=L.rectangle(ll(draftBounds),{color:'#b26716',dashArray:'6 4',weight:2,fill:false,interactive:false}).addTo(map);});
  showPlan();clearError();
}
async function loadComparison(){
  cancelLoad();cancelImport('Comparison load started; plan the TIFF again.');
  const region=validateBounds(draftBounds),plans=demo.sources.map(source=>planWindow(source,region)),current={workers:new Set(),progress:new Map()};job=current;
  current.timer=setTimeout(()=>cancelLoad('Comparison exceeded its 120 second timeout. Previous valid comparison retained.'),120000);$('load-cancel').disabled=false;
  try{
    const staged=[];
    for(const [index,source] of demo.sources.entries()){
      if(job!==current)throw Error('Stale comparison discarded.');
      const key=`${source.asset_sha256}:${plans[index].native_window.join(',')}`;
      let data=cache.get(key);
      if(data)data={...data,acquisition:{...data.acquisition,cache_reused:true,actual_bytes:0,requests:0,original_acquisition:data.acquisition}};
      else{
        data=await new Promise((resolve,reject)=>{
          current.reject=reject;const worker=new Worker('raster-worker.js');current.workers.add(worker);
          worker.onmessage=({data})=>{
            if(job!==current)return;
            if(data.progress){current.progress.set(index,data.progress);const total=[...current.progress.values()].reduce((sum,p)=>sum+p.actual_bytes,0),requests=[...current.progress.values()].reduce((sum,p)=>sum+p.requests,0);$('status').textContent=`Loading ${source.metadata.title} (${index+1}/4). Actual transfer ${bytes(total)} in ${requests} ranges. Previous results remain active.`;if(total>128*1024*1024||requests>4096)cancelLoad('Comparison exceeds the bounded transfer/request budget.');return;}
            current.workers.delete(worker);worker.terminate();data.error?reject(Error(data.error)):resolve(data);
          };
          worker.onerror=event=>reject(Error(event.message));
          const used=[...current.progress.values()];
          worker.postMessage({url:new URL('../data/'+source.asset,location.href).href,bounds:region,expected:source,limits:{bytes:128*1024*1024-used.reduce((sum,p)=>sum+p.actual_bytes,0),requests:4096-used.reduce((sum,p)=>sum+p.requests,0)}});
        });
        if(job!==current)throw Error('Stale comparison discarded.');
        cache.set(key,data);
      }
      const layer=validateLayer({metadata:{...structuredClone(source.metadata),acquisition:data.acquisition},grid:data.grid});staged.push(layer);
    }
    if(job!==current)throw Error('Stale comparison discarded.');
    const display=prepareDisplay(staged,region);compare(staged,region); // All values, images and totals pass before one visible commit.
    layers=[...staged,...layers.filter(layer=>!bundledLayers.has(layer))];staged.forEach(layer=>bundledLayers.add(layer));
    addOptions();maps.forEach((_,i)=>{$(`layer-${i}`).value=staged[i].metadata.id;});comparisonUse='load';acquiredIds=new Set(staged.filter(l=>!l.metadata.acquisition.cache_reused).map(l=>l.metadata.id));updateBounds(region,display);maps.forEach(map=>map.fitBounds(ll(region),{animate:false}));updateOverview();
    const transfer=[...current.progress.values()].reduce((sum,p)=>sum+p.actual_bytes,0);
    $('status').textContent=`Loaded four native windows. Actual transfer ${bytes(transfer)}; ${staged.filter(l=>l.metadata.acquisition.cache_reused).length}/4 windows reused from bounded session cache. Active results use the exact study box.`;
  }catch(error){if(job===current){fail('Comparison load rejected: '+error.message+' Previous valid comparison retained.');$('status').textContent='Comparison not replaced.';}}
  finally{if(job===current){job=null;clearTimeout(current.timer);current.workers.forEach(worker=>worker.terminate());$('load-cancel').disabled=true;}}
}
function renderResults(){
  results=compare(selectedLayers(),bounds);
  for(const result of results){result.metadata.display_classification=structuredClone(classification);result.metadata.comparison_context={requested_bounds:bounds.slice(),use:comparisonUse,cache_reused:!!result.metadata.acquisition?.cache_reused,new_pixels_read:acquiredIds.has(result.metadata.id),actual_bytes_for_this_comparison:acquiredIds.has(result.metadata.id)?result.metadata.acquisition?.actual_bytes||0:0};}
  for(const id of ['csv','json','svg','reset','compare-loaded'])$(id).disabled=!layers.length;
  document.querySelectorAll('.panel-head select,.panel-head button').forEach(el=>el.disabled=!layers.length);
  $('area-description').textContent=`Active bounds: ${bounds.join(', ')} (W, S, E, N). Method: ${METHOD}.`;
  const body=$('results'),chart=$('chart');body.replaceChildren();chart.replaceChildren();
  const max=Math.max(...results.map(r=>r.population||0),1);
  results.forEach(result=>{
    const row=document.createElement('tr'),label=textNode('td',`${result.metadata.title} / ${result.metadata.year}`);
    label.append(textNode('small',`${result.metadata.synthetic?'SYNTHETIC fixture':result.metadata.file_declarations?'IMPORTED · user-declared provenance':'PROVIDER COUNTS'} · ${result.metadata.acquisition?.transport||'local cells'} · ${result.metadata.reference_date||result.metadata.year} · ${result.metadata.population_concept}`));
    row.append(label,textNode('td',fmt(result.population)),textNode('td',`${(result.coverage*100).toFixed(1)}%`),textNode('td',result.intersected_cells));body.append(row);
    const barRow=document.createElement('div');barRow.className='bar-row';
    const barLabel=document.createElement('div');barLabel.className='bar-label';barLabel.append(textNode('span',result.metadata.title),textNode('strong',fmt(result.population)));
    const track=document.createElement('div');track.className='bar-track';const bar=document.createElement('div');bar.className='bar';bar.style.width=`${(result.population||0)/max*100}%`;track.append(bar);barRow.append(barLabel,track);chart.append(barRow);
  });
  const selected=selectedLayers(),bundle=selected.filter(layer=>bundledLayers.has(layer)),has=id=>bundle.some(layer=>layer.metadata.id===id);
  const warnings=['Partial native cells assume uniform population. Coverage is numeric-cell support, not confidence. Agreement does not independently validate accuracy; disagreement does not determine accuracy.',...selected.map(layer=>`${layer.metadata.title}: ${layer.metadata.population_concept}; reference ${layer.metadata.reference_date||layer.metadata.year}.`)];
  if(has('worldpop-2025'))warnings.push('WorldPop Global2 R2025A v1 is an alpha public release.');
  if(has('worldpop-2025')&&has('grid3-2025'))warnings.push('WorldPop and GRID3 share producers/inputs and use different 2025 reference dates.');
  if(has('grid3-2025'))warnings.push('GRID3 NoData includes mapped unsettled cells, not numeric zeros.');
  if(has('ghspop-2025'))warnings.push('GHS-POP uses GPWv4.11 demographic inputs.');
  if(has('landscan-2020'))warnings.push('LandScan describes ambient population averaged over 24 hours.');
  if(results.some(r=>r.prepared_coverage<.999999999))warnings.push('The analysis extends outside at least one prepared native grid; missing area is excluded, never filled.');
  $('comparison-warnings').textContent=warnings.join(' ');
}
function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function stopDrawing(){drawing=false;firstCorner=null;$('draw').setAttribute('aria-pressed','false');$('draw').textContent='Draw rectangle (two clicks)';$('draw-help').textContent='Click a cell to inspect its native count. Pan by dragging; zoom with +/−.';}
function addOptions(){maps.forEach((_,i)=>{const select=$(`layer-${i}`),previous=select.value;select.replaceChildren(...layers.map(l=>{const option=document.createElement('option');option.value=l.metadata.id;option.textContent=`${l.metadata.synthetic?'SYNTHETIC':l.metadata.file_declarations?'IMPORT':'REAL'} · ${l.metadata.title} · ${l.metadata.version}`;return option;}));select.value=previous || layers[Math.min(i,layers.length-1)].metadata.id;});}
function setupRasterImport(){
  let active=null,timer=null,planned=null;
  const preset=$('raster-preset');preset.replaceChildren(...demo.sources.map((l,i)=>{const option=textNode('option',l.metadata.title);option.value=i;return option;}));
  function template(){
    const metadata=removeBundleClaims(structuredClone(demo.sources[Number(preset.value)].metadata));
    for(const key of ['source_asset_sha256_published_by_mirror','retrieval_date','modification','acquisition'])delete metadata[key];
    metadata.id+='-import';metadata.title+=' (import; user declaration)';metadata.retrieval_date='User: enter actual source retrieval date';metadata.modification='User: describe prior processing. This viewer reads a native window only.';
    $('raster-metadata').value=JSON.stringify(metadata,null,2);
    if($('raster-source').value==='remote')$('raster-url').value=demo.sources[Number(preset.value)].metadata.source_asset;
  }
  const finish=()=>{active?.terminate();active=null;planned=null;clearTimeout(timer);$('raster-submit').disabled=true;$('raster-cancel').disabled=true;};
  const deadline=()=>{clearTimeout(timer);timer=setTimeout(()=>cancelImport('TIFF phase exceeded its 120 second timeout. Previous valid comparison retained.'),120000);};
  cancelImport=message=>{editGeneration++;if(active){finish();$('raster-status').textContent=message||'Import cancelled. Previous valid comparison retained.';}};
  template();preset.onchange=()=>{cancelImport('Template changed; plan again.');template();};
  const sourceControls=()=>{const remote=$('raster-source').value==='remote';$('raster-file').hidden=remote;$('raster-file').disabled=remote;$('raster-file').required=!remote;$('raster-url').hidden=!remote;$('raster-url').disabled=!remote;$('raster-url').required=remote;};
  $('raster-source').onchange=()=>{cancelImport('Source changed; plan again.');sourceControls();if($('raster-source').value==='remote'){preset.value='2';template();}};
  sourceControls();
  $('raster-use-area').onclick=()=>{cancelImport('Import bounds changed; plan again.');if(draftBounds)['rw','rs','re','rn'].forEach((id,i)=>$(id).value=draftBounds[i]);};
  ['rw','rs','re','rn'].forEach((id,i)=>$(id).value=demo.default_aoi[i]);
  for(const id of ['raster-file','raster-url','raster-metadata','raster-declaration','rw','rs','re','rn'])$(id).addEventListener('input',()=>cancelImport('Import settings changed; plan again.'));
  $('raster-cancel').onclick=()=>cancelImport();
  $('raster-plan').onclick=()=>{
    cancelImport();cancelLoad('Import planning started. Previous valid comparison retained.');
    try{
      const remote=$('raster-source').value==='remote',file=$('raster-file').files[0],url=$('raster-url').value;
      if(!remote&&!file)throw Error('Choose a local TIFF.');
      if(!$('raster-declaration').checked)throw Error('Review the source declaration and confirm counts and no external mask.');
      const region=inputBounds(['rw','rs','re','rn']),metadata=removeBundleClaims(JSON.parse($('raster-metadata').value));
      validateLayer({metadata,cells:[{bounds:[0,0,1,1],population:0}]});
      if(idTaken(metadata.id))throw Error('Choose a unique metadata id; prepared source IDs are reserved.');
      if(layers.length>=16)throw Error('At most 16 layers may be loaded. Reload to start a new session.');
      const worker=new Worker('raster-worker.js');active=worker;$('raster-cancel').disabled=false;$('raster-status').textContent='Planning from bounded TIFF headers; previous comparison remains active.';
      deadline();
      worker.onmessage=({data})=>{
        if(active!==worker)return;
        try{
          if(data.progress){$('raster-transfer').textContent=`Actual ${remote?'transfer':'local bytes read'}: ${bytes(data.progress.actual_bytes)} in ${data.progress.requests} reads. ${data.progress.validator||''}`;return;}
          if(data.error)throw Error(data.error);
          if(!data.grid){clearTimeout(timer);timer=null;planned=data;$('raster-status').textContent=`Plan: ${planText(data.plan)}. Headers only so far; select Read to acquire pixels. Block costs exclude metadata and repeat reads.`;$('raster-submit').disabled=false;return;}
          const layer=validateLayer({metadata:{...metadata,file_declarations:data.file_declarations,acquisition:data.acquisition,import_extent:region,provenance_status:'User-declared source metadata; TIFF structure checked, source identity not independently verified'},grid:data.grid});
          if(idTaken(metadata.id))throw Error('That id is reserved or was added while reading; choose a unique id.');
          if(layers.length>=16)throw Error('At most 16 layers may be loaded.');
          const selected=layers.length?panelLayers():Array(4).fill(layer);selected[0]=layer;
          const display=prepareDisplay(selected,region);compare([layer],region);
          layers.push(layer);addOptions();$('layer-0').value=layer.metadata.id;comparisonUse='import';acquiredIds=new Set([layer.metadata.id]);updateBounds(region,display);maps[0].fitBounds(ll(layerBounds(layer)),{animate:false});updateOverview();clearError();
          $('raster-status').textContent=`Loaded ${data.grid.width} x ${data.grid.height} native cells. ${planText(data.plan)}. Actual ${remote?'transfer':'local reads'} ${bytes(data.acquisition.actual_bytes)}. Provenance is user-declared; a partial read does not verify a full-file SHA.`;finish();
        }catch(error){fail('TIFF import rejected: '+error.message+' Previous valid comparison retained.');$('raster-status').textContent='Import rejected.';finish();}
      };
      worker.onerror=event=>{if(active!==worker)return;fail('TIFF reader failed: '+event.message+' Previous valid comparison retained.');finish();};
      worker.postMessage({...(remote?{url}:{file}),bounds:region,mode:'plan'});
    }catch(error){fail('TIFF import rejected: '+error.message+' Previous valid comparison retained.');$('raster-status').textContent='Import rejected.';finish();}
  };
  $('raster-form').onsubmit=event=>{event.preventDefault();if(active&&planned){deadline();$('raster-submit').disabled=true;$('raster-status').textContent='Reading the planned native window; previous comparison remains active.';active.postMessage({action:'read'});}};
}

async function start(){
  if(!window.L)throw Error('The local Leaflet map library failed to load.');
  const response=await fetch('../data/population-catalog.json');if(!response.ok)throw Error(`Population catalog failed to load (HTTP ${response.status}).`);demo=await response.json();
  maps=Array.from({length:4},(_,i)=>L.map(`map-${i}`,{crs:L.CRS.EPSG4326,zoomSnap:.25,scrollWheelZoom:false,maxBounds:[[-90,-180],[90,180]]}).fitBounds(ll(demo.bounds)));
  overview=L.map('overview',{crs:L.CRS.EPSG4326,zoomControl:false,attributionControl:false,dragging:false,scrollWheelZoom:false,doubleClickZoom:false,touchZoom:false,keyboard:false,boxZoom:false}).fitBounds(ll(demo.bounds));
  L.rectangle(ll(demo.bounds),{color:'#698079',weight:1,fillOpacity:.15,interactive:false}).addTo(overview);
  overviewFrame=L.rectangle(maps[0].getBounds(),{color:'#183c40',weight:1,fill:false,interactive:false}).addTo(overview);
  maps.forEach((map,i)=>{
    map.attributionControl.setPrefix('<a href="https://leafletjs.com/">Leaflet</a>');map.attributionControl.addAttribution('Local cells; no basemap');
    map.on('move',()=>{if(i===0)updateOverview();if(moving||!$('sync').checked)return;moving=true;maps.forEach(other=>{if(other!==map)other.setView(map.getCenter(),map.getZoom(),{animate:false});});moving=false;});
    map.on('click',event=>{const point=event.latlng;if(!drawing){if(!layers.length)return;$('inspect-panel').value=i;$('inspect-lon').value=point.lng;$('inspect-lat').value=point.lat;inspect(i,point.lng,point.lat);return;}if(!firstCorner){firstCorner=point;$('draw-help').textContent='First corner set. Click the opposite corner; Escape cancels.';}else{try{updateDraft([Math.min(firstCorner.lng,point.lng),Math.min(firstCorner.lat,point.lat),Math.max(firstCorner.lng,point.lng),Math.max(firstCorner.lat,point.lat)]);stopDrawing();}catch(error){fail(error.message);}}});
    $(`layer-${i}`).addEventListener('change',()=>{cancelLoad('Layer selection changed. Previous windows retained.');cancelImport('Layer selection changed; plan again.');try{const display=prepareDisplay(panelLayers(),bounds);compare(selectedLayers(),bounds);comparisonUse='loaded windows';acquiredIds.clear();updateBounds(bounds,display);updateOverview();}catch(error){$(`layer-${i}`).value=$(`layer-${i}`).dataset.committed;fail('Layer selection rejected: '+error.message+' Previous valid comparison retained.');}});
    const fit=document.createElement('button');fit.textContent='Fit grid';fit.title='Zoom to this panel’s selected layer';fit.onclick=()=>map.fitBounds(ll(extent([layers.find(l=>l.metadata.id===$(`layer-${i}`).value)])),{animate:false});$(`layer-${i}`).parentElement.append(fit);
  });
  updateDraft(demo.default_aoi);
  $('inspect-form').onsubmit=event=>{event.preventDefault();inspect(Number($('inspect-panel').value),Number($('inspect-lon').value),Number($('inspect-lat').value));};
  const readDraft=()=>{try{updateDraft(inputBounds(['west','south','east','north']),false);}catch(error){draftBounds=null;cancelLoad('Invalid draft; previous valid comparison retained.');cancelImport('Study bounds changed; plan again.');showPlan();fail(error.message+' Previous valid comparison retained.');}};
  ['west','south','east','north'].forEach(id=>$(id).addEventListener('input',readDraft));
  $('bounds-form').addEventListener('submit',event=>{event.preventDefault();loadComparison().catch(error=>fail(error.message));});
  $('example').onclick=()=>updateDraft(demo.default_aoi);
  $('use-map').onclick=()=>{const b=maps[0].getBounds();try{updateDraft([b.getWest(),b.getSouth(),b.getEast(),b.getNorth()]);}catch(error){fail(error.message);}};
  $('load-cancel').onclick=()=>cancelLoad();
  $('compare-loaded').onclick=()=>{try{const region=validateBounds(draftBounds);compare(selectedLayers(),region);const display=prepareDisplay(panelLayers(),region);cancelLoad('Using loaded windows.');cancelImport('Comparison changed; plan again.');comparisonUse='loaded windows';acquiredIds.clear();updateBounds(region,display);$('status').textContent='Compared already loaded windows. No new pixels read; area beyond their native support has no coverage.';}catch(error){fail(error.message+' Previous valid comparison retained.');}};
  $('reset').textContent='Fit selected grids';
  $('reset').onclick=()=>maps.forEach(map=>map.fitBounds(ll(extent(selectedLayers())),{animate:false}));
  const fitArea=document.createElement('button');fitArea.textContent='Fit study bounds';fitArea.type='button';fitArea.onclick=()=>{if(draftBounds)maps.forEach(map=>map.fitBounds(ll(draftBounds),{animate:false}));};$('example').after(fitArea);
  $('sync').onchange=()=>{if($('sync').checked){maps.slice(1).forEach(map=>map.setView(maps[0].getCenter(),maps[0].getZoom(),{animate:false}));$('status').textContent='Navigation synchronized to the first panel.';}else $('status').textContent='Independent navigation enabled. Each panel can pan and zoom separately.';};
  $('draw').onclick=()=>{if(drawing){stopDrawing();return;}cancelLoad('Drawing started. Previous valid comparison retained.');cancelImport('Study drawing started; plan again.');drawing=true;firstCorner=null;$('draw').setAttribute('aria-pressed','true');$('draw').textContent='Cancel drawing';$('draw-help').textContent='Click the first rectangle corner on any map, then its opposite corner. Escape cancels.';};
  document.addEventListener('keydown',event=>{if(event.key==='Escape')stopDrawing();});
  $('csv').onclick=()=>download('population-comparison.csv',exportCSV(results),'text/csv;charset=utf-8');
  $('json').onclick=()=>download('population-comparison.json',JSON.stringify({schema_version:'2.0',generated_at:new Date().toISOString(),notice:'Population count comparisons. Each layer retains its synthetic status and source declarations; local-file provenance is user-declared. Partial native cells assume uniform counts. Disagreement does not establish accuracy.',bounds,method:METHOD,results},null,2),'application/json');
  $('svg').onclick=()=>{
    const escape=text=>String(text).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
    const wrap=text=>String(text).match(/.{1,120}/g)||[''];
    const credits=results.map(r=>wrap(`Source: ${r.metadata.source}. ${r.metadata.citation} License: ${r.metadata.license} (${r.metadata.license_url}).`));
    const titles=results.map(r=>[...wrap(`${r.metadata.title} (${r.metadata.synthetic?'SYNTHETIC':r.metadata.file_declarations?'IMPORTED; USER DECLARATION':'REAL SOURCE'}; ${r.metadata.acquisition?.transport||'local cells'}, ${r.metadata.reference_date||r.metadata.year})`),...wrap(`Coverage: ${(r.coverage*100).toFixed(1)}%. Population concept: ${r.metadata.population_concept}.`)]);
    const heights=results.map((_,i)=>65+(credits[i].length+titles[i].length)*14);
    const max=Math.max(...results.map(r=>r.population||0),1),height=140+heights.reduce((a,b)=>a+b,0);
    let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="900" height="${height}" viewBox="0 0 900 ${height}"><title>Population comparison with source provenance</title><desc>${escape(JSON.stringify({bounds,method:METHOD,results}))}</desc><rect width="900" height="${height}" fill="white"/><g font-family="sans-serif" fill="#183c40"><text x="24" y="32" font-size="20">Population within the analysis rectangle</text><text x="24" y="55" font-size="12">Bounds: ${escape(bounds.join(', '))}. Spherical area-weighted counts.</text>`;
    let y=90;
    results.forEach((r,i)=>{titles[i].forEach((line,j)=>{svg+=`<text x="24" y="${y+j*14}" font-size="13">${escape(line)}</text>`;});const barY=y+titles[i].length*14;svg+=`<rect x="24" y="${barY}" width="${(r.population||0)/max*650}" height="18" fill="#21776b"/><text x="700" y="${barY+15}" font-size="13">${escape(fmt(r.population))}</text>`;credits[i].forEach((line,j)=>{svg+=`<text x="24" y="${barY+36+j*14}" font-size="10">${escape(line)}</text>`;});y+=heights[i];});
    svg+=`<text x="24" y="${height-16}" font-size="11">Full provenance and method are embedded in this SVG description. Inspired by POPGRID; Leyk et al. (2019).</text></g></svg>`;download('population-comparison.svg',svg,'image/svg+xml');
  };
  $('import').addEventListener('change',async event=>{
    const file=event.target.files[0];if(!file)return;
    cancelLoad('GeoJSON import started. Previous valid comparison retained.');cancelImport('GeoJSON import started.');const token=++editGeneration;
    try{
      if(file.size>2*1024*1024)throw Error('Import is limited to 2 MB.');
      const document=JSON.parse(await file.text());if(token!==editGeneration)return;
      const layer=importGeoJSON(document);layer.metadata={...removeBundleClaims(layer.metadata),file_declarations:{name:file.name,size:file.size,last_modified:file.lastModified,reader:'Rectangular GeoJSON count-cell validator'},provenance_status:'User-declared GeoJSON source metadata; structure checked, source identity not independently verified'};
      if(idTaken(layer.metadata.id))throw Error('That layer id exists or is reserved; choose a unique metadata id.');
      if(layers.length>=16)throw Error('At most 16 layers may be loaded at once. Reload to start a new session.');
      const nextBounds=validateBounds(bounds||layerBounds(layer));compare([layer],nextBounds);
      const selected=layers.length?panelLayers():Array(4).fill(layer);selected[0]=layer;const display=prepareDisplay(selected,nextBounds);
      layers.push(layer);addOptions();$('layer-0').value=layer.metadata.id;maps[0].fitBounds(ll(extent([layer])),{animate:false});comparisonUse='loaded windows';acquiredIds.clear();updateBounds(nextBounds,display);updateOverview();clearError();$('status').textContent=`Imported ${layer.metadata.title} (${layer.cells.length} cells). First panel fitted to its extent; use “Fit study bounds” to return to your draft. Imported data stay in this browser session.`;
    }catch(error){if(token===editGeneration)fail('Import rejected: '+error.message);}finally{if(token===editGeneration)event.target.value='';}
  });
  setupRasterImport();
  document.querySelectorAll('button,select,input[type=file]').forEach(el=>el.disabled=false);$('raster-file').disabled=$('raster-source').value==='remote';$('raster-cancel').disabled=true;$('raster-submit').disabled=true;$('load-cancel').disabled=true;
  for(const id of ['csv','json','svg','reset','compare-loaded'])$(id).disabled=true;
  document.querySelectorAll('.panel-head select,.panel-head button').forEach(el=>el.disabled=true);
  // Read-only state makes the documented calculations inspectable in browser checks.
  window.populationViewer={maps,get layers(){return layers;},get bounds(){return bounds?.slice();},get draftBounds(){return draftBounds?.slice();},get results(){return structuredClone(results);},get classification(){return structuredClone(classification);},get cache(){return {bytes:cache.bytes,entries:cache.entries.size};},get loading(){return !!job;}};
  await loadComparison();
}
start().catch(error=>{fail('Unable to start the viewer: '+error.message);$('status').textContent='Viewer loading failed.';});
