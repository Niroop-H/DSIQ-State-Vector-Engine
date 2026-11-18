// MAH Quantum DSIQ: exact (up to Float64 rounding) DAG contractions.
import {DSIQ} from './engine.mjs';
const add=(a,b)=>[a[0]+b[0],a[1]+b[1]], mul=(a,b)=>[a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0]], conj=a=>[a[0],-a[1]], zero=a=>a[0]===0&&a[1]===0;
const O=[1,0],I=[0,1],Z=[0,0];
export class ScientificDSIQ extends DSIQ {
  constructor(n,budget){super(n,budget);this.measured=false;this.invalid=false}
  requireDAG(){if(this.invalid||this.mode!=='dag')throw Error('Scientific operation requires a valid DAG; replay currently supports amplitude queries only')}
  apply(g){if(this.invalid)throw Error('State invalidated');super.apply(g);if(this.measured&&this.mode!=='dag'){this.invalid=true;throw Error('Resource boundary after measurement: coherent replay of a collapsed history is not supported')}}
  amplitude(bits){if(this.invalid)throw Error('State invalidated');return super.amplitude(bits)}
  sample(random=Math.random){this.requireDAG();return super.sample(random)}
  *replay(bits,slice){if(this.measured||this.invalid)throw Error('Replay after measurement is unsupported');return yield* super.replay(bits,slice)}
  // Contract <this|P|other>, where P is a string ordered q[n-1]...q[0].
  overlap(other=this,pauli='I'.repeat(this.n),memoBudget=this.maxNodes){this.requireDAG();other.requireDAG();if(other.n!==this.n||typeof pauli!=='string'||pauli.length!==this.n||!/^[IXYZ]+$/.test(pauli)||!Number.isSafeInteger(memoBudget)||memoBudget<0)throw Error('Invalid contraction arguments');const memo=new Map();
    const edge=(a,b)=>zero(a[1])||zero(b[1])?Z:mul(mul(conj(a[1]),b[1]),walk(a[0],b[0]));
    const walk=(a,b)=>{if(!a&&!b)return O;const key=a+':'+b;if(memo.has(key))return memo.get(key);const x=this.nodes.get(a),y=other.nodes.get(b);if(!x||!y||x.q!==y.q)throw Error('Invalid DAG levels');const p=pauli[this.n-1-x.q];let v;if(p==='I')v=add(edge(x.a,y.a),edge(x.b,y.b));else if(p==='Z')v=add(edge(x.a,y.a),mul([-1,0],edge(x.b,y.b)));else if(p==='X')v=add(edge(x.a,y.b),edge(x.b,y.a));else v=add(mul([0,-1],edge(x.a,y.b)),mul(I,edge(x.b,y.a)));if(memo.size<memoBudget)memo.set(key,v);return v};
    const v=edge(this.root,other.root);if(!v.every(Number.isFinite))throw Error('Nonfinite contraction');return v;
  }
  expectation(pauli){return this.overlap(this,pauli)[0]}
  norm(){return this.overlap()[0]}
  // Contract a computational-basis projector directly; no amplitude enumeration.
  probability(assignments={}){this.requireDAG();const entries=Object.entries(assignments),wanted=new Map(entries.map(([q,b])=>[Number(q),b]));if(entries.length!==wanted.size||entries.some(([q,b])=>!Number.isInteger(Number(q))||Number(q)<0||Number(q)>=this.n||(b!==0&&b!==1)))throw Error('Invalid projector');const memo=new Map(), e=a=>zero(a[1])?0:(Math.hypot(...a[1])**2)*walk(a[0]);const walk=id=>{if(!id)return 1;if(memo.has(id))return memo.get(id);const n=this.nodes.get(id),b=wanted.get(n.q),p=b===0?e(n.a):b===1?e(n.b):e(n.a)+e(n.b);memo.set(id,p);return p};return e(this.root)}
  measure(q,random=Math.random){this.requireDAG();if(!Number.isInteger(q)||q<0||q>=this.n)throw Error('Invalid measurement qubit');const p0=this.probability({[q]:0}),p1=this.probability({[q]:1}),u=random();if(!(p0+p1>0)||!(u>=0&&u<1))throw Error('Invalid probability or RNG');const bit=u*(p0+p1)<p0?0:1;const old=this.root,memo=new Map();try{const walk=e=>{if(zero(e[1]))return [0,Z];let r=memo.get(e[0]);if(!r){const n=this.nodes.get(e[0]);r=n.q===q?this.make(q,bit?[0,Z]:n.a,bit?n.b:[0,Z]):this.make(n.q,walk(n.a),walk(n.b));memo.set(e[0],r)}return [r[0],mul(r[1],e[1])]};const root=walk(old),m=Math.hypot(...root[1]);if(!(m>0))throw Error('Projection underflow');this.root=[root[0],[root[1][0]/m,root[1][1]/m]];this.measured=true;this.collect();return bit}catch(e){this.root=old;this.collect();throw e}}
  reset(q,random=Math.random){const bit=this.measure(q,random);if(bit)this.apply({name:'x',q,controls:[]});return bit}
}
