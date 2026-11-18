// MAH Quantum DSIQ: affine support + quadratic phase, independent implementation.
// State = exp(i*pi*gamma/4) 2^(-r/2) sum_u i^q(u) |A u xor b>.
// Exact integer phase/support operations; conversion to IEEE floating point only at output.
const bit=i=>1n<<BigInt(i), mod=(x,m)=>((x%m)+m)%m;
const index=b=>b.toString(2).length-1;
function* bits(x){while(x){const b=x&-x;yield index(b);x^=b}}
function parity(x){let s=0;while(x){x&=x-1n;s^=1}return s}
const phases=[[1,0],[Math.SQRT1_2,Math.SQRT1_2],[0,1],[-Math.SQRT1_2,Math.SQRT1_2],[-1,0],[-Math.SQRT1_2,-Math.SQRT1_2],[0,-1],[Math.SQRT1_2,-Math.SQRT1_2]];
export const affineNames=new Set(['i','h','x','y','z','s','sdg','cx','cy','cz','swap']);
export class AffineClifford {
 constructor(n){if(!Number.isSafeInteger(n)||n<1||n>4096)throw Error('Invalid affine width');this.n=n;this.rows=Array(n).fill(0n);this.b=new Uint8Array(n);this.l=new Uint8Array(n+1);this.adj=Array(n+1).fill(0n);this.used=0n;this.r=0;this.gamma=0;this.operations=0;this.peak=0;this.mode='affine-clifford';this.cache=null}
 phase(mask,u){let t=0;for(const i of bits(mask&u)){t+=this.l[i]+2*parity(this.adj[i]&u&(bit(i)-1n))}return mod(t,4)}
 linear(mask,k,b=0){k=mod(k,4);if(b){this.gamma=mod(this.gamma+2*k,8);k=mod(-k,4)}if(!k)return;for(const i of bits(mask)){this.l[i]=mod(this.l[i]+k,4);if(k&1)this.adj[i]^=mask^bit(i)}}
 product(a,b,c=0,d=0){ // add 2*(parity(a*u)^c)*(parity(b*u)^d)
  if(c&&d)this.gamma=mod(this.gamma+4,8);
  if(c)this.linear(b,2);if(d)this.linear(a,2);
  for(const i of bits(a&b))this.l[i]=(this.l[i]+2)%4;
  for(const i of bits(a))this.adj[i]^=b&~bit(i);
  for(const i of bits(b))this.adj[i]^=a&~bit(i);
 }
 drop(p){const k=bit(p);for(const j of bits(this.adj[p]))this.adj[j]&=~k;this.adj[p]=0n;this.l[p]=0;this.used&=~k;this.r--;for(let i=0;i<this.n;i++)this.rows[i]&=~k}
 substitute(p,m,b){const k=this.l[p],a=this.adj[p],bm=bit(p);for(let j=0;j<this.n;j++)if(this.rows[j]&bm){this.rows[j]^=bm^m;this.b[j]^=b}this.drop(p);this.linear(m,k,b);this.product(m,a,b,0)}
 kernel(q){ // one possible null direction after deleting a physical row; at most dimension one
  const basis=Array(this.n+1).fill(0n);for(let j=0;j<this.n;j++){if(j===q)continue;let a=this.rows[j];while(a){const p=index(a);if(basis[p])a^=basis[p];else{basis[p]=a;break}}}
  let v=0n;for(const p of bits(this.used)){if(!basis[p]){if(v)throw Error('Affine rank invariant broken');v=bit(p)}}if(!v)return 0n;for(const p of bits(this.used))if(basis[p]&&parity(basis[p]&v))v^=bit(p);return v
 }
 hadamard(q){const v=this.kernel(q),old=this.rows[q],off=this.b[q];let y=0;while(this.used&bit(y))y++;const yb=bit(y);this.used|=yb;this.r++;this.peak=Math.max(this.peak,this.r);this.rows[q]=yb;this.b[q]=0;this.product(old,yb,off,0);if(!v)return;
  if(!parity(old&v))throw Error('Affine null direction invariant');const p=index(v&-v),h=this.phase(this.used,v);let B=0n;for(const i of bits(v)){B^=this.adj[i];if(this.l[i]&1)B^=bit(i)}B&=~bit(p);this.drop(p);if(!(B&yb))throw Error('Hadamard elimination invariant');if(h%2===0){this.substitute(y,B^yb,h/2)}else{const s=h===1?1:-1;this.gamma=mod(this.gamma+s,8);this.linear(B,-s)}
 }
 apply(g){const {name,q,controls:c}=g;if(!affineNames.has(name)||!Number.isInteger(q)||q<0||q>=this.n||!Array.isArray(c)||c.length!==(['cx','cy','cz','swap'].includes(name)?1:0)||c.some(x=>!Number.isInteger(x)||x<0||x>=this.n||x===q))throw Error('Unsupported affine gate');this.cache=null;
  if(name==='h')this.hadamard(q);else if(name==='x')this.b[q]^=1;else if(name==='y'){this.linear(this.rows[q],2,this.b[q]);this.gamma=mod(this.gamma+2,8);this.b[q]^=1}else if(['z','s','sdg'].includes(name))this.linear(this.rows[q],name==='z'?2:name==='s'?1:3,this.b[q]);else if(name==='cx'||name==='cy'){const a=c[0];if(name==='cy'){this.linear(this.rows[a],1,this.b[a]);this.product(this.rows[a],this.rows[q],this.b[a],this.b[q])}this.rows[q]^=this.rows[a];this.b[q]^=this.b[a]}else if(name==='cz'){const a=c[0];this.product(this.rows[a],this.rows[q],this.b[a],this.b[q])}else if(name==='swap'){const a=c[0];[this.rows[q],this.rows[a]]=[this.rows[a],this.rows[q]];[this.b[q],this.b[a]]=[this.b[a],this.b[q]]}this.operations++
 }
 check(x){if(typeof x!=='string'||x.length!==this.n||!/^[01]+$/.test(x))throw Error('Invalid affine bitstring')}
 equations(){if(this.cache)return this.cache;const piv=Array(this.n+1).fill(null),constraints=[];for(let j=0;j<this.n;j++){let a=this.rows[j],b=bit(j);while(a){const i=index(a);if(piv[i]){a^=piv[i][0];b^=piv[i][1]}else{piv[i]=[a,b];break}}if(!a)constraints.push(b)}this.cache={piv,constraints};return this.cache}
 solve(x){const {piv,constraints}=this.equations();if(constraints.some(a=>parity(a&x)))return null;let u=0n;for(const i of bits(this.used)){const [a,b]=piv[i];if(parity(a&u)^parity(b&x))u|=bit(i)}return u}
 offset(){let b=0n;for(let q=0;q<this.n;q++)if(this.b[q])b|=bit(q);return b}
 amplitude(x){this.check(x);const u=this.solve(BigInt('0b'+x)^this.offset());if(u===null)return {real:0,imag:0,log2Magnitude:null,phase:0};const exponent=mod(this.gamma+2*this.phase(this.used,u),8),p=phases[exponent],m=2**(-this.r/2);return {real:m*p[0],imag:m*p[1],log2Magnitude:-this.r/2,phase:Math.atan2(p[1],p[0]),componentUnderflow:m===0,exact:{sqrt2Power:-this.r,phaseEighthTurns:exponent}}}
 norm(){return 1}
 sample(random=Math.random){let u=0n;for(const i of bits(this.used)){const v=random();if(!(v>=0&&v<1))throw Error('Invalid RNG');if(v<.5)u|=bit(i)}return this.rows.map((a,q)=>String(parity(a&u)^this.b[q])).reverse().join('')}
 expectation(p){if(typeof p!=='string'||p.length!==this.n||!/^[IXYZ]+$/.test(p))throw Error('Invalid Pauli');let x=0n,L=0n,c=0;for(let q=0;q<this.n;q++){const a=p[this.n-1-q];if(a==='X'||a==='Y')x|=bit(q);if(a==='Z'||a==='Y'){L^=this.rows[q];c+=2*this.b[q]}if(a==='Y')c++}const v=this.solve(x);if(v===null)return 0;for(const i of bits(v)){L^=this.adj[i];if(this.l[i]&1)L^=bit(i)}if(L)return 0;const phase=mod(c-this.phase(this.used,v),4);if(phase&1)throw Error('Non-Hermitian affine expectation');return phase===0?1:-1}
 probability(assign){const piv=Array(this.n+1).fill(null);let rank=0;for(const [s,b] of Object.entries(assign)){const q=Number(s);if(!Number.isInteger(q)||q<0||q>=this.n||(b!==0&&b!==1))throw Error('Invalid projection');let a=this.rows[q],v=b^this.b[q],inserted=false;while(a){const i=index(a);if(piv[i]){a^=piv[i][0];v^=piv[i][1]}else{piv[i]=[a,v];rank++;inserted=true;break}}if(!inserted&&v)return 0}return 2**-rank}
 stats(){return {qubits:this.n,gates:this.operations,mode:this.mode,rank:this.r,peakRank:this.peak,precision:'Exact binary and mod-4/mod-8 algebra; Float64 output',liveNodes:null,peakNodes:null}}
}
// Normalize a quadratic Gauss sum exactly in powers of sqrt(2) and eighth roots.
// g is a scratch phase polynomial, with no physical output rows of interest.
function gauss(g){let log=0;while(g.used){const p=index(g.used&-g.used),a=g.adj[p],l=g.l[p];g.drop(p);if(l&1){const s=l===1?1:-1;g.gamma=mod(g.gamma+s,8);g.linear(a,-s);log-=.5}else if(a){const y=index(a&-a);g.substitute(y,a^bit(y),l/2);log--}else if(l===2)return {re:0,im:0,log2Magnitude:null}}const z=phases[g.gamma],m=2**log;return {re:z[0]*m,im:z[1]*m,log2Magnitude:log}}
export class AffinePhaseBoundary extends Error{}
export const affinePhaseNames=new Set([...affineNames,'t','tdg']);
// Extension: a cubic Boolean phase polynomial represented by XOR-parity terms
// mod 8. Supports all Clifford gates whenever Hadamard elimination doesn't
// require summing across a non-Clifford phase direction. No term truncation.
export class AffinePhaseDSIQ extends AffineClifford {
 constructor(n,maxTerms=65536){super(n);if(!Number.isSafeInteger(maxTerms)||maxTerms<1)throw Error('Invalid affine phase budget');this.mode='affine-phase';this.extra=new Map();this.maxTerms=maxTerms;this.peakTerms=0}
 eighth(mask,k,b=0){k=mod(k,8);if(b){this.gamma=mod(this.gamma+k,8);k=mod(-k,8)}if(!mask||!k)return;const a=mod((this.extra.get(mask)??0)+k,8);if(!(a&1)){this.extra.delete(mask);if(a)this.linear(mask,a/2)}else{if(!this.extra.has(mask)&&this.extra.size>=this.maxTerms)throw new AffinePhaseBoundary('Affine phase term budget exceeded');this.extra.set(mask,a);this.peakTerms=Math.max(this.peakTerms,this.extra.size)}}
 hadamard(q){const v=this.kernel(q);if(v){for(const m of this.extra.keys())if(parity(m&v))throw new AffinePhaseBoundary('Hadamard crosses a non-Clifford parity direction; rebuild without this representation');const p=v&-v;const extra=[...this.extra];this.extra.clear();for(const [m,k] of extra){this.eighth(m&~p,k)}}super.hadamard(q)}
 apply(g){if(g.name==='t'||g.name==='tdg'){const {q,controls}=g;if(!Number.isInteger(q)||q<0||q>=this.n||!Array.isArray(controls)||controls.length)throw Error('Invalid phase gate');this.eighth(this.rows[q],g.name==='t'?1:-1,this.b[q]);this.operations++;return}super.apply(g)}
 amplitude(x){this.check(x);const u=this.solve(BigInt('0b'+x)^this.offset());if(u===null)return {real:0,imag:0,log2Magnitude:null,phase:0};let p=this.gamma+2*this.phase(this.used,u);for(const [m,k] of this.extra)if(parity(m&u))p+=k;const z=phases[mod(p,8)],m=2**(-this.r/2);return {real:m*z[0],imag:m*z[1],log2Magnitude:-this.r/2,phase:Math.atan2(z[1],z[0]),componentUnderflow:m===0,exact:{sqrt2Power:-this.r,phaseEighthTurns:mod(p,8)}}}
 expectation(p){if(typeof p!=='string'||p.length!==this.n||!/^[IXYZ]+$/.test(p))throw Error('Invalid Pauli');let x=0n,L=0n,c=0;for(let q=0;q<this.n;q++){const a=p[this.n-1-q];if(a==='X'||a==='Y')x|=bit(q);if(a==='Z'||a==='Y'){L^=this.rows[q];c+=2*this.b[q]}if(a==='Y')c++}const v=this.solve(x);if(v===null)return 0;for(const i of bits(v)){L^=this.adj[i];if(this.l[i]&1)L^=bit(i)}const scratch=new AffineClifford(this.n);scratch.used=this.used;scratch.r=this.r;scratch.gamma=mod(2*c-2*this.phase(this.used,v),8);scratch.linear(L,2);for(const [m,k] of this.extra)if(parity(m&v)){scratch.gamma=mod(scratch.gamma-k,8);scratch.linear(m,k)}const g=gauss(scratch);if(g.im!==0)throw Error('Non-Hermitian affine phase result');return g.re}
 stats(){return {...super.stats(),mode:this.mode,phaseTerms:this.extra.size,peakTerms:this.peakTerms,phaseTermBudget:this.maxTerms,precision:'Exact binary, mod-4/mod-8 phase algebra; Float64 output'}}
}
