import assert from 'node:assert/strict';
import {FactorDSIQ} from '../apps/web/public/dsiq/factor.mjs';
import {executeAdaptive} from '../apps/web/public/dsiq/adaptive.mjs';
import {complementSchedule} from '../apps/web/public/dsiq/complement.mjs';

for(const n of [8,9,10]){
  const gates=Array.from({length:n},(_,q)=>({name:'h',q:n-1-q,controls:[]}));
  for(let layer=0;layer<3;layer++){
    for(let i=0;i<n+1;i++){
      const q=i%n,c=(q+1)%n;
      const cx={name:'cx',q,controls:[c]};
      gates.push(cx,{name:'rz',q,theta:layer===1?0.17*q:-0.37,controls:[]},cx);
    }
    for(let q=0;q<n;q++)gates.push({name:'rx',q,controls:[],theta:0.19*(q+1)});
  }
  // Move independent gates across each other, as a DAG topological sort may.
  for (let pass=0;pass<3;pass++) for(let i=0;i+1<gates.length;i++){
    const a=gates[i], b=gates[i+1], wires=[a.q,...a.controls];
    if (![b.q,...b.controls].some(q=>wires.includes(q))) {
      gates[i]=b; gates[i+1]=a;
    }
  }
  for(const gate of gates) if(gate.name==='rz') gate.theta+=19;
  assert.ok(complementSchedule(n,gates));
  assert.ok(!complementSchedule(n,[...gates,{name:'z',q:0,controls:[]}]));
  const ref=new FactorDSIQ(n,gates);
  for(const gate of gates) ref.apply(gate);
  const it=executeAdaptive(n,gates);let step;
  do{step=it.next()}while(!step.done);
  assert.ok(step.value.denseKernel);
  for(let i=0;i<2**n;i++){
    const bits=i.toString(2).padStart(n,'0');
    const a=step.value.amplitude(bits), b=ref.amplitude(bits);
    assert.ok(Math.hypot(a.real-b.real,a.imag-b.imag)<1e-13);
  }
}
