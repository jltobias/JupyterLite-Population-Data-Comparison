import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const source=readFileSync(new URL('../viewer/analysis.js',import.meta.url),'utf8');
const a=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const example=JSON.parse(readFileSync(new URL('../data/import-example.geojson',import.meta.url),'utf8'));
const metadata=example.metadata;
const polar=[0,89.999999999,1,90];
assert.ok(a.area(polar)>0);
const layer=a.validateLayer({metadata,cells:[{bounds:polar,population:100}]});
assert.equal(a.compare([layer],polar)[0].population,100);
assert.equal(a.compare([layer],[0,polar[1],.5,90])[0].population,50);
assert.equal(a.compare([{metadata,cells:[{bounds:[0,0,1,1],population:1e-320}]}],[0,0,1,1])[0].population,1e-320);
assert.throws(()=>a.validateBounds([0,0,Number.MIN_VALUE,1]),/representable/);
const tiny={bounds:[0,0,1e-11,1],population:10};
assert.throws(()=>a.validateLayer({metadata,cells:[tiny,structuredClone(tiny)]}),/overlap/);
for(const value of [JSON.parse('1e400'),NaN,'control\u0000','control\u000b','noncharacter\ufffe','surrogate\ud800']){
  const document=structuredClone(example);document.metadata.optional={nested:[value]};
  assert.throws(()=>a.importGeoJSON(document),/Metadata/);
}
const badKey=structuredClone(example);badKey.metadata['bad\u0000key']='value';
assert.throws(()=>a.importGeoJSON(badKey),/Metadata/);
const valid=structuredClone(example);
valid.metadata.optional={toString:'provider value',nested:[null,true,4.5,'Valid Unicode: 🌍']};
assert.deepEqual(a.importGeoJSON(valid).metadata.optional,valid.metadata.optional);
const result=a.compare([a.importGeoJSON(valid)],[120.1,14.1,120.3,14.3])[0];
assert.ok(Math.abs(result.population-400)<1e-7);
assert.ok(a.exportCSV([result]).includes('provider value'));
console.log('JavaScript numerical and metadata regressions: PASS');
const data=JSON.parse(readFileSync(new URL('../data/population.json',import.meta.url),'utf8'));
const oracle=JSON.parse(readFileSync(new URL('../data/real/independent_oracle.json',import.meta.url),'utf8'));
const real=a.compare(data.layers,data.default_aoi);
for(let i=0;i<data.layers.length;i++){
  const layer=a.validateLayer(data.layers[i]),expected=oracle.sources[layer.metadata.id],result=real[i];
  assert.equal(layer.metadata.synthetic,false);
  assert.equal(layer.grid.values.filter(v=>v!==null).length,expected.valid_cells);
  assert.ok(Math.abs(result.population-expected.aoi_population)<.0001);
  assert.ok(Math.abs(result.coverage-Math.min(1,expected.aoi_coverage))<1e-10);
  assert.equal(result.intersected_cells,expected.aoi_intersected_cells);
  assert.ok(Math.abs(a.compare([layer],a.layerBounds(layer))[0].population-expected.native_sum)<.001);
}
const compact={metadata,grid:{width:2,height:2,west:3,north:7,dx:.1,dy:.1,values:[0,null,1,2]}};
a.validateLayer(compact);
assert.equal(a.inspectCell(compact,3.05,6.95).population,0);
assert.equal(a.inspectCell(compact,3.15,6.95).population,null);
for(const change of [l=>l.cells=null,l=>l.grid=null,l=>l.grid.width=true,l=>l.grid.width=262145,l=>l.grid.values=[1],l=>l.grid.values=[false,null,1,2],l=>l.grid.values=[0,-1,1,2],l=>l.grid.values=[0,Infinity,1,2],l=>Object.assign(l.grid,{west:100,dx:1e-14}),l=>Object.assign(l.grid,{north:80,dy:1e-14})]){
  const layer=structuredClone(compact);change(layer);assert.throws(()=>a.validateLayer(layer));
}
console.log('JavaScript real-source oracle, masks, native windows and grid rejections: PASS');
for(const layer of [compact,...data.layers]){
  const g=layer.grid,edgeX=g.west+g.dx,edgeY=g.north-g.dy;
  const second=a.inspectCell(layer,g.west+g.dx/2,g.north-1.5*g.dy);
  assert.equal(second.row,1);assert.equal(second.column,0);assert.equal(second.population,g.values[g.width]);
  const internal=a.inspectCell(layer,edgeX,edgeY);
  assert.equal(internal.row,1);assert.equal(internal.column,1);
  assert.deepEqual(internal.bounds,[edgeX,g.north-2*g.dy,g.west+2*g.dx,edgeY]);
  assert.equal(a.inspectCell(layer,g.west,g.north).row,0);
  const [w,s,e,n]=a.gridBounds(g);
  for(const [lon,lat] of [[e,n],[w,s],[w-g.dx/100,n],[w,n+g.dy/100],[e+g.dx/100,n],[w,s-g.dy/100]])assert.equal(a.inspectCell(layer,lon,lat),null);
}
console.log('Native inspection second rows, exact edges and geographic half-open bounds: PASS');

