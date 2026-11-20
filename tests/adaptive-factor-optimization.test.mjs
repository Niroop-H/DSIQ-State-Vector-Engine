import assert from 'node:assert/strict';
import {executeAdaptive} from '../apps/web/public/dsiq/adaptive.mjs';
import {FactorDSIQ,FactorBudget} from '../apps/web/public/dsiq/factor.mjs';
import {reference} from './factor.test.mjs';
import {rng} from '../apps/web/public/dsiq/worker.mjs';

const gate=(name,q,controls=[],theta=undefined)=>({name,q,controls,theta});
const close=(a,b,tol=1e-12)=>assert.ok(Math.abs(a-b)<=tol,`${a} != ${b} (tol ${tol})`);
const n=20,gs=[],oracle=[];
for(let off=0;off<n;off+=5){
  const block=[];
  for(let depth=0;depth<8;depth++){
    for(let q=0;q<5;q++)block.push(gate(['rx','ry','rz'][(depth+q)%3],q,[],(depth+q)*.031));
    for(let q=depth%2;q<4;q+=2)block.push(gate('cx',q+1,[q]));
  }
  oracle.push(reference(5,block));
  for(const g of block)gs.push({...g,q:g.q+off,controls:g.controls.map(q=>q+off)});
}
const start=performance.now();const iterator=executeAdaptive(n,gs,32768,{precision:'fp64',shots:256,query:'0'.repeat(n)});
let it=iterator.next();while(!it.done)it=iterator.next();const adaptive=it.value;
assert.equal(adaptive.mode,'factor-statevector','independent components should use factor evolution above 16 qubits');
assert.equal(adaptive.stats().factors,4);
assert.equal(adaptive.stats().coefficientBytes,2048);
const random=rng(99127);let maximum=0;
for(let k=0;k<256;k++){
  const bits=Array.from({length:n},()=>random()<.5?'0':'1').join('');
  let expectedRe=1,expectedIm=0;
  for(let j=0;j<4;j++){
    let idx=0;for(let q=0;q<5;q++)if(bits[n-1-(j*5+q)]==='1')idx|=1<<q;
    const [re,im]=oracle[j][idx];
    [expectedRe,expectedIm]=[expectedRe*re-expectedIm*im,expectedRe*im+expectedIm*re];
  }
  const got=adaptive.amplitude(bits);
  maximum=Math.max(maximum,Math.hypot(expectedRe-got.real,expectedIm-got.imag));
  assert.ok(Math.hypot(expectedRe-got.real,expectedIm-got.imag)<1e-12,`oracle mismatch on ${bits}`);
}
close(adaptive.norm(),1,1e-12);
const first=adaptive.sampler();
assert.equal(first,adaptive.sampler(),'CDF must be reused for a state not modified');
assert.throws(()=>adaptive.sampler(16),FactorBudget,'cached CDF must not bypass scratch allocation budget');
const seed=2712,rg=rng(seed),rh=rng(seed);
for(let i=0;i<512;i++)assert.equal(adaptive.sample(rg),first.sample(rh),'sample path must preserve seeded distribution and sequence');
assert.equal(adaptive.stats().samplingCDFBuilds,1);
assert.ok(adaptive.stats().samplingCacheHits>=513);
let delta=performance.now()-start;

// An in-place gate must invalidate the CDF. Compare with a transparent exact one-qubit state.
const d=new FactorDSIQ(1,[gate('x',0)],{maxBytes:1024});
assert.equal(d.sample(()=>0),'0');
assert.equal(d.stats().samplingCDFBuilds,1);
d.apply(gate('x',0));assert.equal(d.stats().samplingScratchBytes,0);
assert.equal(d.sample(()=>0),'1');assert.equal(d.stats().samplingCDFBuilds,2);
assert.equal(d.stats().samplingInvalidations,1);
const h=[[Math.SQRT1_2,0],[Math.SQRT1_2,0],[Math.SQRT1_2,0],[-Math.SQRT1_2,0]];
d.applyUnitary([0],h);
assert.equal(d.stats().samplingScratchBytes,0);
assert.equal(d.stats().samplingInvalidations,2);
close(d.amplitude('0').real,Math.SQRT1_2);
close(d.amplitude('1').real,-Math.SQRT1_2);
assert.equal(d.sample(()=>0),'0');assert.equal(d.sample(()=>.999999),'1');
assert.equal(d.stats().samplingCDFBuilds,3);

// A rejected edit must not corrupt probability tables.
const current=d.sampler();
assert.throws(()=>d.apply(gate('cx',0,[0])));
assert.equal(d.sampler(),current);

// Even a zero-angle gate invalidates a cache conservatively, preserving exact result.
d.apply(gate('rz',0,[],0));assert.notEqual(d.sampler(),current);
close(d.norm(),1);
console.log(JSON.stringify({status:'PASS',qubits:20,gates:gs.length,oracleAmplitudeQueries:256,maxAmplitudeError:maximum,estimatedElapsedMs:delta,cdfBuildsFor512Samples:adaptive.stats().samplingCDFBuilds,cdfCacheHits:adaptive.stats().samplingCacheHits,unitaryMutationInvalidation:true}));
