// MAH Quantum DSIQ: all-index pair contraction, with scope-only multi-start
// planning. Eliminate any index whose last occurrences are in a merged pair.
// This is exact algebra, with ordinary Float64 numerical error.
export class PairBudget extends Error{}
const sorted=s=>[...s].sort((a,b)=>a-b);
export function pairPlan(scopes,{trials=12,maxPlannerWork=10000000,seed=0x763516}={}){
 if(!Number.isInteger(trials)||trials<1||trials>64||!Number.isSafeInteger(maxPlannerWork)||maxPlannerWork<1)throw Error('Invalid pair planning limits');let work=0,best=null,attempts=0,exhausted=false;
 const spend=k=>{work+=k;if(work>maxPlannerWork)throw new PairBudget('Pair planning work limit')};
 function rng(seed){let x=seed>>>0;return ()=>{x=(Math.imul(x,1664525)+1013904223)>>>0;return x/4294967296}}
 for(let t=0;t<trials;t++){try{const links=new Map(),factors=new Map(),steps=[],random=rng(seed+t*7919);let next=scopes.length,live=0,peak=0,products=0,span=0;
  const add=(id,vars)=>{const a={id,vars};factors.set(id,a);for(const v of vars){if(!links.has(v))links.set(v,new Set());links.get(v).add(id)}live+=16*2**vars.length;peak=Math.max(peak,live)};
  const remove=id=>{const {vars}=factors.get(id);for(const v of vars){const s=links.get(v);s.delete(id);if(!s.size)links.delete(v)}factors.delete(id);live-=16*2**vars.length};
  for(let i=0;i<scopes.length;i++){if(new Set(scopes[i]).size!==scopes[i].length)throw Error('Duplicate factor variable');if(scopes[i].length)add(i,scopes[i]);else peak=Math.max(peak,live+16)}
  const candidate=(a,b)=>{const union=sorted(new Set([...factors.get(a).vars,...(b===null?[]:factors.get(b).vars)])),drop=union.filter(v=>[...links.get(v)].every(i=>i===a||i===b)),keep=union.filter(v=>!drop.includes(v));spend(1+union.length);return {a,b,union,drop,keep,span:union.length,cost:2**union.length,bytes:16*2**keep.length}};
  while(factors.size){let choice=null,score=Infinity;const seen=new Set();for(const [a,f] of factors){spend(1);if(f.vars.some(v=>links.get(v).size===1)){const c=candidate(a,null),s=c.keep.length+.04*c.span-2;if(s<score){score=s;choice=c}}for(const v of f.vars)for(const b of links.get(v)){if(b<=a)continue;const k=a+':'+b;if(seen.has(k))continue;seen.add(k);const c=candidate(a,b),sa=f.vars.length,sb=factors.get(b).vars.length;let s;switch(t%4){case 0:s=c.keep.length+.07*c.span;break;case 1:s=c.span+.12*c.keep.length;break;case 2:s=c.keep.length-.35*Math.max(sa,sb)+.14*c.span;break;default:s=c.keep.length+.3*c.span-.2*c.drop.length}if(t)s+=random()*.7;if(s<score){score=s;choice=c}}}
   if(!choice)throw Error('No local contraction pair');const c=choice,id=next++;peak=Math.max(peak,live+c.bytes+8*(2**c.keep.length+2**c.drop.length));products+=c.cost;span=Math.max(span,c.span);if(best&&peak>best.peakTensorBytes&&products>=best.estimatedProducts)break;steps.push({...c,id});remove(c.a);if(c.b!==null)remove(c.b);if(c.keep.length)add(id,c.keep);
  }
  attempts++;if(!factors.size){const p={steps,peakTensorBytes:peak,estimatedProducts:products,maxPairArity:span,trial:t};if(!best||p.peakTensorBytes<best.peakTensorBytes||p.peakTensorBytes===best.peakTensorBytes&&p.estimatedProducts<best.estimatedProducts)best=p}
 }catch(e){if(!(e instanceof PairBudget))throw e;exhausted=true;break}}
 if(!best)throw new PairBudget('No complete pair contraction plan');return {...best,plannerWork:work,trialsCompleted:attempts,plannerExhausted:exhausted}
}
const zero=a=>a[0]===0&&a[1]===0;
function normalized(a){let m=0;for(let i=0;i<a.length;i++)m=Math.max(m,Math.abs(a[i]));if(!Number.isFinite(m))throw new PairBudget('Nonfinite pair coefficient');if(!m)return 0;const exp=Math.min(1023,Math.floor(Math.log2(m))),s=2**exp;for(let i=0;i<a.length;i++){const old=a[i];a[i]/=s;if(old!==0&&a[i]===0)throw new PairBudget('Pair dynamic range exceeded')}return exp}
export function evaluatePairFactors(raw,{maxBytes=67108864,maxWork=500000000,trials=12}={}){
 const plan=pairPlan(raw.map(f=>f.vars),{trials,maxPlannerWork:Math.min(maxWork,50000000)});if(!Number.isSafeInteger(maxBytes)||maxBytes<16||!Number.isSafeInteger(maxWork)||maxWork<1)throw Error('Invalid pair limits');let work=plan.plannerWork,live=0,peak=0,scalar=[1,0],exponent=0;
 if(plan.peakTensorBytes>maxBytes||plan.maxPairArity>29||plan.estimatedProducts+work>maxWork)throw Object.assign(new PairBudget('Pair contraction exceeds predicted budget'),{predictedBytes:plan.peakTensorBytes,predictedProducts:plan.estimatedProducts,predictedWidth:plan.maxPairArity,work});
 const reserve=n=>{if(live+n>maxBytes)throw new PairBudget('Pair memory budget exceeded');live+=n;peak=Math.max(peak,live)};const spend=n=>{work+=n;if(work>maxWork)throw new PairBudget('Pair work budget exceeded')};const fs=new Map();
 const insert=(id,vars,a,e=0)=>{e+=normalized(a);if(!vars.length){const z=new Float64Array([scalar[0]*a[0]-scalar[1]*a[1],scalar[0]*a[1]+scalar[1]*a[0]]);if(!zero(scalar)&&!zero(a)&&zero(z))throw new PairBudget('Pair scalar underflow');exponent+=e+normalized(z);scalar=[...z];live-=a.byteLength}else fs.set(id,{vars,a,e})};
 for(let i=0;i<raw.length;i++){const f=raw[i],N=2**f.vars.length;if(f.vars.length>24)throw new PairBudget('Pair input arity exceeds 24');reserve(N*16);spend(N);const a=new Float64Array(2*N);for(let j=0;j<N;j++){const z=f.value(j);a[2*j]=z[0];a[2*j+1]=z[1]}insert(i,f.vars,a)}
 for(const c of plan.steps){const A=fs.get(c.a),B=c.b===null?null:fs.get(c.b);if(!A||c.b!==null&&!B)throw Error('Invalid pair plan');const N=2**c.keep.length,K=2**c.drop.length;reserve(N*16);spend(N*K);const out=new Float64Array(2*N),lookup=new Map([...c.keep.map((v,i)=>[v,[0,i]]),...c.drop.map((v,i)=>[v,[1,i]])]);const am=A.vars.map(v=>lookup.get(v)),bm=B?B.vars.map(v=>lookup.get(v)):[];
  const indices=(m,kind,len)=>{const arr=new Uint32Array(len);const masks=Array.from({length:Math.log2(len)},()=>0);m.forEach(([k,j],i)=>{if(k===kind)masks[j]|=1<<i});for(let x=1;x<len;x++){const bit=31-Math.clz32(x&-x);arr[x]=arr[x&(x-1)]|masks[bit]}return arr};
  // Scratch index arrays are deliberately checked against the same budget.
  const scratch=8*(N+K);reserve(scratch);const ax=indices(am,0,N),ay=indices(am,1,K),bx=indices(bm,0,N),by=indices(bm,1,K);
  for(let x=0;x<N;x++){let re=0,im=0;for(let y=0;y<K;y++){const i=2*(ax[x]|ay[y]),j=2*(bx[x]|by[y]),ar=A.a[i],ai=A.a[i+1],br=B?B.a[j]:1,bi=B?B.a[j+1]:0,r=ar*br-ai*bi,z=ar*bi+ai*br;if((ar!==0||ai!==0)&&(br!==0||bi!==0)&&r===0&&z===0)throw new PairBudget('Pair tensor product underflow');re+=r;im+=z}out[2*x]=re;out[2*x+1]=im}
  live-=scratch+A.a.byteLength+(B?B.a.byteLength:0);fs.delete(c.a);if(B)fs.delete(c.b);insert(c.id,c.keep,out,A.e+(B?.e??0));
 }
 if(fs.size)throw Error('Incomplete pair contraction');const m=Math.hypot(...scalar),log=m?exponent+Math.log2(m):null,component=x=>exponent< -1022?(x*2**(exponent+1074))*Number.MIN_VALUE:x*2**exponent,real=m?component(scalar[0]):0,imag=m?component(scalar[1]):0;if(!Number.isFinite(real)||!Number.isFinite(imag))throw new PairBudget('Nonfinite pair result');return {real,imag,log2Magnitude:log,phase:m?Math.atan2(scalar[1],scalar[0]):0,componentUnderflow:!!(m&&(scalar[0]&&!real||scalar[1]&&!imag)),scaledMantissa:scalar,binaryExponent:exponent,mode:'pair-contraction',peakTensorBytes:peak,work,maxPairArity:plan.maxPairArity,planning:{predictedBytes:plan.peakTensorBytes,predictedProducts:plan.estimatedProducts,plannerWork:plan.plannerWork,trialsCompleted:plan.trialsCompleted},precision:'Float64; all retired indices summed; no deliberate truncation'}
}
