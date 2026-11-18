// MAH Quantum DSIQ: coherent sum of phase-decorated product terms.
// No truncation, zero tests are exact IEEE zeros. This is a bounded alternate
// representation, not a claim of efficient arbitrary universal simulation.
import {matrix} from './engine.mjs';
const O=[1,0],Z=[0,0],I=[0,1],N=[-1,0];
const add=(a,b)=>[a[0]+b[0],a[1]+b[1]],mul=(a,b)=>{const v=[a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0]];if(zero(v)&&!zero(a)&&!zero(b))throw new CoherentBudget('Float64 product underflow; use another representation');return v},neg=a=>[-a[0],-a[1]],conj=a=>[a[0],-a[1]],zero=a=>a[0]===0&&a[1]===0;
const clone=t=>({w:t.w,v:t.v.slice(),edges:new Set(t.edges)});
const id=(a,b,n)=>Math.min(a,b)*n+Math.max(a,b);
const transform=(v,m)=>[add(mul(m[0],v[0]),mul(m[1],v[1])),add(mul(m[2],v[0]),mul(m[3],v[1]))];
const finite=a=>a.every(Number.isFinite);
export class CoherentBudget extends Error{}
export class CoherentDSIQ {
 constructor(n,maxTerms=256,maxDifference=18){if(!Number.isInteger(n)||n<1||n>4096||!Number.isInteger(maxTerms)||maxTerms<1||maxTerms>4096||!Number.isInteger(maxDifference)||maxDifference<0||maxDifference>24)throw Error('Invalid coherent budget');this.n=n;this.maxTerms=maxTerms;this.maxDifference=maxDifference;this.terms=[{w:O,v:Array.from({length:n},()=>[O,Z]),edges:new Set()}];this.operations=0;this.peak=1;this.mode='coherent';}
 check(bits){if(typeof bits!=='string'||bits.length!==this.n||!/^[01]+$/.test(bits))throw Error('Invalid bitstring')}
 // Projection absorbs graph edges incident on fixed vertices into neighbor phases.
 fixed(t,q,b){const a=t.v[q][b];if(zero(a))return null;const r=clone(t);r.w=mul(r.w,a);r.v[q]=b?[Z,O]:[O,Z];for(const e of r.edges){const x=Math.floor(e/this.n),y=e%this.n;if(x===q||y===q){r.edges.delete(e);if(b){const k=x===q?y:x;r.v[k]=[r.v[k][0],neg(r.v[k][1])]}}}return r}
 local(t,q,m){if(zero(m[1])&&zero(m[2])){const r=clone(t);r.v[q]=transform(r.v[q],m);return [r]}let incident=false;for(const e of t.edges)if(Math.floor(e/this.n)===q||e%this.n===q){incident=true;break}if(!incident){const r=clone(t);r.v[q]=transform(r.v[q],m);return [r]}const out=[];for(const b of [0,1]){const r=this.fixed(t,q,b);if(r){r.v[q]=[m[b],m[2+b]];out.push(r)}}return out}
 apply(g){const {q,controls:c,name}=g;if(!Number.isInteger(q)||q<0||q>=this.n||!Array.isArray(c)||new Set([q,...c]).size!==c.length+1||c.some(k=>!Number.isInteger(k)||k<0||k>=this.n)||[g.theta??0,g.phi??0,g.lambda??0].some(x=>!Number.isFinite(x)))throw Error('Invalid gate');const expected=name==='ccx'?2:name==='mcx'?c.length:['cx','cz','cy','crx','cry','crz','cp','cu','csx','swap'].includes(name)?1:0;if(c.length!==expected||(name==='mcx'&&!c.length)||(['rx','ry','rz','p','u','crx','cry','crz','cp','cu'].includes(name)&&!Number.isFinite(g.theta))||(['u','cu'].includes(name)&&(!Number.isFinite(g.phi)||!Number.isFinite(g.lambda))))throw Error('Invalid gate signature');const m=name==='swap'?null:matrix(g),out=[];const append=r=>{if(r&&!zero(r.w)&&!r.v.some(v=>zero(v[0])&&zero(v[1]))){if(!finite(r.w)||r.v.some(v=>!finite(v[0])||!finite(v[1])))throw Error('Nonfinite coherent term');if(out.length>=this.maxTerms)throw new CoherentBudget('Coherent term budget exhausted');out.push(r)}};
 for(const t of this.terms){if(name==='swap'){const r=clone(t),a=c[0];[r.v[a],r.v[q]]=[r.v[q],r.v[a]];const perm=k=>k===a?q:k===q?a:k;r.edges=new Set([...r.edges].map(e=>id(perm(Math.floor(e/this.n)),perm(e%this.n),this.n)));append(r);continue}
 if(name==='cz'){const r=clone(t),e=id(q,c[0],this.n);if(r.edges.has(e))r.edges.delete(e);else r.edges.add(e);append(r);continue}
 if(!c.length){for(const r of this.local(t,q,m))append(r);continue}
 // If the controls are individually definite, no branch is needed.
 if(c.some(k=>zero(t.v[k][1]))){append(t);continue}
 if(c.every(k=>zero(t.v[k][0]))){for(const r of this.local(t,q,m))append(r);continue}
 // U_c = I + Pi_controls (U-I), keeping the contributions coherent.
 append(t);let r=t;for(const k of c){r=this.fixed(r,k,1);if(!r)break}if(r){const delta=[add(m[0],N),m[1],m[2],add(m[3],N)];for(const a of this.local(r,q,delta))append(a)}}
 this.terms=out;this.operations++;this.peak=Math.max(this.peak,out.length)}
 // Arbitrary small unitary, with row/column indices ordered by qubits (first=LSB).
 // Atomic operation: only commit the new term list if every row fits the budget.
 applyUnitary(qubits,M){const k=qubits.length,size=2**k;if(!Number.isInteger(k)||k<1||k>5||new Set(qubits).size!==k||qubits.some(q=>!Number.isInteger(q)||q<0||q>=this.n)||!Array.isArray(M)||M.length!==size*size||M.some(z=>!Array.isArray(z)||z.length!==2||!finite(z)))throw Error('Invalid custom matrix');
 for(let i=0;i<size;i++)for(let j=0;j<size;j++){let sum=Z;for(let r=0;r<size;r++)sum=add(sum,mul(conj(M[r*size+i]),M[r*size+j]));if(Math.hypot(sum[0]-(i===j?1:0),sum[1])>1e-12)throw Error('Custom matrix is not unitary within tolerance')}
 const out=[],set=new Set(qubits),emit=t=>{if(!zero(t.w)){if(out.length>=this.maxTerms)throw new CoherentBudget('Custom matrix exceeds term budget');out.push(t)}};
 for(const t of this.terms){let incident=false;for(const e of t.edges)if(set.has(Math.floor(e/this.n))||set.has(e%this.n)){incident=true;break}if(!incident){const inputs=[];for(let x=0;x<size;x++){let a=O;for(let i=0;i<k;i++)a=mul(a,t.v[qubits[i]][(x>>i)&1]);inputs.push(a)}for(let y=0;y<size;y++){let a=Z;for(let x=0;x<size;x++)a=add(a,mul(M[y*size+x],inputs[x]));if(zero(a))continue;const r=clone(t);r.w=mul(r.w,a);for(let i=0;i<k;i++)r.v[qubits[i]]=((y>>i)&1)?[Z,O]:[O,Z];emit(r)}}else{for(let x=0;x<size;x++){let r=t;for(let i=0;i<k&&r;i++)r=this.fixed(r,qubits[i],(x>>i)&1);if(!r)continue;for(let y=0;y<size;y++){const a=M[y*size+x];if(zero(a))continue;const u=clone(r);u.w=mul(u.w,a);for(let i=0;i<k;i++)u.v[qubits[i]]=((y>>i)&1)?[Z,O]:[O,Z];emit(u)}}}}
 this.terms=out;this.operations++;this.peak=Math.max(this.peak,out.length)
 }
 amplitude(bits){this.check(bits);const x=Array.from(bits).reverse().map(Number);let s=Z,cor=Z;for(const t of this.terms){let a=t.w;for(let q=0;q<this.n;q++)a=mul(a,t.v[q][x[q]]);let parity=0;for(const e of t.edges)parity^=x[Math.floor(e/this.n)]&x[e%this.n];if(parity)a=neg(a);const y=add(a,neg(cor)),v=add(s,y);cor=add(add(v,neg(s)),neg(y));s=v}const m=Math.hypot(...s);if(!finite(s))throw Error('Nonfinite amplitude');return {real:s[0],imag:s[1],log2Magnitude:m?Math.log2(m):null,phase:Math.atan2(s[1],s[0])}}
 // Exact contraction of graph differences. Equal quadratic forms cancel under
 // Pauli translation; unequal forms require bounded enumeration of active bits.
 overlap(other=this,p='I'.repeat(this.n),assign={}){if(other.n!==this.n||p.length!==this.n||!/^[IXYZ]+$/.test(p))throw Error('Invalid Pauli');for(const [q,b] of Object.entries(assign))if(!Number.isInteger(Number(q))||q<0||q>=this.n||(b!==0&&b!==1))throw Error('Invalid projection');const ops=[...p].reverse(),flip=ops.map(c=>c==='X'||c==='Y'?1:0);let sum=Z,cor=Z;
 for(const a of this.terms)for(const b of other.terms){const diff=new Set(a.edges),lin=Array(this.n).fill(0);let phase=0;for(const e of b.edges){if(diff.has(e))diff.delete(e);else diff.add(e);const x=Math.floor(e/this.n),y=e%this.n;lin[x]^=flip[y];lin[y]^=flip[x];phase^=flip[x]&flip[y]}
 const local=ops.map((op,q)=>[0,1].map(x=>{if(assign[q]!==undefined&&assign[q]!==x)return Z;let v=mul(conj(a.v[q][x]),b.v[q][x^flip[q]]);if(lin[q]&x)v=neg(v);if(op==='Z'&&x)v=neg(v);if(op==='Y')v=mul(v,x?I:[0,-1]);return v}));
 const active=[...new Set([...diff].flatMap(e=>[Math.floor(e/this.n),e%this.n]))];if(active.length>this.maxDifference)throw new CoherentBudget('Quadratic difference contraction budget exhausted');const set=new Set(active);let outside=mul(conj(a.w),b.w);if(phase)outside=neg(outside);for(let q=0;q<this.n;q++)if(!set.has(q))outside=mul(outside,add(...local[q]));const pos=new Map(active.map((q,i)=>[q,i]));const edges=[...diff].map(e=>[pos.get(Math.floor(e/this.n)),pos.get(e%this.n)]);let inside=Z;for(let k=0;k<2**active.length;k++){let v=O,parity=0;for(let j=0;j<active.length;j++)v=mul(v,local[active[j]][(k>>j)&1]);for(const [x,y] of edges)parity^=((k>>x)&(k>>y)&1);inside=add(inside,parity?neg(v):v)}const term=mul(outside,inside),y=add(term,neg(cor)),v=add(sum,y);cor=add(add(v,neg(sum)),neg(y));sum=v}if(!finite(sum))throw Error('Nonfinite contraction');return sum}
 norm(){return this.overlap()[0]}
 expectation(p){return this.overlap(this,p)[0]}
 probability(a={}){return this.overlap(this,'I'.repeat(this.n),a)[0]}
 sample(random=Math.random){if(this.terms.length===1){const t=this.terms[0];return t.v.map(v=>{const a=Math.hypot(...v[0])**2,b=Math.hypot(...v[1])**2,u=random();if(!(a+b>0)||!(u>=0&&u<1))throw Error('Invalid sampling distribution');return u*(a+b)<a?'0':'1'}).reverse().join('')}const out={};for(let q=0;q<this.n;q++){const a=this.probability({...out,[q]:0}),b=this.probability({...out,[q]:1}),u=random();if(a<0||b<0||!(a+b>0)||!(u>=0&&u<1))throw Error('Numerically invalid sampling distribution');out[q]=u*(a+b)<a?0:1}return Object.values(out).reverse().join('')}
 stats(){return {mode:this.mode,qubits:this.n,gates:this.operations,terms:this.terms.length,peakTerms:this.peak,termBudget:this.maxTerms,quadraticEdges:this.terms.reduce((s,t)=>s+t.edges.size,0),precision:'Float64, no deliberate truncation; non-scaled products may underflow'}}
}
