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
