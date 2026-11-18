// MAH Quantum DSIQ: bounded variable elimination of the circuit's complex
// amplitude factor graph. All factors are evaluated; no truncation/sampling.
// Binary factor elimination for amplitudes, double-layer probabilities and observables.
import {matrix} from './engine.mjs';
import {createScaledAccumulator} from './scaled-replay.mjs';
import {planElimination} from './contraction-plan.mjs';
import {evaluateDyadicFactors} from './dyadic-contraction.mjs';
export class ContractionBudget extends Error{}
const zero=z=>z[0]===0&&z[1]===0;
function normalize(a){let m=0;for(let i=0;i<a.length;i++)m=Math.max(m,Math.abs(a[i]));if(!Number.isFinite(m))throw Error('Nonfinite contraction tensor');if(!m)return 0;const k=Math.min(1023,Math.floor(Math.log2(m))),s=2**k;for(let i=0;i<a.length;i++){const x=a[i];a[i]/=s;if(x!==0&&a[i]===0)throw new ContractionBudget('Tensor dynamic range exceeds Float64');}return k}
function validate(n,g){const {name,q,controls:c}=g;if(!Number.isInteger(q)||q<0||q>=n||!Array.isArray(c)||new Set([q,...c]).size!==c.length+1||c.some(v=>!Number.isInteger(v)||v<0||v>=n))throw Error('Invalid contraction operands');const k=['mcx','mcry'].includes(name)?c.length:name==='ccx'?2:['cx','cy','cz','crx','cry','crz','cp','cu','csx','swap'].includes(name)?1:0;if(k!==c.length||(['mcx','mcry'].includes(name)&&!k)||(['rx','ry','rz','p','crx','cry','crz','cp','u','cu','mcry'].includes(name)&&!Number.isFinite(g.theta))||(['u','cu'].includes(name)&&(!Number.isFinite(g.phi)||!Number.isFinite(g.lambda))))throw Error('Invalid contraction signature')}
const emptyResult=(dyadic=false)=>({real:0,imag:0,log2Magnitude:null,phase:0,mode:dyadic?'dyadic-contraction':'factor-contraction',peakTensorBytes:0,work:0,eliminated:0,...(dyadic?{exact:{realMantissa:'0',imagMantissa:'0',binaryExponent:0},peakDyadicPayloadBytes:0}: {})});
export function contractAmplitude(n,gates,bits,options={}){return contractNetwork(n,gates,bits,options,false)}
export function exactDyadicAmplitude(n,gates,bits,options={}){return contractNetwork(n,gates,bits,{...options,dyadic:true},false)}
// A double-layer circuit network contracts <0|U† P U|0>. For a marginal,
// P is the product of computational-basis projectors. Output bra and ket
// indices are identified; all unrestricted indices are summed coherently.
export function contractProbability(n,gates,mask,options={}){
 const r=contractNetwork(n,gates,mask,options,true);
 if(r.log2Magnitude!==null&&(r.phase < -1e-9||r.phase>1e-9||r.log2Magnitude>1e-9))throw new ContractionBudget('Non-real or negative probability; numerical result rejected');
 return {...r,probability:r.real,log2Probability:r.log2Magnitude,mode:'double-layer-probability'}
}
export function contractExpectation(n,gates,pauli,options={}){
 if(typeof pauli!=='string'||pauli.length!==n||!/^[IXYZ]+$/.test(pauli))throw Error('Invalid Pauli string');
 const extra=[];for(let q=0;q<n;q++){const name=pauli[n-1-q].toLowerCase();if(name!=='i')extra.push({name,q,controls:[]})}
 const r=contractNetwork(n,gates,'*'.repeat(n),options,true,extra);
 if(Math.abs(r.imag)>1e-11||Math.abs(r.real)>1+1e-11)throw new ContractionBudget('Observable outside Hermitian numerical tolerance');
 return {...r,value:r.real,mode:'double-layer-expectation'}
}
function contractNetwork(n,gates,bits,{maxBytes=4194304,maxWork=50000000,maxVariables=4096,internalFixed=[],ordering='degree',dyadic=false,maxBits=131072,maxArity=18}={},double=false,extra=[]){
 if(!Number.isInteger(n)||n<1||n>4096||typeof bits!=='string'||bits.length!==n||!(double?/^[01*]+$/:/^[01]+$/).test(bits)||!Array.isArray(gates)||!Number.isSafeInteger(maxBytes)||maxBytes<16||!Number.isSafeInteger(maxWork)||maxWork<1||!Number.isSafeInteger(maxVariables)||maxVariables<n||!['degree','fill','search'].includes(ordering))throw Error('Invalid contraction configuration');
 let next=0,raw=[];const fixed=new Map(),alloc=()=>{if(next>=maxVariables)throw new ContractionBudget('Contraction variable budget exceeded');return next++};
 function build(program,conj){const wire=Array.from({length:n},()=>{const v=alloc();fixed.set(v,0);return v});for(const g of program){validate(n,g);if(g.name==='swap'){[wire[g.q],wire[g.controls[0]]]=[wire[g.controls[0]],wire[g.q]];continue}let m=matrix(g);if(m.some(v=>!v.every(Number.isFinite)))throw Error('Nonfinite contraction matrix');if(conj)m=m.map(([r,i])=>[r,-i]);const c=g.controls.map(q=>wire[q]),a=wire[g.q],diag=zero(m[1])&&zero(m[2]),b=diag?a:alloc();wire[g.q]=b;raw.push({vars:diag?[...c,a]:[...c,a,b],c:c.length,diag,m})}return wire}
 const wire=build(double&&extra.length?[...gates,...extra]:gates,false);
 if(double){const bra=build(gates,true),map=new Map(bra.map((v,q)=>[v,wire[q]]));for(const [v,w] of map){if(fixed.has(v)){if(fixed.has(w)&&fixed.get(w)!==fixed.get(v))return emptyResult(dyadic);fixed.set(w,fixed.get(v));fixed.delete(v)}}for(const f of raw)f.vars=f.vars.map(v=>map.get(v)??v)}
 for(let q=0;q<n;q++){const c=bits[n-1-q];if(c==='*')continue;const x=Number(c),v=wire[q];if(fixed.has(v)&&fixed.get(v)!==x)return emptyResult(dyadic);fixed.set(v,x)}
 for(const [v,x] of internalFixed){if(double||!Number.isInteger(v)||v<n||v>=next||fixed.has(v)||(x!==0&&x!==1))throw Error('Invalid internal contraction slice');fixed.set(v,x)}
 const factors=raw.map(f=>{const vars=f.vars.filter(x=>!fixed.has(x)),pos=f.vars.map(v=>fixed.has(v)?-(fixed.get(v)+1):vars.indexOf(v));return {vars,value(x){const bit=j=>pos[j]<0?-pos[j]-1:(x>>>pos[j])&1;let active=true;for(let k=0;k<f.c;k++)if(!bit(k)){active=false;break}const col=bit(f.c),row=f.diag?col:bit(f.c+1);return active?f.m[row*2+col]:[+(row===col),0]}}});
 return dyadic?evaluateDyadicFactors(factors,{maxBytes,maxWork,maxBits,maxArity}):evaluateBinaryFactors(factors,{maxBytes,maxWork,ordering});
}
// Internal reusable contraction primitive; factors contain trusted compiled
// coefficient generators with unique binary variable identifiers.
export function evaluateBinaryFactors(raw,{maxBytes=4194304,maxWork=50000000,ordering='degree'}={}){
 let plan=null;if(ordering==='search'){try{plan=planElimination(raw.map(f=>f.vars),{maxPlannerWork:Math.min(maxWork,100000000)})}catch(e){throw new ContractionBudget('Elimination planner: '+e.message)}}let planCursor=0;if(plan&&(plan.peakTensorBytes>maxBytes||plan.maxSeparatorVariables>24||plan.estimatedProducts+plan.plannerWork>maxWork))throw Object.assign(new ContractionBudget('Predicted contraction exceeds configured tensor/work budget'),{work:plan.plannerWork,peakTensorBytes:0,predictedBytes:plan.peakTensorBytes,predictedWidth:plan.maxSeparatorVariables,predictedProducts:plan.estimatedProducts,variable:raw.length?plan.order[0]:undefined});
 let bytes=0,peak=0,work=plan?.plannerWork??0,id=0,eliminated=0,maxWidth=0;const fs=new Map(),links=new Map();let scalar=[1,0],exponent=0;
 const limit=(message,variable)=>{throw Object.assign(new ContractionBudget(message),{variable,work,peakTensorBytes:peak})};const spend=k=>{work+=k;if(work>maxWork)limit('Contraction work budget exceeded')};const reserve=(k,variable)=>{if(!Number.isSafeInteger(k)||bytes+k>maxBytes)limit('Contraction tensor byte budget exceeded',variable??links.keys().next().value);bytes+=k;peak=Math.max(peak,bytes)};
 const insert=(vars,a,e=0)=>{e+=normalize(a);if(vars.length===0){const r=scalar[0]*a[0]-scalar[1]*a[1],i=scalar[0]*a[1]+scalar[1]*a[0],x=new Float64Array([r,i]);if(!zero(scalar)&&!zero(a)&&zero(x))limit('Contraction scalar product underflow');exponent+=e+normalize(x);scalar=[...x];bytes-=a.byteLength;return}const f={vars,a,e,id:id++};fs.set(f.id,f);for(const q of vars){if(!links.has(q))links.set(q,new Set());links.get(q).add(f.id)}};
 const remove=f=>{fs.delete(f.id);bytes-=f.a.byteLength;for(const q of f.vars){const s=links.get(q);s.delete(f.id);if(!s.size)links.delete(q)}};
 for(const f of raw){const vars=f.vars,len=2**vars.length;if(vars.length>24)limit('Gate tensor arity exceeds 24',vars[0]);reserve(len*16,vars[0]);const a=new Float64Array(len*2);spend(len);for(let x=0;x<len;x++){const v=f.value(x);a[2*x]=v[0];a[2*x+1]=v[1]}insert(vars,a)}raw=[];
 while(links.size){let q,best=Infinity,bestScore=Infinity,neighbors=null;for(const [v,ids] of (plan?[[plan.order[planCursor++],links.get(plan.order[planCursor-1])]]:links)){if(!ids)throw Error('Contraction plan mismatch');const s=new Set();for(const j of ids)for(const w of fs.get(j).vars)if(w!==v)s.add(w);spend(1);let score=s.size;if(ordering==='fill'){if(s.size>24){score=Infinity;continue}let fill=0;const vs=[...s];for(let i=0;i<vs.length;i++)for(let j=i+1;j<vs.length;j++){spend(1);const a=links.get(vs[i]),b=links.get(vs[j]);if(![...a].some(k=>b.has(k)))fill++}score=fill+s.size*.01}if(score<bestScore){q=v;best=s.size;bestScore=score;neighbors=s;if(best===0)break}}if(best>24)limit('Contraction separator exceeds 24 variables',q);maxWidth=Math.max(maxWidth,best);const vars=[...neighbors].sort((a,b)=>a-b),group=[...links.get(q)].map(j=>fs.get(j)),len=2**vars.length;reserve(16*len,q);const a=new Float64Array(2*len),index=new Map(vars.map((v,j)=>[v,j])),maps=group.map(f=>f.vars.map(v=>v===q?-1:index.get(v))),e=group.reduce((x,f)=>x+f.e,0);spend(2*len*group.length);
  // Enumerate output assignments in Gray-code order. Each transition toggles
  // one output bit; the per-factor indices are updated in O(incident factors),
  // rather than rebuilding an index from every variable for every product.
  const base=new Uint32Array(group.length),qbit=new Uint32Array(group.length),toggles=Array.from({length:vars.length},()=>[]);for(let j=0;j<group.length;j++)for(let t=0;t<maps[j].length;t++){const v=maps[j][t],b=1<<t;if(v<0)qbit[j]=b;else toggles[v].push([j,b])}
  for(let step=0;step<len;step++){const x=step^(step>>>1);if(step){const changed=31-Math.clz32(step&-step);for(const [j,b] of toggles[changed])base[j]^=b}let ar=0,ai=0;for(let v=0;v<2;v++){let r=1,i=0;for(let k=0;k<group.length;k++){const idx=base[k]^(v?qbit[k]:0),arr=group[k].a,b=arr[2*idx],c=arr[2*idx+1],rr=r*b-i*c,ii=r*c+i*b;if((r!==0||i!==0)&&(b!==0||c!==0)&&rr===0&&ii===0)throw new ContractionBudget('Contraction product underflow');r=rr;i=ii}ar+=r;ai+=i}a[2*x]=ar;a[2*x+1]=ai}for(const f of group)remove(f);insert(vars,a,e);eliminated++}
 const m=Math.hypot(...scalar),log=m?exponent+Math.log2(m):null,scale=2**exponent;const component=x=>exponent< -1022?(x*2**(exponent+1074))*Number.MIN_VALUE:x*scale;const real=m?component(scalar[0]):0,imag=m?component(scalar[1]):0;if(!Number.isFinite(real)||!Number.isFinite(imag))throw Error('Nonfinite amplitude result');return {real,imag,log2Magnitude:log,phase:m?Math.atan2(scalar[1],scalar[0]):0,componentUnderflow:!!(m&&(scalar[0]&&!real||scalar[1]&&!imag)),scaledMantissa:scalar,binaryExponent:exponent,mode:'factor-contraction',peakTensorBytes:peak,maxSeparatorVariables:maxWidth,work,eliminated,...(plan?{planning:{predictedBytes:plan.peakTensorBytes,predictedWidth:plan.maxSeparatorVariables,estimatedProducts:plan.estimatedProducts,plannerWork:plan.plannerWork,trialsCompleted:plan.trialsCompleted}}:{}),precision:'Float64; all terms contracted, no intentional pruning'}
}

