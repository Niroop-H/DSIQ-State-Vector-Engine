import {readFileSync} from 'node:fs';
import {buildFrame} from '../apps/web/public/dsiq/frame-factor.mjs';
import {rng} from '../apps/web/public/dsiq/worker.mjs';
const n=Number(process.argv[2]||25),r=rng(18927351),gates=[];
if(!Number.isInteger(n)||n<1||n>63)throw Error('Invalid test width');
const push=(name,q,controls=[],theta=0)=>gates.push({name,q,controls,theta});
// Non-Clifford local evolution with multiple components, then a connected
// nonlocal Clifford frame spanning all physical wires. The dense oracle does
// NOT use that structure. No cancellation, no inverse or output template.
for(let q=0;q<n;q++){push('ry',q,[],.23+r()*1.7);push('rz',q,[],r()*2-1)}
for(let q=0;q+1<n;q+=2){push('cx',q+1,[q]);push('ry',q+1,[],r()*.8-.4)}
for(let q=0;q+1<n;q++)push('cx',q+1,[q]);
for(let q=0;q+2<n;q+=2)push('cz',q+2,[q]);
for(let q=0;q<n;q+=3)push('s',q);
if(n>1)push('swap',n-1,[0]);
let d=buildFrame(n,gates,{maxBytes:67108864}),frame=d.monomialDescriptor();frame.groups=frame.groups.map(({qs,a})=>({qs,a:Array.from(a)}));
const probes=[];for(let i=0;i<64;i++){const bits=Array.from({length:n},()=>r()<.5?'0':'1').join(''),a=d.amplitude(bits);probes.push({bits,real:a.real,imag:a.imag})}
console.log(JSON.stringify({n,gates,frame,probes,stats:d.stats(),norm:d.norm()}));
