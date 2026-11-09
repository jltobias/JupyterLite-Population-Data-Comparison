/* Dependency-free counterpart to notebooks/population_tools.py. */
export const METHOD = 'Spherical area-weighted count allocation; uniform population within each rectangular cell';
export const METADATA = ['id', 'title', 'source', 'citation', 'license', 'license_url', 'year', 'version', 'synthetic', 'units', 'crs', 'resolution', 'population_concept', 'allocation', 'census_vintage'];
export const MAX_GRID_CELLS = 262144;
// ColorBrewer YlOrBr, five sequential classes: https://colorbrewer2.org/#type=sequential&scheme=YlOrBr&n=5
export const DENSITY_COLORS = Object.freeze(['#ffffd4','#fed98e','#fe9929','#d95f0e','#993404']);
export const ZERO_DENSITY_COLOR = '#eeeeee';
const finite = value => typeof value === 'number' && Number.isFinite(value);
export function cellDensity(population,bounds) {
  if(!finite(population)||population<0)throw Error('Density requires finite nonnegative native counts.');
  const value=population/(area(bounds)*6371.0088**2);
  // Preserve positive versus zero counts even beyond the representable density range.
  return population===0?0:value===0?Number.MIN_VALUE:Math.min(value,Number.MAX_VALUE);
}
export function classifyDensity(layers,bounds) {
  validateBounds(bounds);
  const unique=[...new Map(layers.map(layer=>[layer.metadata.id,layer])).values()],samples=[];
  for(const layer of unique)for(const cell of iterateCells(layer,bounds)){
    if(cell.population===0)continue;
    const overlap=intersection(cell.bounds,bounds);if(!overlap)continue;
    const weight=area(overlap),value=cellDensity(cell.population,cell.bounds);
    samples.push({value,weight});
  }
  samples.sort((a,b)=>a.value-b.value||a.weight-b.weight);
  const thresholds=[];
  if(samples.length){
    // Compensated sums and a few ULPs of area tolerance keep exact quintile
    // boundaries stable under source order and floating-point geometry arithmetic.
    let total=0,correction=0;
    for(const {weight} of samples){const adjusted=weight-correction,next=total+adjusted;correction=(next-total)-adjusted;total=next;}
    const tolerance=total*8*Number.EPSILON;
    let index=0,cumulative=samples[0].weight,cumulativeCorrection=0;
    for(let cut=1;cut<5;cut++){
      const target=total*cut/5;
      while(cumulative<target-tolerance&&index<samples.length-1){const adjusted=samples[++index].weight-cumulativeCorrection,next=cumulative+adjusted;cumulativeCorrection=(next-cumulative)-adjusted;cumulative=next;}
      thresholds.push(samples[index].value);
    }
  }
  return {method:'Shared area-weighted positive-density quantiles',units:'people/km²',bounds:bounds.slice(),layer_ids:unique.map(layer=>layer.metadata.id),percentiles:[20,40,60,80],thresholds,palette:'ColorBrewer YlOrBr (5)',colors:[...DENSITY_COLORS],zero_color:ZERO_DENSITY_COLOR,nodata:'transparent',weight:'Spherical native-cell overlap with committed study bounds; density uses full native-cell area',ties:'Equal values stay together; upper class bounds are inclusive; some classes may be empty',numeric_limits:'Positive density underflow/overflow saturates to the smallest/largest finite positive number for display only; weighted boundaries allow 8 machine epsilons of pooled area'};
}
export function densityColor(value,classification) {
  if(value===null)return null;
  if(!finite(value)||value<0)throw Error('Density must be finite and nonnegative for display.');
  if(value===0)return ZERO_DENSITY_COLOR;
  if(!classification.thresholds.length)return DENSITY_COLORS[0];
  const index=classification.thresholds.findIndex(upper=>value<=upper);
  return DENSITY_COLORS[index<0?4:index];
}
export function validateBounds(bounds) {
  if (!Array.isArray(bounds) || bounds.length !== 4 || !bounds.every(finite)) throw Error('Bounds need four finite numbers: west, south, east, north.');
  const [w,s,e,n] = bounds;
  if (!(w >= -180 && w < e && e <= 180 && s >= -90 && s < n && n <= 90)) throw Error('Use west < east and south < north within WGS84 ranges. Antimeridian areas are unsupported.');
  area(bounds);
  return bounds.slice();
}
export function area([w,s,e,n]) {
  const polarDistance=s+n>=0?((90-n)+(90-s))/2:((90+n)+(90+s))/2;
  const result=(e-w)*Math.PI/180 * (2*Math.sin(polarDistance*Math.PI/180)*Math.sin((n-s)*Math.PI/360));
  if(!finite(result)||result<=0)throw Error('Rectangle area must be positive and representable at floating-point precision.');
  return result;
}
export function intersection(a,b) {
  const c=[Math.max(a[0],b[0]),Math.max(a[1],b[1]),Math.min(a[2],b[2]),Math.min(a[3],b[3])];
  return c[0]<c[2] && c[1]<c[3] ? c : null;
}
export function validateLayer(layer) {
  const metadata=layer?.metadata;
  if (!metadata || typeof metadata!=='object' || Array.isArray(metadata) || METADATA.some(k => !Object.hasOwn(metadata,k))) throw Error(`Layer metadata must provide: ${METADATA.join(', ')}.`);
  validateJSONMetadata(metadata);
  for (const key of METADATA.filter(k=>!['year','synthetic'].includes(k))) {
    if (typeof metadata[key] !== 'string' || !metadata[key].trim() || metadata[key].length>4000) throw Error(`Metadata ${key} must be nonempty text (maximum 4000 characters).`);
  }
  if (typeof metadata.synthetic !== 'boolean' || !Number.isInteger(metadata.year) || metadata.year<0 || metadata.year>9999) throw Error('Provide a boolean synthetic status and an integer year (0–9999).');
  if (metadata.units!=='people/cell' || metadata.crs!=='EPSG:4326') throw Error('Only people/cell counts in EPSG:4326 are supported; convert density before import.');
  if (Object.hasOwn(layer,'grid')) {
    const g=layer.grid;
    if(!g||typeof g!=='object'||Array.isArray(g))throw Error('Grid must be an object.');
    if (!Number.isInteger(g.width)||!Number.isInteger(g.height)||g.width<1||g.height<1||g.width*g.height>MAX_GRID_CELLS) throw Error(`A regular grid requires positive dimensions and at most ${MAX_GRID_CELLS} cells.`);
    if (![g.west,g.north,g.dx,g.dy].every(finite)||g.dx<=0||g.dy<=0||g.dx>5||g.dy>5) throw Error('Grid requires finite north-up coordinates and positive cell sizes of at most 5 degrees.');
    validateBounds(gridBounds(g));
    let minWidth=Infinity;
    for(let x=0;x<g.width;x++){const w=g.west+x*g.dx,e=g.west+(x+1)*g.dx;if(!(e>w))throw Error('Native cell bounds must remain representable at floating-point precision.');minWidth=Math.min(minWidth,e-w);}
    for(let y=0;y<g.height;y++)validateBounds([g.west,g.north-(y+1)*g.dy,g.west+minWidth,g.north-y*g.dy]);
    if (!Array.isArray(g.values)||g.values.length!==g.width*g.height) throw Error('Grid values must be a row-major array matching its dimensions.');
    let sum=0;
    for (const value of g.values) {if(value!==null&&(!finite(value)||value<0))throw Error('Grid values must be nonnegative finite counts or null NoData.');sum+=value||0;}
    if(!finite(sum))throw Error('Grid population sum exceeds finite numeric range.');
    if(Object.hasOwn(layer,'cells'))throw Error('Provide either a regular grid or rectangular cells.');
    return layer;
  }
  if (!Array.isArray(layer.cells) || !layer.cells.length || layer.cells.length>2000) throw Error('A layer needs between 1 and 2000 cells.');
  layer.cells.forEach((cell,i)=>{
    const b=validateBounds(cell.bounds);
    if (b[2]-b[0]>5 || b[3]-b[1]>5) throw Error('Each cell may span at most 5 degrees in either direction.');
    if (!finite(cell.population) || cell.population<0) throw Error('Cell populations must be finite, nonnegative counts; omit NoData cells.');
    for (const previous of layer.cells.slice(0,i)) {
      const c=intersection(b,previous.bounds);
      if (c) throw Error('Cells may touch at edges but must not overlap.');
    }
  });
  if (!finite(layer.cells.reduce((sum,c)=>sum+c.population,0))) throw Error('Layer population sum exceeds finite numeric range.');
  return layer;
}
function validateJSONMetadata(value,depth=0,ancestors=new Set()) {
  if(depth>64)throw Error('Metadata nesting must not exceed 64 levels.');
  if(value===null || typeof value==='boolean')return;
  if(typeof value==='string'){
    for(const char of value){const code=char.codePointAt(0);if(!(code===9||code===10||code===13||(code>=0x20&&code<=0xd7ff)||(code>=0xe000&&code<=0xfffd)||(code>=0x10000&&code<=0x10ffff)))throw Error('Metadata strings and keys must contain only XML-representable Unicode characters.');}
    return;
  }
  if(typeof value==='number'){if(!finite(value))throw Error('Metadata numbers must be finite JSON-safe numbers.');return;}
  if(typeof value!=='object' || (!Array.isArray(value)&&Object.getPrototypeOf(value)!==Object.prototype&&Object.getPrototypeOf(value)!==null))throw Error('Metadata must contain only JSON objects, arrays, strings, finite numbers, booleans, or null.');
  if(ancestors.has(value))throw Error('Metadata must not contain circular references.');
  ancestors.add(value);
  for(const [key,child] of Object.entries(value)){validateJSONMetadata(key,depth+1,ancestors);validateJSONMetadata(child,depth+1,ancestors);}
  ancestors.delete(value);
}
export function importGeoJSON(document) {
  if (!document || document.type!=='FeatureCollection' || 'crs' in document) throw Error('Import a WGS84 GeoJSON FeatureCollection without a crs override.');
  if (!Array.isArray(document.features) || !document.features.length || document.features.length>2000) throw Error('Import requires between 1 and 2000 features.');
  const cells=document.features.map(feature=>{
    const geometry=feature?.geometry, rings=geometry?.coordinates;
    if (feature?.type!=='Feature' || geometry?.type!=='Polygon' || !Array.isArray(rings) || rings.length!==1) throw Error('Only rectangular Polygon cells without holes are supported.');
    const r=rings[0];
    if (!Array.isArray(r) || r.length!==5 || r.some(p=>!Array.isArray(p) || p.length!==2 || !p.every(finite))) throw Error('A rectangle needs five [longitude, latitude] positions, including closure.');
    const bounds=validateBounds([Math.min(...r.map(p=>p[0])),Math.min(...r.map(p=>p[1])),Math.max(...r.map(p=>p[0])),Math.max(...r.map(p=>p[1]))]);
    const [w,s,e,n]=bounds, corners=new Set([[w,s],[e,s],[e,n],[w,n]].map(p=>JSON.stringify(p)));
    if (JSON.stringify(r[0])!==JSON.stringify(r[4]) || new Set(r.slice(0,4).map(p=>JSON.stringify(p))).size!==4 || r.slice(0,4).some((p,i)=>!corners.has(JSON.stringify(p)) || (p[0]!==r[i+1][0] && p[1]!==r[i+1][1]))) throw Error('Cells must be closed, axis-aligned rectangles with no crossing edges.');
    return {bounds,population:feature.properties?.population};
  });
  return validateLayer({metadata:document.metadata,cells});
}
export function compare(layers,bounds) {
  validateBounds(bounds);
  return layers.map(layer=>{
    let total=0,covered=0,intersected=0;
    for (const cell of iterateCells(layer,bounds)) {
      const overlap=intersection(bounds,cell.bounds);
      if (overlap) { const a=area(overlap); total+=cell.population*Math.min(1,a/area(cell.bounds)); covered+=a; intersected++; }
    }
    const support=intersection(bounds,layerBounds(layer));
    return {metadata:structuredClone(layer.metadata),population:intersected?total:null,coverage:Math.min(1,covered/area(bounds)),intersected_cells:intersected,bounds:bounds.slice(),method:METHOD,grid:layer.grid?gridIdentity(layer.grid):null,prepared_coverage:support?Math.min(1,area(support)/area(bounds)):0};
  });
}
export function gridBounds(g){return [g.west,g.north-g.height*g.dy,g.west+g.width*g.dx,g.north];}
export function gridIdentity(g){return Object.fromEntries(['width','height','west','north','dx','dy'].map(key=>[key,g[key]]));}
export function layerBounds(layer){
  if(layer.grid)return gridBounds(layer.grid);
  return layer.cells.reduce((b,c)=>[Math.min(b[0],c.bounds[0]),Math.min(b[1],c.bounds[1]),Math.max(b[2],c.bounds[2]),Math.max(b[3],c.bounds[3])],[Infinity,Infinity,-Infinity,-Infinity]);
}
export function nativeWindow(g,bounds){
  return [Math.max(0,Math.min(g.width,Math.floor((bounds[0]-g.west)/g.dx))),Math.max(0,Math.min(g.height,Math.floor((g.north-bounds[3])/g.dy))),Math.max(0,Math.min(g.width,Math.ceil((bounds[2]-g.west)/g.dx))),Math.max(0,Math.min(g.height,Math.ceil((g.north-bounds[1])/g.dy)))];
}
// Planning uses catalog geometry/block tables, never population values.
export function planWindow(source,bounds){
  validateBounds(bounds);
  if(!intersection(bounds,gridBounds(source.grid)))throw Error('Study bounds lie outside this source.');
  const g=source.grid,l=source.layout,[x0,y0,x1,y1]=nativeWindow(g,bounds),width=x1-x0,height=y1-y0;
  if(width<=0||height<=0)throw Error('Study bounds lie outside this source.');
  const cells=width*height;
  if(cells>MAX_GRID_CELLS)throw Error(`Selected native window exceeds ${MAX_GRID_CELLS} cells. Choose smaller bounds; no resampling is performed.`);
  if(width>32767||height>32767)throw Error('Native display axes are limited to 32767 pixels. Choose smaller bounds.');
  const bw=l.block_width,bh=l.block_height,across=Math.ceil(g.width/bw),indices=[];
  if(![bw,bh].every(v=>Number.isSafeInteger(v)&&v>0)||bw*bh>16777216)throw Error('Unsupported native TIFF block dimensions.');
  let compressed=0,decoded=0;
  for(let by=Math.floor(y0/bh);by<Math.ceil(y1/bh);by++)for(let bx=Math.floor(x0/bw);bx<Math.ceil(x1/bw);bx++){
    const index=by*across+bx,size=Number(l.block_byte_counts[index]),offset=Number(l.block_offsets[index]);
    if(!Number.isSafeInteger(size)||!Number.isSafeInteger(offset)||size<0||offset<0||offset+size>source.asset_size||(size===0)!==(offset===0))throw Error('TIFF blocks exceed declared asset bounds.');
    indices.push(index);compressed+=size;
    decoded+=bw*(l.tiled?bh:Math.min(bh,g.height-by*bh))*l.bits_per_sample/8;
  }
  if(compressed>64*1024*1024||decoded>128*1024*1024)throw Error('Selected blocks exceed 64 MiB compressed / 128 MiB decoded limits. Choose smaller bounds or a tiled excerpt.');
  return {native_window:[x0,y0,x1,y1],width,height,cells,output_bytes:cells*8,blocks:indices.length,compressed_bytes:compressed,decoded_bytes:decoded,layout:l.tiled?'tiles':'full-width strips',partial_coverage:!bounds.every((v,i)=>i<2?v>=gridBounds(g)[i]:v<=gridBounds(g)[i])};
}