// Independent spherical-area fixtures distinguish area weighting from pixel ranks.
const referenceArea=([w,s,e,n])=>6371.0088**2*(e-w)*Math.PI/180*(Math.sin(n*Math.PI/180)-Math.sin(s*Math.PI/180));
const densityCell=(bounds,value)=>({bounds,population:value*referenceArea(bounds)});
const scope=[0,0,1,1];
const weighted={metadata:{id:'weighted'},cells:[
  densityCell([0,0,.35,1],10),densityCell([.35,0,.45,1],20),densityCell([.45,0,.55,1],30),densityCell([.55,0,.65,1],40),densityCell([.65,0,1,1],50)
]};
const near=(actual,expected)=>assert.ok(Math.abs(actual-expected)<1e-9,`${actual} != ${expected}`);
const shared=a.classifyDensity([weighted],scope);
shared.thresholds.forEach((v,i)=>near(v,[10,20,40,50][i]));
assert.deepEqual(a.DENSITY_COLORS,['#ffffd4','#fed98e','#fe9929','#d95f0e','#993404']);
const subdivided=structuredClone(weighted);subdivided.metadata.id='fine';
subdivided.cells=weighted.cells.flatMap(cell=>{
  const [w,s,e,n]=cell.bounds,value=cell.population/referenceArea(cell.bounds);
  return Array.from({length:10},(_,i)=>densityCell([w+(e-w)*i/10,s,w+(e-w)*(i+1)/10,n],value));
});
a.classifyDensity([subdivided],scope).thresholds.forEach((v,i)=>near(v,shared.thresholds[i]));
assert.deepEqual(a.classifyDensity([weighted,weighted],scope),shared);
const coarse={metadata:{id:'coarse'},cells:[densityCell(scope,100)]};
const fine={metadata:{id:'fine-low'},cells:Array.from({length:100},(_,i)=>densityCell([i/100,0,(i+1)/100,1],1))};
a.classifyDensity([fine,coarse],scope).thresholds.forEach((v,i)=>near(v,[1,1,100,100][i]));
const equalArea={metadata:{id:'equal-area'},cells:Array.from({length:5},(_,i)=>densityCell([i,0,i+1,1],i+1))};
a.classifyDensity([equalArea],[0,0,5,1]).thresholds.forEach((v,i)=>near(v,i+1));
const equatorial={metadata:{id:'equatorial'},cells:[densityCell(scope,10)]};
const highLatitude={metadata:{id:'high-latitude'},cells:[densityCell(scope,0),densityCell([0,60,1,61],100)]};
const latitudeClasses=a.classifyDensity([equatorial,highLatitude],[0,0,1,61]);
latitudeClasses.thresholds.forEach((v,i)=>near(v,[10,10,10,100][i]));
assert.deepEqual(a.classifyDensity([highLatitude,equatorial],[0,0,1,61]).thresholds,latitudeClasses.thresholds);
const pair={metadata:{id:'pair'},cells:[densityCell([0,0,.5,1],10),densityCell([.5,0,1,1],100)]};
a.classifyDensity([pair],[.45,0,1,1]).thresholds.forEach(v=>near(v,100));
const tied={metadata:{id:'tied'},cells:[densityCell(scope,25)]};
const ties=a.classifyDensity([tied],scope);
assert.ok(ties.thresholds.every(v=>v===ties.thresholds[0]));
assert.equal(a.densityColor(ties.thresholds[0],ties),a.DENSITY_COLORS[0]);
const exact={thresholds:[10,20,30,40]};
for(const [value,color] of [[0,a.ZERO_DENSITY_COLOR],[1,a.DENSITY_COLORS[0]],[10,a.DENSITY_COLORS[0]],[10.001,a.DENSITY_COLORS[1]],[20,a.DENSITY_COLORS[1]],[30,a.DENSITY_COLORS[2]],[40,a.DENSITY_COLORS[3]],[40.001,a.DENSITY_COLORS[4]],[null,null]])assert.equal(a.densityColor(value,exact),color);
assert.deepEqual(a.classifyDensity([compact],[-1,-1,0,0]).thresholds,[]);
const empty={metadata:{id:'empty'},grid:{width:2,height:1,west:0,north:1,dx:.5,dy:1,values:[0,null]}};
assert.deepEqual(a.classifyDensity([empty],scope).thresholds,[]);
assert.equal(a.densityColor(1,a.classifyDensity([],scope)),a.DENSITY_COLORS[0]);
assert.equal(a.densityColor(0,a.classifyDensity([],scope)),a.ZERO_DENSITY_COLOR);
const originalCounts=structuredClone(data.layers.map(layer=>layer.grid.values));
const realClasses=a.classifyDensity(data.layers,data.default_aoi);
assert.equal(realClasses.thresholds.length,4);
assert.ok(realClasses.thresholds.every((value,i)=>value>0&&(i===0||value>=realClasses.thresholds[i-1])));
assert.deepEqual(data.layers.map(layer=>layer.grid.values),originalCounts);
assert.throws(()=>a.densityColor(Infinity,exact),/finite/);
for(const [cell,expected] of [[{bounds:[0,0,5,5],population:Number.MIN_VALUE},Number.MIN_VALUE],[{bounds:[0,0,1e-100,1],population:1e300},Number.MAX_VALUE]]){
  const extreme=a.validateLayer({metadata,cells:[cell]});
  const native=cell.population,display=a.classifyDensity([extreme],cell.bounds);
  assert.equal(a.cellDensity(native,cell.bounds),expected);
  assert.ok(display.thresholds.every(value=>value===expected));
  assert.notEqual(a.densityColor(expected,display),a.ZERO_DENSITY_COLOR);
  assert.equal(a.compare([extreme],cell.bounds)[0].population,native);
  assert.ok(JSON.stringify(display));
}
console.log('Shared area-weighted density quantiles, subdivision, clipping, ties, palette and zero/NoData: PASS');
