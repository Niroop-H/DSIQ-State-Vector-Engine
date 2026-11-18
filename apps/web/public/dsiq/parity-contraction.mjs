// MAH Quantum DSIQ: affine constraint elimination before numerical contraction.
// The computational bit after a monomial CX/X/SWAP is a binary affine form,
// not an additional independent summation variable. Endpoints impose linear
// constraints. Eliminating a pivot exactly changes coordinates of the path sum.
import {matrix} from './engine.mjs';
import {evaluateBinaryFactors,ContractionBudget} from './contraction.mjs';
const xor=(a,b)=>{const v=new Set(a.v);for(const x of b.v)v.has(x)?v.delete(x):v.add(x);return {v,c:a.c^b.c}};
const z=()=>({v:new Set(),c:0}),constant=c=>({v:new Set(),c}),variable=v=>({v:new Set([v]),c:0});
const zero=([r,i])=>r===0&&i===0;
const toggle=(a)=>({v:a.v,c:a.c^1});
const parity=(x)=>{x^=x>>>16;x^=x>>>8;x^=x>>>4;return (0x6996>>>(x&15))&1};
export function parityAmplitude(n,gates,bits,{maxBytes=67108864,maxWork=500000000,maxVariables=100000,ordering='degree'}={}){
 if(!Number.isInteger(n)||n<1||n>4096||!Array.isArray(gates)||typeof bits!=='string'||bits.length!==n||!/^[01]+$/.test(bits)||!Number.isSafeInteger(maxBytes)||maxBytes<16||!Number.isSafeInteger(maxWork)||maxWork<1||!Number.isSafeInteger(maxVariables)||maxVariables<1||!['degree','fill','search'].includes(ordering))throw Error('Invalid parity contraction configuration');
 const wires=Array.from({length:n},z),raw=[];let next=0,work=0,affineGates=0,pivots=0,maxExpression=0;
 const spend=k=>{if((work+=k)>maxWork)throw new ContractionBudget('Parity preprocessing work budget exceeded')};
 const fresh=()=>{if(next>=maxVariables)throw new ContractionBudget('Parity variable budget exceeded');return variable(next++)};
 const checked=e=>{maxExpression=Math.max(maxExpression,e.v.size);spend(e.v.size+1);return e};
 for(const g of gates){const {q,controls:c,name}=g;if(!Number.isInteger(q)||q<0||q>=n||!Array.isArray(c)||new Set([q,...c]).size!==c.length+1||c.some(v=>!Number.isInteger(v)||v<0||v>=n))throw Error('Invalid parity gate operands');const k=['mcx','mcry'].includes(name)?c.length:name==='ccx'?2:['cx','cy','cz','crx','cry','crz','cp','cu','csx','swap'].includes(name)?1:0;if(k!==c.length||(['mcx','mcry'].includes(name)&&!k)||(['rx','ry','rz','p','crx','cry','crz','cp','u','cu','mcry'].includes(name)&&!Number.isFinite(g.theta))||(['u','cu'].includes(name)&&(!Number.isFinite(g.phi)||!Number.isFinite(g.lambda))))throw Error('Invalid parity gate signature');spend(1);if(name==='swap'){[wires[q],wires[c[0]]]=[wires[c[0]],wires[q]];affineGates++;continue}const m=matrix(g);if(m.some(v=>!v.every(Number.isFinite)))throw Error('Nonfinite parity matrix');const before=wires[q],controls=c.map(i=>wires[i]),diag=zero(m[1])&&zero(m[2]),flip=zero(m[0])&&zero(m[3])&&c.length<=1;let after;
  if(diag)after=before;else if(flip){after=checked(c.length?xor(before,controls[0]):toggle(before));affineGates++}else after=fresh();
  wires[q]=after;
  // X and CX generate a bijective affine bit update with unit weight. Other
  // monomial matrices retain their phase factor. No branch is omitted.
  if(flip&&m[1][0]===1&&m[1][1]===0&&m[2][0]===1&&m[2][1]===0)continue;
  raw.push({expressions:[...controls,before,after],controls:c.length,m});
 }
 let equations=wires.map((w,q)=>checked(xor(w,constant(Number(bits[n-1-q])))));
 const impossible=()=>({real:0,imag:0,log2Magnitude:null,phase:0,mode:'parity-contraction',peakTensorBytes:0,work,eliminated:0,pivots,affineGates,pathVariables:next,maxExpression});
 // Keep the most local substitutions local. Sparsest equation first, followed
 // by its least-used eligible pivot. This is equivalent to GF(2) elimination.
 while(equations.length){equations.sort((a,b)=>a.v.size-b.v.size);const e=equations.shift();if(!e.v.size){if(e.c)return impossible();continue}const degree=new Map([...e.v].map(v=>[v,0]));for(const f of raw)for(const w of f.expressions){spend(w.v.size+1);for(const v of w.v)if(degree.has(v))degree.set(v,degree.get(v)+1)}let pivot=-1,score=Infinity;for(const [v,d] of degree)if(d<score||(d===score&&v>pivot)){pivot=v;score=d}const relation=xor(e,variable(pivot));for(const f of raw)f.expressions=f.expressions.map(w=>w.v.has(pivot)?checked(xor(w,e)):w);equations=equations.map(w=>w.v.has(pivot)?checked(xor(w,e)):w);if(relation.v.has(pivot))throw Error('Invalid affine pivot');pivots++;spend(raw.length+equations.length)}
 const present=new Set(),factors=raw.map(f=>{const vars=[...new Set(f.expressions.flatMap(e=>[...e.v]))].sort((a,b)=>a-b);if(vars.length>24)throw new ContractionBudget('Parity factor arity exceeds 24');const idx=new Map(vars.map((v,i)=>[v,i])),masks=f.expressions.map(e=>[...e.v].reduce((s,v)=>s|(1<<idx.get(v)),0));for(const v of vars)present.add(v);return {vars,value(x){const bit=j=>parity(masks[j]&x)^f.expressions[j].c;let active=true;for(let j=0;j<f.controls;j++)if(!bit(j)){active=false;break}const col=bit(f.controls),row=bit(f.controls+1);return active?f.m[2*row+col]:[+(row===col),0]}}});
 // Each remaining independent path variable must be summed even if its factor
 // becomes a constant. The compiled scopes retain all mentioned variables.
 if(present.size>next-pivots)throw Error('Invalid parity contraction rank');
 for(let j=0;j<next-pivots-present.size;j++)factors.push({vars:[],value:()=>[2,0]});
 if(work>=maxWork)throw new ContractionBudget('Parity preprocessing budget reached');const r=evaluateBinaryFactors(factors,{maxBytes,maxWork:maxWork-work,ordering});return {...r,work:r.work+work,mode:'parity-contraction',pathVariables:next,freeVariables:next-pivots,pivots,affineGates,maxExpression,preprocessWork:work}
}
