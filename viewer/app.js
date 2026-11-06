import {METHOD,validateBounds,validateLayer,importGeoJSON,compare,exportCSV} from './analysis.js';
const $=id=>document.getElementById(id), fmt=value=>value===null?'No coverage':value.toLocaleString(undefined,{maximumFractionDigits:2});
const ll=b=>[[b[1],b[0]],[b[3],b[2]]];
let layers=[], maps=[], grids=[], rectangles=[], results=[], bounds, demo, overview, overviewFrame, overviewAOI, moving=false, drawing=false, firstCorner=null;
const fail=message=>{ $('error').textContent=message; $('error').hidden=false; };
const clearError=()=>{ if(!window.populationAssetError)$('error').hidden=true; };
function selectedLayers(){return [...new Set(maps.map((_,i)=>$(`layer-${i}`).value))].map(id=>layers.find(l=>l.metadata.id===id));}
function extent(layersToFit){const cells=layersToFit.flatMap(layer=>layer.cells);return [Math.min(...cells.map(c=>c.bounds[0])),Math.min(...cells.map(c=>c.bounds[1])),Math.max(...cells.map(c=>c.bounds[2])),Math.max(...cells.map(c=>c.bounds[3]))];}
function textNode(tag,text){const node=document.createElement(tag);node.textContent=text;return node;}
function renderLayer(index){
  const layer=layers.find(l=>l.metadata.id===$(`layer-${index}`).value), max=Math.max(...layer.cells.map(c=>c.population),1);
  if (grids[index]) grids[index].remove();
  const colors=['#e8efd8','#9ec6a0','#4c9b88','#14685f','#103e48'];
  grids[index]=L.layerGroup(layer.cells.map(cell=>{
    const rect=L.rectangle(ll(cell.bounds),{color:'#416b64',weight:.7,fillColor:colors[Math.min(4,Math.floor(cell.population/max*5))],fillOpacity:.85});
    const inspect=()=>{
      if(drawing)return;
      $('inspection').textContent=`${layer.metadata.title} · ${layer.metadata.synthetic?'SYNTHETIC':'Imported; declared non-synthetic'} · ${layer.metadata.year}\nNative cell: ${cell.bounds.join(', ')} (west, south, east, north)\nCount: ${fmt(cell.population)} people/cell · ${layer.metadata.resolution}\nSource: ${layer.metadata.source}\n${layer.metadata.citation} · License: ${layer.metadata.license}`;
    };
    rect.on('click',inspect);
    rect.on('add',()=>{const path=rect.getElement();path.setAttribute('tabindex','0');path.setAttribute('role','button');path.setAttribute('aria-label',`${layer.metadata.title}: ${fmt(cell.population)} people; cell ${cell.bounds.join(', ')}. Inspect native cell.`);path.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();event.stopPropagation();inspect();}});});
    return rect;
  })).addTo(maps[index]);
  const legend=$(`legend-${index}`);legend.replaceChildren(textNode('span','0'),Object.assign(document.createElement('span'),{className:'legend-ramp'}),textNode('span',`${fmt(max)} people/cell · native grid`),textNode('span','Unshaded: no coverage'));
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
    label.append(textNode('small',result.metadata.synthetic?'SYNTHETIC · invented teaching counts':'Imported · declared non-synthetic'));
    row.append(label,textNode('td',fmt(result.population)),textNode('td',`${(result.coverage*100).toFixed(1)}%`),textNode('td',result.intersected_cells));body.append(row);
    const barRow=document.createElement('div');barRow.className='bar-row';
    const barLabel=document.createElement('div');barLabel.className='bar-label';barLabel.append(textNode('span',result.metadata.title),textNode('strong',fmt(result.population)));
    const track=document.createElement('div');track.className='bar-track';const bar=document.createElement('div');bar.className='bar';bar.style.width=`${(result.population||0)/max*100}%`;track.append(bar);barRow.append(barLabel,track);chart.append(barRow);
  });
}
function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function stopDrawing(){drawing=false;firstCorner=null;$('draw').setAttribute('aria-pressed','false');$('draw').textContent='Draw rectangle (two clicks)';$('draw-help').textContent='Click a cell to inspect its native count. Pan by dragging; zoom with +/−.';}
function addOptions(){maps.forEach((_,i)=>{const select=$(`layer-${i}`),previous=select.value;select.replaceChildren(...layers.map(l=>{const option=document.createElement('option');option.value=l.metadata.id;option.textContent=`${l.metadata.synthetic?'SYNTHETIC':'IMPORTED'} · ${l.metadata.title}`;return option;}));select.value=previous || layers[i].metadata.id;});}
async function start(){
  if(!window.L)throw Error('The local Leaflet map library failed to load.');
  const response=await fetch('../data/demo.json');if(!response.ok)throw Error(`Teaching data failed to load (HTTP ${response.status}).`);demo=await response.json();layers=demo.layers.map(validateLayer);
  maps=Array.from({length:4},(_,i)=>L.map(`map-${i}`,{crs:L.CRS.EPSG4326,zoomSnap:.25,scrollWheelZoom:false,maxBounds:[[-90,-180],[90,180]]}).fitBounds(ll(demo.bounds)));
  overview=L.map('overview',{crs:L.CRS.EPSG4326,zoomControl:false,attributionControl:false,dragging:false,scrollWheelZoom:false,doubleClickZoom:false,touchZoom:false,keyboard:false,boxZoom:false}).fitBounds(ll([119.9,13.9,120.5,14.5]));
  L.rectangle(ll(demo.bounds),{color:'#698079',weight:1,fillOpacity:.15,interactive:false}).addTo(overview);
  overviewFrame=L.rectangle(maps[0].getBounds(),{color:'#183c40',weight:1,fill:false,interactive:false}).addTo(overview);
  addOptions();
  maps.forEach((map,i)=>{
    map.attributionControl.setPrefix('<a href="https://leafletjs.com/">Leaflet</a>');map.attributionControl.addAttribution('Local cells; no basemap');
    map.on('move',()=>{if(i===0)updateOverview();if(moving||!$('sync').checked)return;moving=true;maps.forEach(other=>{if(other!==map)other.setView(map.getCenter(),map.getZoom(),{animate:false});});moving=false;});
    map.on('click',event=>{if(!drawing)return;const point=event.latlng;if(!firstCorner){firstCorner=point;$('draw-help').textContent='First corner set. Click the opposite corner; Escape cancels.';}else{try{updateBounds([Math.min(firstCorner.lng,point.lng),Math.min(firstCorner.lat,point.lat),Math.max(firstCorner.lng,point.lng),Math.max(firstCorner.lat,point.lat)]);stopDrawing();}catch(error){fail(error.message);}}});
    $(`layer-${i}`).addEventListener('change',()=>{renderLayer(i);renderResults();updateOverview();});renderLayer(i);
    const fit=document.createElement('button');fit.textContent='Fit grid';fit.title='Zoom to this panel’s selected layer';fit.onclick=()=>map.fitBounds(ll(extent([layers.find(l=>l.metadata.id===$(`layer-${i}`).value)])),{animate:false});$(`layer-${i}`).parentElement.append(fit);
  });
  updateBounds(demo.default_aoi);
  $('bounds-form').addEventListener('submit',event=>{event.preventDefault();try{updateBounds(['west','south','east','north'].map(id=>Number($(id).value)));}catch(error){fail(error.message+' The previous valid analysis is retained.');}});
  $('example').onclick=()=>updateBounds(demo.default_aoi);
  $('reset').textContent='Fit selected grids';
  $('reset').onclick=()=>maps.forEach(map=>map.fitBounds(ll(extent(selectedLayers())),{animate:false}));
  const fitArea=document.createElement('button');fitArea.textContent='Fit analysis area';fitArea.type='button';fitArea.onclick=()=>maps.forEach(map=>map.fitBounds(ll(bounds),{animate:false}));$('example').after(fitArea);
  $('sync').onchange=()=>{if($('sync').checked){maps.slice(1).forEach(map=>map.setView(maps[0].getCenter(),maps[0].getZoom(),{animate:false}));$('status').textContent='Navigation synchronized to the first panel.';}else $('status').textContent='Independent navigation enabled. Each panel can pan and zoom separately.';};
  $('draw').onclick=()=>{if(drawing){stopDrawing();return;}drawing=true;firstCorner=null;$('draw').setAttribute('aria-pressed','true');$('draw').textContent='Cancel drawing';$('draw-help').textContent='Click the first rectangle corner on any map, then its opposite corner. Escape cancels.';};
  document.addEventListener('keydown',event=>{if(event.key==='Escape')stopDrawing();});
  $('csv').onclick=()=>download('population-comparison.csv',exportCSV(results),'text/csv;charset=utf-8');
  $('json').onclick=()=>download('population-comparison.json',JSON.stringify({schema_version:'1.0',generated_at:new Date().toISOString(),notice:'Bundled layers are SYNTHETIC teaching counts. Imported layers retain their declared synthetic status.',bounds,method:METHOD,results},null,2),'application/json');
  $('svg').onclick=()=>{
    const escape=text=>String(text).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
    const wrap=text=>String(text).match(/.{1,120}/g)||[''];
    const credits=results.map(r=>wrap(`Source: ${r.metadata.source}. ${r.metadata.citation} License: ${r.metadata.license} (${r.metadata.license_url}).`));
    const titles=results.map(r=>[...wrap(`${r.metadata.title} (${r.metadata.synthetic?'SYNTHETIC':'IMPORTED'}, ${r.metadata.year})`),...wrap(`Coverage: ${(r.coverage*100).toFixed(1)}%. Population concept: ${r.metadata.population_concept}.`)]);
    const heights=results.map((_,i)=>65+(credits[i].length+titles[i].length)*14);
    const max=Math.max(...results.map(r=>r.population||0),1),height=140+heights.reduce((a,b)=>a+b,0);
    let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="900" height="${height}" viewBox="0 0 900 ${height}"><title>Population comparison — synthetic status identified per layer</title><desc>${escape(JSON.stringify({bounds,method:METHOD,results}))}</desc><rect width="900" height="${height}" fill="white"/><g font-family="sans-serif" fill="#183c40"><text x="24" y="32" font-size="20">Population within the analysis rectangle</text><text x="24" y="55" font-size="12">Bounds: ${escape(bounds.join(', '))}. Spherical area-weighted counts.</text>`;
    let y=90;
    results.forEach((r,i)=>{titles[i].forEach((line,j)=>{svg+=`<text x="24" y="${y+j*14}" font-size="13">${escape(line)}</text>`;});const barY=y+titles[i].length*14;svg+=`<rect x="24" y="${barY}" width="${(r.population||0)/max*650}" height="18" fill="#21776b"/><text x="700" y="${barY+15}" font-size="13">${escape(fmt(r.population))}</text>`;credits[i].forEach((line,j)=>{svg+=`<text x="24" y="${barY+36+j*14}" font-size="10">${escape(line)}</text>`;});y+=heights[i];});
    svg+=`<text x="24" y="${height-16}" font-size="11">Full provenance and method are embedded in this SVG description. Inspired by POPGRID; Leyk et al. (2019).</text></g></svg>`;download('population-comparison.svg',svg,'image/svg+xml');
  };
  $('import').addEventListener('change',async event=>{
    const file=event.target.files[0];if(!file)return;
    try{if(file.size>2*1024*1024)throw Error('Import is limited to 2 MB.');const layer=importGeoJSON(JSON.parse(await file.text()));if(layers.some(l=>l.metadata.id===layer.metadata.id))throw Error('That layer id already exists; choose a unique metadata id.');if(layers.length>=16)throw Error('At most 16 layers may be loaded at once. Reload to start a new session.');layers.push(layer);addOptions();$('layer-0').value=layer.metadata.id;renderLayer(0);maps[0].fitBounds(ll(extent([layer])),{animate:false});renderResults();updateOverview();clearError();$('status').textContent=`Imported ${layer.metadata.title} (${layer.cells.length} cells). First panel fitted to its extent; use “Fit analysis area” to return to your boundary. Imported data stay in this browser session.`;}catch(error){fail('Import rejected: '+error.message);}finally{event.target.value='';}
  });
  document.querySelectorAll('button,select,input[type=file]').forEach(el=>el.disabled=false);
  $('status').textContent='Four local synthetic grids loaded. All calculations run in your browser; no population service is queried.';
  // Read-only state makes the documented calculations inspectable in browser checks.
  window.populationViewer={maps,get layers(){return layers;},get bounds(){return bounds.slice();},get results(){return structuredClone(results);}};
}
start().catch(error=>{fail('Unable to start the viewer: '+error.message);$('status').textContent='Viewer loading failed.';});
