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
gates.push({name:'mcx',q:2,controls:[7,0,3]},{name:'ccx',q:0,controls:[1,6]});
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

for(const prepare of [[],[{name:'h',q:0,controls:[]},{name:'h',q:1,controls:[]}]]){
 const ops=[...prepare,{name:'cp',controls:[1],q:0,theta:0.37}];
 const it=executeAdaptive(2,ops);let result;do{result=it.next()}while(!result.done);
 if(!prepare.length)assert.equal(result.value.mode,'phase-product');
 const ref=new FactorDSIQ(2,ops);for(const gate of ops)ref.apply(gate);
 for(const bits of ['00','01','10','11']){
   const x=result.value.amplitude(bits),y=ref.amplitude(bits);
   assert.ok(Math.hypot(x.real-y.real,x.imag-y.imag)<1e-13);
 }
}
