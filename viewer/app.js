import {METHOD,validateBounds,validateLayer,importGeoJSON,compare,exportCSV,layerBounds,area,inspectCell} from './analysis.js';
const $=id=>document.getElementById(id), fmt=value=>value===null?'No coverage':value.toLocaleString(undefined,{maximumFractionDigits:2});
const ll=b=>[[b[1],b[0]],[b[3],b[2]]];
let layers=[], maps=[], grids=[], rectangles=[], results=[], bounds, demo, overview, overviewFrame, overviewAOI, moving=false, drawing=false, firstCorner=null;
const bundledLayers=new Set(),rasterImages=new WeakMap();
function removeBundleClaims(metadata){
  for(const key of Object.keys(metadata))if(['prepared_extent','processing_receipt','validation'].includes(key)||/verified/i.test(key))delete metadata[key];
  return metadata;
}
const fail=message=>{ $('error').textContent=message; $('error').hidden=false; };
const clearError=()=>{ if(!window.populationAssetError)$('error').hidden=true; };
function selectedLayers(){return [...new Set(maps.map((_,i)=>$(`layer-${i}`).value))].map(id=>layers.find(l=>l.metadata.id===id));}
function extent(layersToFit){return layersToFit.map(layerBounds).reduce((a,b)=>[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[2],b[2]),Math.max(a[3],b[3])],[Infinity,Infinity,-Infinity,-Infinity]);}
function textNode(tag,text){const node=document.createElement(tag);node.textContent=text;return node;}
const colors=['#eef3df','#b3d7ae','#66b79e','#258577','#12525b','#103445'];
function densityColor(value){return colors[value===0?0:Math.min(5,Math.max(1,Math.ceil(Math.log10(Math.max(1,value)))) )];}
function inspect(index,lon,lat){
  const layer=layers.find(l=>l.metadata.id===$(`layer-${index}`).value),cell=inspectCell(layer,lon,lat);
  $('inspection').textContent=cell?`${layer.metadata.title} · ${layer.metadata.year} · ${layer.metadata.population_concept}\nNative cell: ${cell.bounds.join(', ')} (west, south, east, north)${cell.row===undefined?'':` · row ${cell.row}, column ${cell.column}`}\nCount: ${cell.population===null?'NoData (not zero)':fmt(cell.population)+' people/cell'}\n${cell.population===null?layer.metadata.nodata_semantics:`Density for display: ${fmt(cell.population/(area(cell.bounds)*6371.0088**2))} people/km²`}\nSource: ${layer.metadata.source}\n${layer.metadata.citation} · License: ${layer.metadata.license}`:`${layer.metadata.title}: outside the prepared native grid. No global streaming is provided.`;
}
function gridImage(layer){
  if(rasterImages.has(layer))return rasterImages.get(layer);
  if(layer.grid){
    if(layer.grid.width>32767||layer.grid.height>32767)throw Error('Native display axes are limited to 32767 pixels. Choose a smaller native window; no resampling is performed.');
    const g=layer.grid,canvas=document.createElement('canvas');canvas.width=g.width;canvas.height=g.height;
    const ctx=canvas.getContext('2d'),image=ctx.createImageData(g.width,g.height);
    for(let y=0;y<g.height;y++){
      const cellArea=area([g.west,g.north-(y+1)*g.dy,g.west+g.dx,g.north-y*g.dy])*6371.0088**2;
      for(let x=0;x<g.width;x++){
        const value=g.values[y*g.width+x];if(value===null)continue;
        const color=densityColor(value/cellArea),offset=(y*g.width+x)*4;
        image.data[offset]=parseInt(color.slice(1,3),16);image.data[offset+1]=parseInt(color.slice(3,5),16);image.data[offset+2]=parseInt(color.slice(5,7),16);image.data[offset+3]=235;
      }
    }
    ctx.putImageData(image,0,0);
    const url=canvas.toDataURL('image/png');if(!url.startsWith('data:image/png'))throw Error('The native grid cannot be serialized for display. Choose a smaller window.');
    rasterImages.set(layer,url);return url;
  }
}
function renderLayer(index){
  const layer=layers.find(l=>l.metadata.id===$(`layer-${index}`).value),url=gridImage(layer);
  if(grids[index])grids[index].remove();
  if(layer.grid){
    grids[index]=L.imageOverlay(url,ll(layerBounds(layer)),{interactive:false,className:'native-grid',alt:`${layer.metadata.title}, native count grid shown as people per square kilometre`}).addTo(maps[index]);
  }else{
    grids[index]=L.layerGroup(layer.cells.map(cell=>L.rectangle(ll(cell.bounds),{color:'#416b64',weight:.5,fillColor:densityColor(cell.population/(area(cell.bounds)*6371.0088**2)),fillOpacity:.9,interactive:false}))).addTo(maps[index]);
  }
  const legend=$(`legend-${index}`);legend.replaceChildren(textNode('span','0'),Object.assign(document.createElement('span'),{className:'legend-ramp'}),textNode('span','≤10 · ≤100 · ≤1k · ≤10k · >10k people/km²'),textNode('span','Unshaded: NoData / outside grid. Zero: pale.'));
  const metadata=$(`metadata-${index}`);metadata.replaceChildren();
  for (const [key,value] of Object.entries(layer.metadata)){metadata.append(textNode('dt',key.replaceAll('_',' ')),textNode('dd',value!==null&&typeof value==='object'?JSON.stringify(value):String(value)));}
  if(rectangles[index]) rectangles[index].bringToFront();
}
function updateOverview(){if(overviewFrame){overviewFrame.setBounds(maps[0].getBounds());const frame=maps[0].getBounds();overview.fitBounds(L.latLngBounds(ll(extent(selectedLayers()))).extend(frame),{padding:[6,6],animate:false});}}
function updateBounds(next){
  const valid=validateBounds(next); // Validate completely before changing the active analysis.
  bounds=valid;
  ['west','south','east','north'].forEach((id,i)=>$(id).value=valid[i]);
  maps.forEach((map,i)=>{if(rectangles[i])rectangles[i].setBounds(ll(valid));else rectangles[i]=L.rectangle(ll(valid),{color:'#176bc0',weight:2.5,fill:false,interactive:false}).addTo(map);});
  if(overviewAOI)overviewAOI.setBounds(ll(valid));
  else overviewAOI=L.rectangle(ll(valid),{color:'#176bc0',weight:2,fill:false,interactive:false}).addTo(overview);
  clearError();renderResults();
}
function renderResults(){
  results=compare(selectedLayers(),bounds);
  $('area-description').textContent=`Active bounds: ${bounds.join(', ')} (W, S, E, N). Method: ${METHOD}.`;
  const body=$('results'),chart=$('chart');body.replaceChildren();chart.replaceChildren();
  const max=Math.max(...results.map(r=>r.population||0),1);
  results.forEach(result=>{
    const row=document.createElement('tr'),label=textNode('td',`${result.metadata.title} / ${result.metadata.year}`);
    label.append(textNode('small',`${result.metadata.synthetic?'SYNTHETIC fixture':result.metadata.file_declarations?'LOCAL FILE · user-declared provenance':'PROVIDER COUNTS'} · ${result.metadata.reference_date||result.metadata.year} · ${result.metadata.population_concept}`));
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
function addOptions(){maps.forEach((_,i)=>{const select=$(`layer-${i}`),previous=select.value;select.replaceChildren(...layers.map(l=>{const option=document.createElement('option');option.value=l.metadata.id;option.textContent=`${l.metadata.synthetic?'SYNTHETIC':l.metadata.file_declarations?'LOCAL FILE':'REAL'} · ${l.metadata.title} · ${l.metadata.version}`;return option;}));select.value=previous || layers[i].metadata.id;});}
function setupRasterImport(){
  let active=null;
  const preset=$('raster-preset');preset.replaceChildren(...layers.map((l,i)=>{const option=textNode('option',l.metadata.title);option.value=i;return option;}));
  function template(){
    const metadata=structuredClone(layers[Number(preset.value)].metadata);
    for(const key of ['prepared_extent','processing_receipt','validation','source_asset_sha256_published_by_mirror','source_asset_sha256_locally_verified','retrieval_date','modification'])delete metadata[key];
    metadata.id+='-local';metadata.title+=' (local file; user declaration)';metadata.retrieval_date='User: enter actual source retrieval date';metadata.modification='User: describe prior processing. This viewer will read a native file window only.';
    $('raster-metadata').value=JSON.stringify(metadata,null,2);
  }
  template();preset.onchange=template;
  $('raster-use-area').onclick=()=>['rw','rs','re','rn'].forEach((id,i)=>$(id).value=bounds[i]);
  ['rw','rs','re','rn'].forEach((id,i)=>$(id).value=demo.default_aoi[i]);
  const finish=()=>{active?.terminate();active=null;$('raster-submit').disabled=false;$('raster-cancel').disabled=true;};
  $('raster-cancel').onclick=()=>{finish();$('raster-status').textContent='Import cancelled. The previous valid layers and analysis are retained.';};
  $('raster-form').onsubmit=event=>{
    event.preventDefault();
    try{
      if(active)throw Error('A TIFF read is already active. Cancel it before starting another.');
      const file=$('raster-file').files[0];if(!file)throw Error('Choose a local TIFF.');
      const region=validateBounds(['rw','rs','re','rn'].map(id=>Number($(id).value))),metadata=JSON.parse($('raster-metadata').value);
      validateLayer({metadata,cells:[{bounds:[0,0,1,1],population:0}]});
      if(layers.some(l=>l.metadata.id===metadata.id))throw Error('Choose a unique metadata id.');
      if(layers.length>=16)throw Error('At most 16 layers may be loaded. Reload to start a new session.');
      // Verified bundle receipts must never attach to a user-selected file.
      removeBundleClaims(metadata);
      const worker=new Worker('raster-worker.js');active=worker;$('raster-submit').disabled=true;$('raster-cancel').disabled=false;$('raster-status').textContent='Reading selected native window locally… Cancel remains available.';
      worker.onmessage=({data})=>{
        if(active!==worker)return;
        try{
          if(data.error)throw Error(data.error);
          const layer=validateLayer({metadata:{...metadata,file_declarations:data.file_declarations,import_extent:region,provenance_status:'User-declared source metadata; file structure checked, source identity not independently verified'},grid:data.grid});
          if(layers.some(l=>l.metadata.id===metadata.id))throw Error('That id was added while reading; choose a unique id.');
          if(layers.length>=16)throw Error('At most 16 layers may be loaded. Reload to start a new session.');
          gridImage(layer); // Complete fallible serialization before changing the valid session.
          layers.push(layer);addOptions();$('layer-0').value=layer.metadata.id;renderLayer(0);maps[0].fitBounds(ll(layerBounds(layer)),{animate:false});renderResults();updateOverview();clearError();$('raster-status').textContent=`Loaded ${data.grid.width} × ${data.grid.height} native cells from ${file.name}. Source provenance is user-declared. Select any area inside this window for comparisons; import another window for another area.`;
        }catch(error){fail('TIFF import rejected: '+error.message+' The previous valid analysis is retained.');$('raster-status').textContent='Import rejected.';}finally{finish();}
      };
      worker.onerror=event=>{if(active!==worker)return;fail('TIFF reader failed: '+event.message+' The previous valid analysis is retained.');finish();};
      worker.postMessage({file,bounds:region});
    }catch(error){fail('TIFF import rejected: '+error.message+' The previous valid analysis is retained.');}
  };
}
async function start(){
  if(!window.L)throw Error('The local Leaflet map library failed to load.');
  const response=await fetch('../data/population.json');if(!response.ok)throw Error(`Real population data failed to load (HTTP ${response.status}).`);demo=await response.json();layers=demo.layers.map(validateLayer);
  layers.forEach(layer=>bundledLayers.add(layer));
  maps=Array.from({length:4},(_,i)=>L.map(`map-${i}`,{crs:L.CRS.EPSG4326,zoomSnap:.25,scrollWheelZoom:false,maxBounds:[[-90,-180],[90,180]]}).fitBounds(ll(demo.bounds)));
  overview=L.map('overview',{crs:L.CRS.EPSG4326,zoomControl:false,attributionControl:false,dragging:false,scrollWheelZoom:false,doubleClickZoom:false,touchZoom:false,keyboard:false,boxZoom:false}).fitBounds(ll(demo.bounds));
  L.rectangle(ll(demo.bounds),{color:'#698079',weight:1,fillOpacity:.15,interactive:false}).addTo(overview);
  overviewFrame=L.rectangle(maps[0].getBounds(),{color:'#183c40',weight:1,fill:false,interactive:false}).addTo(overview);
  addOptions();
  maps.forEach((map,i)=>{
    map.attributionControl.setPrefix('<a href="https://leafletjs.com/">Leaflet</a>');map.attributionControl.addAttribution('Local cells; no basemap');
    map.on('move',()=>{if(i===0)updateOverview();if(moving||!$('sync').checked)return;moving=true;maps.forEach(other=>{if(other!==map)other.setView(map.getCenter(),map.getZoom(),{animate:false});});moving=false;});
    map.on('click',event=>{const point=event.latlng;if(!drawing){$('inspect-panel').value=i;$('inspect-lon').value=point.lng;$('inspect-lat').value=point.lat;inspect(i,point.lng,point.lat);return;}if(!firstCorner){firstCorner=point;$('draw-help').textContent='First corner set. Click the opposite corner; Escape cancels.';}else{try{updateBounds([Math.min(firstCorner.lng,point.lng),Math.min(firstCorner.lat,point.lat),Math.max(firstCorner.lng,point.lng),Math.max(firstCorner.lat,point.lat)]);stopDrawing();}catch(error){fail(error.message);}}});
    $(`layer-${i}`).addEventListener('change',()=>{renderLayer(i);renderResults();updateOverview();});renderLayer(i);
    const fit=document.createElement('button');fit.textContent='Fit grid';fit.title='Zoom to this panel’s selected layer';fit.onclick=()=>map.fitBounds(ll(extent([layers.find(l=>l.metadata.id===$(`layer-${i}`).value)])),{animate:false});$(`layer-${i}`).parentElement.append(fit);
  });
  updateBounds(demo.default_aoi);
  $('inspect-form').onsubmit=event=>{event.preventDefault();inspect(Number($('inspect-panel').value),Number($('inspect-lon').value),Number($('inspect-lat').value));};
  $('bounds-form').addEventListener('submit',event=>{event.preventDefault();try{updateBounds(['west','south','east','north'].map(id=>Number($(id).value)));}catch(error){fail(error.message+' The previous valid analysis is retained.');}});
  $('example').onclick=()=>updateBounds(demo.default_aoi);
  $('reset').textContent='Fit selected grids';
  $('reset').onclick=()=>maps.forEach(map=>map.fitBounds(ll(extent(selectedLayers())),{animate:false}));
  const fitArea=document.createElement('button');fitArea.textContent='Fit analysis area';fitArea.type='button';fitArea.onclick=()=>maps.forEach(map=>map.fitBounds(ll(bounds),{animate:false}));$('example').after(fitArea);
  $('sync').onchange=()=>{if($('sync').checked){maps.slice(1).forEach(map=>map.setView(maps[0].getCenter(),maps[0].getZoom(),{animate:false}));$('status').textContent='Navigation synchronized to the first panel.';}else $('status').textContent='Independent navigation enabled. Each panel can pan and zoom separately.';};
  $('draw').onclick=()=>{if(drawing){stopDrawing();return;}drawing=true;firstCorner=null;$('draw').setAttribute('aria-pressed','true');$('draw').textContent='Cancel drawing';$('draw-help').textContent='Click the first rectangle corner on any map, then its opposite corner. Escape cancels.';};
  document.addEventListener('keydown',event=>{if(event.key==='Escape')stopDrawing();});
  $('csv').onclick=()=>download('population-comparison.csv',exportCSV(results),'text/csv;charset=utf-8');
  $('json').onclick=()=>download('population-comparison.json',JSON.stringify({schema_version:'2.0',generated_at:new Date().toISOString(),notice:'Population count comparisons. Each layer retains its synthetic status and source declarations; local-file provenance is user-declared. Partial native cells assume uniform counts. Disagreement does not establish accuracy.',bounds,method:METHOD,results},null,2),'application/json');
  $('svg').onclick=()=>{
    const escape=text=>String(text).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
    const wrap=text=>String(text).match(/.{1,120}/g)||[''];
    const credits=results.map(r=>wrap(`Source: ${r.metadata.source}. ${r.metadata.citation} License: ${r.metadata.license} (${r.metadata.license_url}).`));
    const titles=results.map(r=>[...wrap(`${r.metadata.title} (${r.metadata.synthetic?'SYNTHETIC':r.metadata.file_declarations?'LOCAL FILE; USER DECLARATION':'REAL SOURCE'}, ${r.metadata.reference_date||r.metadata.year})`),...wrap(`Coverage: ${(r.coverage*100).toFixed(1)}%. Population concept: ${r.metadata.population_concept}.`)]);
    const heights=results.map((_,i)=>65+(credits[i].length+titles[i].length)*14);
    const max=Math.max(...results.map(r=>r.population||0),1),height=140+heights.reduce((a,b)=>a+b,0);
    let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="900" height="${height}" viewBox="0 0 900 ${height}"><title>Population comparison with source provenance</title><desc>${escape(JSON.stringify({bounds,method:METHOD,results}))}</desc><rect width="900" height="${height}" fill="white"/><g font-family="sans-serif" fill="#183c40"><text x="24" y="32" font-size="20">Population within the analysis rectangle</text><text x="24" y="55" font-size="12">Bounds: ${escape(bounds.join(', '))}. Spherical area-weighted counts.</text>`;
    let y=90;
    results.forEach((r,i)=>{titles[i].forEach((line,j)=>{svg+=`<text x="24" y="${y+j*14}" font-size="13">${escape(line)}</text>`;});const barY=y+titles[i].length*14;svg+=`<rect x="24" y="${barY}" width="${(r.population||0)/max*650}" height="18" fill="#21776b"/><text x="700" y="${barY+15}" font-size="13">${escape(fmt(r.population))}</text>`;credits[i].forEach((line,j)=>{svg+=`<text x="24" y="${barY+36+j*14}" font-size="10">${escape(line)}</text>`;});y+=heights[i];});
    svg+=`<text x="24" y="${height-16}" font-size="11">Full provenance and method are embedded in this SVG description. Inspired by POPGRID; Leyk et al. (2019).</text></g></svg>`;download('population-comparison.svg',svg,'image/svg+xml');
  };
  $('import').addEventListener('change',async event=>{
    const file=event.target.files[0];if(!file)return;
    try{if(file.size>2*1024*1024)throw Error('Import is limited to 2 MB.');const layer=importGeoJSON(JSON.parse(await file.text()));layer.metadata={...removeBundleClaims(layer.metadata),file_declarations:{name:file.name,size:file.size,last_modified:file.lastModified,reader:'Rectangular GeoJSON count-cell validator'},provenance_status:'User-declared GeoJSON source metadata; structure checked, source identity not independently verified'};if(layers.some(l=>l.metadata.id===layer.metadata.id))throw Error('That layer id already exists; choose a unique metadata id.');if(layers.length>=16)throw Error('At most 16 layers may be loaded at once. Reload to start a new session.');layers.push(layer);addOptions();$('layer-0').value=layer.metadata.id;renderLayer(0);maps[0].fitBounds(ll(extent([layer])),{animate:false});renderResults();updateOverview();clearError();$('status').textContent=`Imported ${layer.metadata.title} (${layer.cells.length} cells). First panel fitted to its extent; use “Fit analysis area” to return to your boundary. Imported data stay in this browser session.`;}catch(error){fail('Import rejected: '+error.message);}finally{event.target.value='';}
  });
  setupRasterImport();
  document.querySelectorAll('button,select,input[type=file]').forEach(el=>el.disabled=false);$('raster-cancel').disabled=true;
  $('status').textContent='Four genuine provider grids loaded for Greater Lagos [3.2, 6.35, 3.6, 6.7]. All calculations run in this browser. Prepared excerpts are regional; import a local count TIFF for another area.';
  // Read-only state makes the documented calculations inspectable in browser checks.
  window.populationViewer={maps,get layers(){return layers;},get bounds(){return bounds.slice();},get results(){return structuredClone(results);}};
}
start().catch(error=>{fail('Unable to start the viewer: '+error.message);$('status').textContent='Viewer loading failed.';});