export class WindowCache {
  constructor(maxBytes=16*1024*1024,maxEntries=16){this.maxBytes=maxBytes;this.maxEntries=maxEntries;this.entries=new Map();this.bytes=0;}
  get(key){const entry=this.entries.get(key);if(!entry)return null;this.entries.delete(key);this.entries.set(key,entry);return entry.value;}
  set(key,value){const size=value.grid.values.length*8;if(this.entries.has(key)){this.bytes-=this.entries.get(key).size;this.entries.delete(key);}if(size>this.maxBytes)return;this.entries.set(key,{value,size});this.bytes+=size;while(this.bytes>this.maxBytes||this.entries.size>this.maxEntries){const first=this.entries.keys().next().value;this.bytes-=this.entries.get(first).size;this.entries.delete(first);}}
}
export function* iterateCells(layer,bounds=layerBounds(layer)){
  if(!layer.grid){yield* layer.cells;return;}
  const g=layer.grid,[x0,y0,x1,y1]=nativeWindow(g,bounds);
  for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++){
    const population=g.values[y*g.width+x];
    if(population!==null)yield {bounds:[g.west+x*g.dx,g.north-(y+1)*g.dy,g.west+(x+1)*g.dx,g.north-y*g.dy],population};
  }
}
export function inspectCell(layer,lon,lat){
  if(!layer.grid)return layer.cells.find(c=>lon>=c.bounds[0]&&lon<c.bounds[2]&&lat>c.bounds[1]&&lat<=c.bounds[3])||null;
  const g=layer.grid,[w,s,e,n]=gridBounds(g);
  if(!finite(lon)||!finite(lat)||lon<w||lon>=e||lat<=s||lat>n)return null;
  let x=Math.max(0,Math.min(g.width-1,Math.floor((lon-w)/g.dx))),y=Math.max(0,Math.min(g.height-1,Math.floor((n-lat)/g.dy)));
  // Quotients can round across exact grid lines; compare the actual stored-grid edges.
  while(x>0&&lon<g.west+x*g.dx)x--;
  while(x+1<g.width&&lon>=g.west+(x+1)*g.dx)x++;
  while(y>0&&lat>g.north-y*g.dy)y--;
  while(y+1<g.height&&lat<=g.north-(y+1)*g.dy)y++;
  return {bounds:[g.west+x*g.dx,g.north-(y+1)*g.dy,g.west+(x+1)*g.dx,g.north-y*g.dy],population:g.values[y*g.width+x],column:x,row:y};
}
export function exportCSV(results) {
  const fields=[...METADATA,'population','coverage','intersected_cells','bounds','method','grid','prepared_coverage','metadata_json'];
  const quote=value=>{
    let text=value===null?'':typeof value==='object'?JSON.stringify(value):String(value);
    if (/^\s*[=+\-@]/.test(text)) text="'"+text;
    return '"'+text.replaceAll('"','""')+'"';
  };
  return [fields,...results.map(r=>fields.map(k=>({...r.metadata,...r,metadata_json:r.metadata})[k]))].map(row=>row.map(quote).join(',')).join('\r\n')+'\r\n';
}
