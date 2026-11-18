// DSIQ: computational measurement of a Clifford-encoded arbitrary active state.
// For commuting output Z images, row-reduce inactive X masks. Each independent
// inactive flip makes one uniform outcome. Remaining rows act only on the
// active state because inactive wires are |0>. A second symplectic elimination
// reduces these commuting logical Paulis to at most r independent measurements.
// No measurement probabilities are supplied by the caller or benchmark identity.
const bit=q=>1n<<BigInt(q), mod=(a,m)=>(a%m+m)%m;
function parity(x){let p=0;while(x){x&=x-1n;p^=1}return p}
const mul=(a,b)=>({x:a.x^b.x,z:a.z^b.z,p:mod(a.p+b.p+2*parity(a.z&b.x),4)});
const p32=x=>{x^=x>>>16;x^=x>>>8;x^=x>>>4;return (0x6996>>>(x&15))&1};
const phases=[[1,0],[0,1],[-1,0],[0,-1]];
export function createRankSampler(d,Budget){
 const {plan,n}=d,r=plan.flipRank,active=plan.rotations.reduce((s,a)=>s|a.x,0n),coords=[];for(let q=0;q<n;q++)if(active&bit(q))coords.push(q);
 if(coords.length!==r||r>24)throw new Budget('Rank sampling active space exceeds supported arity');
 const N=2**r,vectorBytes=N*16,required=plan.coefficientBytes+4*vectorBytes;
 if(!Number.isSafeInteger(required)||required>plan.maxBytes)throw new Budget('Rank sampling state/scratch exceeds coefficient budget');
 let work=0;const spend=k=>{work+=k;if(work>d.maxWork)throw new Budget('Rank sampling work budget exceeded')};
 const compact=x=>coords.reduce((a,q,i)=>a|((x&bit(q))?bit(i):0n),0n),flipBasis=new Map(),logicalBasis=new Map(),rows=[];
 for(let i=0;i<n;i++){
  let p={...plan.Z[i]},deps=[],k=p.x&~active;
  while(k){spend(1);const j=k.toString(2).length-1,a=flipBasis.get(j);if(!a){flipBasis.set(j,{p,i});break}deps.push(a.i);p=mul(p,a.p);k=p.x&~active}
  if(k){rows.push({kind:'uniform',deps});continue}
  p={x:compact(p.x),z:compact(p.z),p:p.p};let key=p.x|(p.z<<BigInt(r));
  while(key){spend(1);const j=key.toString(2).length-1,a=logicalBasis.get(j);if(!a){logicalBasis.set(j,{p,i});break}deps.push(a.i);p=mul(p,a.p);key=p.x|(p.z<<BigInt(r))}
  if(key){rows.push({kind:'logical',deps,x:Number(p.x),z:Number(p.z),p:p.p});continue}
  if(p.p%2)throw Error('Non-Hermitian rank measurement row');rows.push({kind:'fixed',deps,value:p.p===2?1:0});
 }
 if(logicalBasis.size>r)throw Error('Rank measurement basis exceeds commuting logical rank');
 const base=new Float64Array(2*N);for(let j=0;j<N;j++){let a=1,b=0;for(const {qs,a:v} of d.groups){let x=0;for(let k=0;k<qs.length;k++){const t=coords.indexOf(qs[k]);if(t>=0&&(j>>t&1))x|=1<<k}const re=v[2*x],im=v[2*x+1],nr=a*re-b*im,ni=a*im+b*re;a=nr;b=ni}base[2*j]=a;base[2*j+1]=b;spend(d.groups.length)}
 const state=new Float64Array(base.length),plus=new Float64Array(base.length),minus=new Float64Array(base.length);
 d.rankSampling={inactiveUniformBits:flipBasis.size,logicalMeasurements:logicalBasis.size,deterministicRows:n-flipBasis.size-logicalBasis.size,peakCoefficientBytes:required};
 const draw=random=>{const u=random();if(!(u>=0&&u<1))throw Error('Invalid RNG');return u};
 function walk(random,forced=null){state.set(base);const transformed=new Uint8Array(n),physical=new Uint8Array(n);let log=0;
  for(let i=0;i<n;i++){const row=rows[i];let b,p0,want=forced===null?null:Number(forced[n-1-i]);if(want!==null)for(const j of row.deps)want^=transformed[j];
   if(row.kind==='uniform'){b=want??(draw(random)<.5?0:1);p0=.5}
   else if(row.kind==='fixed'){b=want??row.value;p0=row.value===0?1:0}
   else{
    let np=0,nm=0,hp=false,hm=false;const [pr,pi]=phases[row.p];for(let x=0;x<N;x++){const j=x^row.x,sgn=p32(j&row.z)?-1:1,a=state[2*x],c=state[2*x+1],u=state[2*j],v=state[2*j+1],re=sgn*(pr*u-pi*v),im=sgn*(pr*v+pi*u);const P=a+re,Q=c+im,R=a-re,S=c-im;plus[2*x]=P;plus[2*x+1]=Q;minus[2*x]=R;minus[2*x+1]=S;np+=P*P+Q*Q;nm+=R*R+S*S;hp||=P!==0||Q!==0;hm||=R!==0||S!==0}spend(N);if(!Number.isFinite(np+nm)||np+nm===0||hp&&np===0||hm&&nm===0)throw new Budget('Rank measurement probability not representable');p0=np/(np+nm);b=want??(draw(random)*(np+nm)<np?0:1);const s=b?minus:plus,norm=Math.sqrt(b?nm:np);if(!(norm>0)){if(forced!==null)return {probability:0,log2Probability:null};throw new Budget('Zero-probability selected branch')}for(let x=0;x<state.length;x++)state[x]=s[x]/norm;
    // Compute the selected conditional probability directly, not 1-p0
    // (the latter would erase a small nonzero minus branch).
    const selected=(b?nm:np)/(np+nm);if(!(selected>0))throw new Budget('Rank conditional ratio underflow');log+=Math.log2(selected);p0=null;
   }if(p0!==null){const chosen=b?1-p0:p0;if(chosen===0){if(forced!==null)return {probability:0,log2Probability:null};throw new Budget('Impossible sampled fixed row')}log+=Math.log2(chosen)}transformed[i]=b;for(const j of row.deps)b^=transformed[j];physical[i]=b;spend(1+row.deps.length)}return {bits:Array.from(physical).reverse().join(''),probability:2**log,log2Probability:log};
 }
 return {sample(random=Math.random){return walk(random).bits},probabilityOf(bits){if(typeof bits!=='string'||bits.length!==n||!/^[01]+$/.test(bits))throw Error('Invalid rank sampling basis query');return walk(null,bits)}};
}
