import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {PhaseProductDSIQ as P} from '../apps/web/public/dsiq/phase-product.mjs';
import {ScientificDSIQ as D} from '../apps/web/public/dsiq/scientific.mjs';
import {rng} from '../apps/web/public/dsiq/worker.mjs';
const gate=(name,q,controls=[],extra={})=>({name,q,controls,...extra});
const pg=(q,c,num,den)=>gate('cp',q,[c],{theta:Math.PI*Number(num)/Number(den),piTheta:[String(num),String(den)]});
const near=(a,b,t=1e-12)=>assert.ok(Math.abs(a-b)<=t,`${a} vs ${b}`);
export function qftGates(n){const gs=[];for(let q=n-1;q>=0;q--){gs.push(gate('h',q));for(let c=q-1;c>=0;c--)gs.push(pg(q,c,1n,1n<<BigInt(q-c)))}for(let q=0;q<Math.floor(n/2);q++)gs.push(gate('swap',n-1-q,[q]));return gs}
export function inverse(gs){return [...gs].reverse().map(g=>g.piTheta?{...g,theta:-g.theta,piTheta:[String(-BigInt(g.piTheta[0])),g.piTheta[1]]}:g)}
export function qft100(n=100){const r=rng(1981),d=new P(n),x=Array.from({length:n},()=>r()<.5?'0':'1').join('');for(let q=0;q<n;q++)if(x[n-1-q]==='1')d.apply(gate('x',q));const gs=qftGates(n);for(const g of gs)d.apply(g);for(let i=0;i<200;i++){const y=Array.from({length:n},()=>r()<.5?'0':'1').join(''),phase=2*Math.PI*Number((BigInt('0b'+x)*BigInt('0b'+y))% (1n<<BigInt(n)))/2**n,a=d.amplitude(y),m=2**(-n/2);near(a.real/m,Math.cos(phase));near(a.imag/m,Math.sin(phase))}for(const g of inverse(gs))d.apply(g);assert.equal(d.amplitude(x).real,1);assert.equal(d.sample(r),x);return {...d.stats(),forwardGates:gs.length,midpointQueries:200}}
export function qpe50(){const n=50,target=n,d=new P(n+1),value=BigInt('0b10101101100101100101011011001010010110110101011011'),mod=1n<<BigInt(n);d.apply(gate('x',target));for(let q=0;q<n;q++){d.apply(gate('h',q));d.apply(pg(target,q,(2n*value*(1n<<BigInt(q)))%(2n*mod),mod))}for(const g of inverse(qftGates(n)))d.apply(g);const bits='1'+value.toString(2).padStart(n,'0');assert.equal(d.amplitude(bits).real,1);assert.equal(d.sample(),bits);return {...d.stats(),phaseBits:50,readout:bits.slice(1)}}
if(process.argv[1]===fileURLToPath(import.meta.url)){console.log('QFT',qft100());console.log('QPE',qpe50())}