// Exact coherent slicing of internal binary variables; the accumulator sums the
// represented Float64 slice results as bounded integers. No partial result if
// either work/slice limits are reached. Tensor bytes exclude JS metadata.
export function slicedAmplitude(n,gates,bits,{maxBytes=4194304,maxWork=50000000,maxVariables=4096,maxSlices=256,maxAccumulatorBits=262144,ordering='degree'}={}){
 if(!Number.isSafeInteger(maxSlices)||maxSlices<1||maxSlices>65536||!Number.isSafeInteger(maxWork)||maxWork<1)throw Error('Invalid slicing limits');
 const pending=[[]],sum=createScaledAccumulator(maxAccumulatorBits);let work=0,peak=0,completed=0,attempts=0,width=0;
 while(pending.length){if(++attempts>2*maxSlices-1||work>=maxWork)throw new ContractionBudget('Sliced contraction total work/slice limit exceeded; no complete amplitude');const fixed=pending.pop();try{const r=contractAmplitude(n,gates,bits,{maxBytes,maxWork:maxWork-work,maxVariables,internalFixed:fixed,ordering});work+=r.work;peak=Math.max(peak,r.peakTensorBytes);width=Math.max(width,r.maxSeparatorVariables??0);if(++completed>maxSlices)throw new ContractionBudget('Slice limit exceeded; no complete amplitude');if(r.scaledMantissa)sum.add(r.scaledMantissa,r.binaryExponent)}catch(e){if(!(e instanceof ContractionBudget)||!Number.isInteger(e.variable))throw e;work+=e.work??0;peak=Math.max(peak,e.peakTensorBytes??0);if(completed+pending.length+2>maxSlices)throw new ContractionBudget('Slice limit exceeded; no complete amplitude');pending.push([...fixed,[e.variable,0]],[...fixed,[e.variable,1]])}}
 return {...sum.result(),mode:'sliced-contraction',peakTensorBytes:peak,maxSeparatorVariables:width,work,slices:completed,attempts,precision:'Float64 tensor contractions; exact sum of represented slice outputs; no intentional pruning'}
}
