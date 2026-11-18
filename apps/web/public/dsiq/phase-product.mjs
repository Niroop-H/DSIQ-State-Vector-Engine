// MAH Quantum independent symbolic product-frame backend. Phases are rational
// multiples of pi, not snapped from approximate floats. Unsupported entanglement
// or local states fail explicitly and can be rebuilt in another representation.
export class PhaseUnsupported extends Error{}
const G=(a,b)=>{a=a<0n?-a:a;while(b){[a,b]=[b,a%b]}return a||1n};
const R=(a,b=1n)=>{if(b<=0n)throw Error('Invalid phase denominator');a=(a%(2n*b)+2n*b)%(2n*b);const g=G(a,b);a/=g;b/=g;if(b.toString(2).length>4096)throw new PhaseUnsupported('Phase denominator budget exhausted');return [a,b]};
const add=(a,b)=>R(a[0]*b[1]+a[1]*b[0],a[1]*b[1]),neg=a=>R(-a[0],a[1]),zero=R(0n),one=R(1n),half=R(1n,2n),quarter=R(1n,4n),eq=(a,b)=>a[0]===b[0]&&a[1]===b[1];
const angle=p=>{const n=p[0]>p[1]?p[0]-2n*p[1]:p[0],a=n<0n?-n:n,b=p[1];if(!a)return 0;const sa=Math.max(0,a.toString(2).length-53),sb=Math.max(0,b.toString(2).length-53);return (n<0n?-1:1)*Math.PI*(Number(a>>BigInt(sa))/Number(b>>BigInt(sb)))*2**(sa-sb)};
const cis=p=>eq(p,zero)?[1,0]:eq(p,one)?[-1,0]:eq(p,half)?[0,1]:eq(p,neg(half))?[0,-1]:[Math.cos(angle(p)),Math.sin(angle(p))];
export class PhaseProductDSIQ {
 constructor(n){if(!Number.isInteger(n)||n<1||n>4096)throw Error('Invalid width');this.n=n;this.v=Array.from({length:n},()=>({b:0}));this.global=zero;this.mode='phase-product';this.operations=0}
 check(bits){if(typeof bits!=='string'||bits.length!==this.n||!/^[01]+$/.test(bits))throw Error('Invalid bitstring')}
 apply(g){const {q,controls:c,name}=g;if(!Number.isInteger(q)||q<0||q>=this.n||!Array.isArray(c)||new Set([q,...c]).size!==c.length+1||c.some(k=>!Number.isInteger(k)||k<0||k>=this.n))throw Error('Invalid gate operands');const expected=['cz','cp','cx','swap'].includes(name)?1:0;if(c.length!==expected)throw new PhaseUnsupported('Unsupported controlled product gate');const v=this.v[q];
 const phase=(k,p)=>{const x=this.v[k];if(x.b===1)this.global=add(this.global,p);else if(x.b===undefined)this.v[k]={p:add(x.p,p)}};
 const p=()=>{if(!Array.isArray(g.piTheta)||g.piTheta.length!==2||g.piTheta.some(s=>typeof s!=='string'||!/^[-]?\d{1,1235}$/.test(s)))throw new PhaseUnsupported('Explicit rational pi phase required');const r=R(BigInt(g.piTheta[0]),BigInt(g.piTheta[1]));if(!Number.isFinite(g.theta))throw Error('Invalid phase');const t=angle(r),a=Math.atan2(Math.sin(t-g.theta),Math.cos(t-g.theta));if(Math.abs(a)>1e-12)throw Error('Conflicting symbolic and numeric phases');return r};
 const x=()=>{if(v.b!==undefined)this.v[q]={b:v.b^1};else{this.global=add(this.global,v.p);this.v[q]={p:neg(v.p)}}};
 if(name==='i'){}else if(name==='x')x();else if(name==='h'){if(v.b!==undefined)this.v[q]={p:v.b?one:zero};else if(eq(v.p,zero))this.v[q]={b:0};else if(eq(v.p,one))this.v[q]={b:1};else throw new PhaseUnsupported('Hadamard creates general local state')}
 else if(['z','s','sdg','t','tdg','p'].includes(name))phase(q,({z:one,s:half,sdg:neg(half),t:quarter,tdg:neg(quarter)})[name]??p());
 else if(name==='swap'){[this.v[q],this.v[c[0]]]=[this.v[c[0]],this.v[q]]}
 else if(name==='cz'||name==='cp'){const u=this.v[c[0]],a=name==='cz'?one:p();if(eq(a,zero)||u.b===0||v.b===0){}else if(u.b===1)phase(q,a);else if(v.b===1)phase(c[0],a);else throw new PhaseUnsupported('Controlled phase creates non-product state')}
 else if(name==='cx'){const u=this.v[c[0]];if(u.b===1)x();else if(u.b!==0){if(v.b===undefined&&eq(v.p,zero)){}else if(v.b===undefined&&eq(v.p,one))phase(c[0],one);else throw new PhaseUnsupported('CNOT creates non-product state')}}else throw new PhaseUnsupported('Unsupported symbolic gate '+name);this.operations++}
 amplitude(bits){this.check(bits);let p=this.global,count=0;for(let q=0;q<this.n;q++){const x=Number(bits[this.n-1-q]),v=this.v[q];if(v.b!==undefined){if(v.b!==x)return {real:0,imag:0,phase:0,log2Magnitude:null}}else{count++;if(x)p=add(p,v.p)}}const a=cis(p),m=2**(-count/2);return {real:a[0]*m,imag:a[1]*m,phase:Math.atan2(a[1],a[0]),log2Magnitude:-count/2}}
 norm(){return 1}
 probability(a={}){let c=0;for(const [q,b] of Object.entries(a)){if(!Number.isInteger(Number(q))||q<0||q>=this.n||(b!==0&&b!==1))throw Error('Invalid projector');const v=this.v[q];if(v.b!==undefined){if(v.b!==b)return 0}else c++}return 2**(-c)}
 expectation(p){if(typeof p!=='string'||p.length!==this.n||!/^[IXYZ]+$/.test(p))throw Error('Invalid Pauli');let a=1;for(let q=0;q<this.n;q++){const v=this.v[q],op=p[this.n-1-q];if(op==='I')continue;if(v.b!==undefined)a*=op==='Z'?(v.b?-1:1):0;else a*=op==='Z'?0:cis(v.p)[op==='X'?0:1]}return a}
 sample(random=Math.random){return this.v.map(v=>{if(v.b!==undefined)return String(v.b);const r=random();if(!(r>=0&&r<1))throw Error('Invalid RNG');return r<.5?'0':'1'}).reverse().join('')}
 stats(){return {mode:this.mode,qubits:this.n,gates:this.operations,phaseFactors:this.n,precision:'Exact rational pi phases; Float64 conversion only at output'}}
}
