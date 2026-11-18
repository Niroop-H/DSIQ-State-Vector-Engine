// Bounded coherent product expansion. Interval arithmetic on every complex
// coefficient; no small-value pruning or circuit-family recognition.
import {fixedMatrix as certifiedMatrix,iz,Z,O,ca,cm,cj,cn,zero,timesI,local,result} from './fixed-interval.mjs';
export class ProductBoundary extends Error{}
const oneNames=new Set(['i','h','x','y','z','s','sdg','t','tdg','rx','ry','rz','p','sx','sy','u']),controlled=new Set(['cx','cy','cz','cp','crx','cry','crz','cu','csx']);
export function operands(n,g){const c=g.controls;if(!Number.isInteger(g.q)||g.q<0||g.q>=n||!Array.isArray(c)||new Set([g.q,...c]).size!==c.length+1||c.some(x=>!Number.isInteger(x)||x<0||x>=n))throw Error('Invalid product operands');if(!(oneNames.has(g.name)&&!c.length||(controlled.has(g.name)||g.name==='swap')&&c.length===1))throw new ProductBoundary('Product gate unsupported');if(['rx','ry','rz','p','u','crx','cry','crz','cp','cu'].includes(g.name)&&!Number.isFinite(g.theta)||['u','cu'].includes(g.name)&&(!Number.isFinite(g.phi)||!Number.isFinite(g.lambda)))throw Error('Invalid angle')}
export class IntervalProduct {
 constructor(n,{maxBytes=67108864,maxWork=50000000,maxTerms=32}={}){if(!Number.isInteger(n)||n<1||n>4096||!Number.isSafeInteger(maxBytes)||maxBytes<1||!Number.isSafeInteger(maxWork)||maxWork<1||!Number.isInteger(maxTerms)||maxTerms<1||maxTerms>32)throw Error('Invalid product configuration');this.n=n;this.terms=[Array.from({length:n},()=>[O,Z])];this.maxTerms=Math.min(maxTerms,Math.floor(maxBytes/(256*n)));if(this.maxTerms<1)throw new ProductBoundary('Product coefficient budget');this.maxWork=maxWork;this.work=0;this.peak=1;this.operations=0;this.mode='interval-coherent-product'}
 charge(k){this.work+=k;if(this.work>this.maxWork)throw new ProductBoundary('Product work budget')}
 apply(g){operands(this.n,g);const q=g.q,c=g.controls[0];this.charge(this.terms.length*16);if(g.name==='swap'){for(const b of this.terms)[b[q],b[c]]=[b[c],b[q]];this.operations++;return}
 let m;try{m=certifiedMatrix(g)}catch(e){throw new ProductBoundary(e.message)}const out=[];
 for(const b of this.terms){if(c===undefined){b[q]=local(b[q],m);out.push(b);continue}const v=b[c],t=b[q];if(zero(v[1])){out.push(b);continue}if(zero(v[0])){b[q]=local(t,m);out.push(b);continue}
 // Diagonal target known: controlled gate reduces to a local control phase.
 if(zero(m[1])&&zero(m[2])&&(zero(t[0])||zero(t[1]))){b[c]=[v[0],cm(v[1],m[zero(t[1])?0:3])];out.push(b);continue}
 // Exact coherent decomposition P0⊗I + P1⊗U.
 const a=b.slice(),d=b.slice();a[c]=[v[0],Z];d[c]=[Z,v[1]];d[q]=local(t,m);out.push(a,d);this.charge(this.n);if(out.length>this.maxTerms)throw new ProductBoundary('Coherent product term budget')}
 this.terms=out;this.peak=Math.max(this.peak,out.length);this.operations++}
 result(v){return result(v)}
 amplitude(bits){if(typeof bits!=='string'||bits.length!==this.n||!/^[01]+$/.test(bits))throw Error('Invalid bitstring');this.charge(this.n*this.terms.length);let s=Z;for(const b of this.terms){let a=O;for(let q=0;q<this.n;q++){a=cm(a,b[q][Number(bits[this.n-1-q])]);if(zero(a))break}s=ca(s,a)}return this.result(s)}
 expectation(p){if(typeof p!=='string'||p.length!==this.n||!/^[IXYZ]+$/.test(p))throw Error('Invalid Pauli');this.charge(this.n*this.terms.length**2*4);let s=Z;for(const a of this.terms)for(const b of this.terms){let r=O;for(let q=0;q<this.n;q++){const o=p[this.n-1-q],v=b[q],w=o==='I'?v:o==='X'?[v[1],v[0]]:o==='Y'?[cn(timesI(v[1])),timesI(v[0])]:[v[0],cn(v[1])];r=cm(r,ca(cm(cj(a[q][0]),w[0]),cm(cj(a[q][1]),w[1])));if(zero(r))break}s=ca(s,r)}return this.result([s[0],iz])}
 norm(){return this.expectation('I'.repeat(this.n))}
 stats(){return {mode:this.mode,qubits:this.n,gates:this.operations,terms:this.terms.length,peakTerms:this.peak,intervalPayloadBytes:256*this.n*this.terms.length,work:this.work,precision:'192-bit outward intervals, no deliberate truncation'}}
}
