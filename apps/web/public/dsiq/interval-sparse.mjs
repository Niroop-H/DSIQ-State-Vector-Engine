// Incremental exact-support state evolution. No magnitude pruning or fixture IDs.
import {fixedMatrix,Z,O,iz,ca,cm,cj,cn,zero,timesI,result} from './fixed-interval.mjs';
import {operands} from './interval-product.mjs';
import {nextUp} from './certified-factor.mjs';
export class SparseBoundary extends Error {}
const SCALE=1n<<192n;
const center=a=>{const m=(a[0]+a[1])/2n;return [m,m]};
const radius=a=>a[1]-a[0]; // conservative L1 radius in grid units
const widen=(a,r)=>[a[0]-r,a[1]+r];
const swap=(x,t,c)=>Boolean(x&t)===Boolean(x&c)?x:x^t^c;
export function sparsePlan(n,gates,opts){
 const unit=1024+Math.ceil(n/8)*4, cap=Math.min(8192,opts.maxNodes??8192,Math.floor(opts.maxBytes/(2*unit)));if(cap<1)throw new SparseBoundary('Sparse coefficient budget');
 let support=new Set([0n]),peak=1,work=0;
 for(const g of gates){operands(n,g);if(g.piTheta||g.piPhi||g.piLambda)throw new SparseBoundary('Symbolic rational angles require symbolic execution');const t=1n<<BigInt(g.q),c=g.controls.length?1n<<BigInt(g.controls[0]):0n;const m=g.name==='swap'?null:fixedMatrix(g),mask=m?.map(x=>!zero(x)),out=new Set();
  work+=support.size*4;if(work>opts.maxWork/4)throw new SparseBoundary('Sparse support planning work budget');
  for(const x of support){if(!m){out.add(swap(x,t,c));continue}if(c&&!(x&c)){out.add(x);continue}const j=x&t?1:0;if(mask[j])out.add(x&~t);if(mask[2+j])out.add(x|t);if(out.size>cap)throw new SparseBoundary(`Sparse support estimate exceeds coefficient cap ${cap}`)}
  support=out;peak=Math.max(peak,out.size);
 }
 return {cap,peak,work,unit};
}
export class IntervalSparse {
 constructor(n,gates,opts){this.n=n;this.gates=gates;this.plan=sparsePlan(n,gates,opts);this.mode='interval-sparse-support';this.state=new Map([[0n,O]]);this.maxWork=opts.maxWork;this.work=this.plan.work;this.operations=0;this.peak=1;this.error=0n;}
 charge(k){if(this.work+k>this.maxWork)throw new SparseBoundary(`Sparse work budget: ${this.work+k}>${this.maxWork}`);this.work+=k;}
 apply(g){if(g!==this.gates[this.operations])throw Error('Sparse gate sequence differs from plan');const t=1n<<BigInt(g.q),c=g.controls.length?1n<<BigInt(g.controls[0]):0n,m=g.name==='swap'?null:fixedMatrix(g),mask=m?.map(x=>!zero(x));this.charge(this.state.size*16);const out=new Map();const put=(x,v)=>{if(zero(v))return;const w=out.has(x)?ca(out.get(x),v):v;if(zero(w))out.delete(x);else out.set(x,w);};
 for(const [x,a] of this.state){if(!m){put(swap(x,t,c),a);continue}if(c&&!(x&c)){put(x,a);continue}const j=x&t?1:0;if(mask[j])put(x&~t,cm(m[j],a));if(mask[2+j])put(x|t,cm(m[2+j],a));}
 if(out.size>this.plan.cap)throw new SparseBoundary('Sparse coefficient cap exceeded');// The physical gate is exactly unitary, so the preceding L2 error is
 // unchanged. From a point state, every local interval encloses the new
 // point evolution. Sum component radii (L1 dominates L2), then recenter.
 // This avoids dependency wrapping without resetting physical norm or
 // dropping an unaccounted coefficient.
 let delta=0n;for(const [x,v] of out){delta+=radius(v[0])+radius(v[1]);const z=[center(v[0]),center(v[1])];if(zero(z))out.delete(x);else out.set(x,z);}
 this.error+=delta;if(this.error>=SCALE)throw new SparseBoundary('Sparse accumulated state error exceeds one');this.state=out;this.peak=Math.max(this.peak,out.size);this.operations++;
 }
 amplitude(bits){if(typeof bits!=='string'||bits.length!==this.n||!/^[01]+$/.test(bits))throw Error('Invalid sparse bitstring');this.charge(1);const v=this.state.get(BigInt('0b'+bits))??Z;return result([widen(v[0],this.error),widen(v[1],this.error)]);}
 expectation(p){if(typeof p!=='string'||p.length!==this.n||!/^[IXYZ]+$/.test(p))throw Error('Invalid sparse Pauli');let flip=0n,phase=0n,y=0;for(let q=0;q<this.n;q++){const c=p[this.n-1-q],b=1n<<BigInt(q);if(c==='X'||c==='Y')flip|=b;if(c==='Z'||c==='Y')phase|=b;if(c==='Y')y++;}this.charge(this.state.size*(this.n+8));let s=Z;for(const [x,a] of this.state){const b=this.state.get(x^flip);if(!b)continue;let v=cm(cj(b),a);for(let j=0;j<y%4;j++)v=timesI(v);let z=x&phase,k=0;while(z){z&=z-1n;k^=1;}s=ca(s,k?cn(v):v);}// ||psi||=1, ||center||<=1+e, so for any Pauli P with ||P||=1,
 // |<psi|P|psi>-<center|P|center>| <= (2+e)e <= 3e (e<1).
 return result([widen(s[0],3n*this.error),iz]);}
 // Exact integer weights of the represented fixed-point state. Sampling
 // probabilities are normalized explicitly; numerical queries never are.
 // The normalized center's measurement TV error is at most 2*stateL2Error.
 distribution(){const outcomes=[];let total=0n;this.charge(this.state.size*4);for(const [x,v] of this.state){const w=v[0][0]**2n+v[1][0]**2n;if(w>0n){total+=w;outcomes.push({bits:x.toString(2).padStart(this.n,'0'),cumulative:total});}}if(total===0n)throw new SparseBoundary('Zero sampling weight');return {outcomes,total,tvUpperBound:this.error===0n?0:Math.min(1,nextUp(Number(2n*this.error)/2**192))};}
 norm(){return this.expectation('I'.repeat(this.n));}
 stats(){return {mode:this.mode,qubits:this.n,gates:this.operations,support:this.state.size,peakSupport:this.peak,plannedSupport:this.plan.peak,estimatedCoefficientBytes:2*this.peak*this.plan.unit,work:this.work,stateL2ErrorUpperBound:this.error===0n?0:nextUp(Number(this.error)/2**192),precision:'192-bit point evolution plus outward global L2 error, exact support only'};}
}
