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
