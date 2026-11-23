import assert from 'node:assert/strict';
import {executeAdaptive} from '../apps/web/public/dsiq/adaptive.mjs';
import {FactorDSIQ} from '../apps/web/public/dsiq/factor.mjs';

const n=8;
const gates=Array.from({length:n-1},(_,i)=>({name:'cx',controls:[i],q:i+1}));
gates.push({name:'rz',q:0,theta:0.37,controls:[]});
for(let layer=0;layer<6;layer++){
  for(let q=0;q<n;q++){
    gates.push({name:layer%2?'ry':'h',theta:(q+1)*0.19,controls:[],q});
    gates.push({name:'rz',theta:(layer+1)*0.13,controls:[],q});
    gates.push({name:'cx',q,controls:[(q+3)%n]});
  }
}
const iterator=executeAdaptive(n,gates,32768,{shots:0,precision:'fp64'});
let step;
do {step=iterator.next();} while(!step.done);
const fused=step.value;
assert.ok(fused.denseKernel);
const plain=new FactorDSIQ(n,gates);
for(const gate of gates) plain.apply(gate);
for(let i=0;i<2**n;i++){
  const bits=i.toString(2).padStart(n,'0');
  const a=fused.amplitude(bits), b=plain.amplitude(bits);
  assert.ok(Math.hypot(a.real-b.real,a.imag-b.imag)<1e-13);
}
assert.ok(Math.abs(fused.norm()-1)<1e-12);
assert.ok(Math.abs(fused.expectation('XYZIIZXY')-plain.expectation('XYZIIZXY'))<1e-12);
const denied=new FactorDSIQ(n,gates,{fuse:true,maxBytes:2**n*16});
assert.equal(denied.denseKernel,undefined);
