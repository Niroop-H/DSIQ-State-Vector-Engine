// DSIQ lossless static wire-order planner. No gate cancellation or circuit templates.
import {ScientificDSIQ} from './scientific.mjs';
export function planOrder(n,gates){
  if(!Number.isInteger(n)||n<1||n>4096)throw Error('Invalid circuit width');
  const adj=Array.from({length:n},()=>new Map());
  for(const g of gates){for(const c of g.controls||[]){if(!Number.isInteger(c)||c<0||c>=n||!Number.isInteger(g.q)||g.q<0||g.q>=n)throw Error('Invalid gate operands');adj[c].set(g.q,(adj[c].get(g.q)||0)+1);adj[g.q].set(c,(adj[g.q].get(c)||0)+1)}}
  // Connected components, ordered by breadth-first traversal with weighted degree tie-breaks.
  // This is an ordering of variables, not a partition that drops interactions.
  const seen=new Set(),order=[];for(let start=0;start<n;start++){if(seen.has(start))continue;const queue=[start];seen.add(start);for(let p=0;p<queue.length;p++){const q=queue[p];order.push(q);const next=Array.from(adj[q]).filter(([v])=>!seen.has(v)).sort((a,b)=>b[1]-a[1]||adj[a[0]].size-adj[b[0]].size||a[0]-b[0]);for(const [v] of next){seen.add(v);queue.push(v)}}}
  return order;
}
export class PlannedDSIQ {
  constructor(n,gates,budget=32768,order=planOrder(n,gates)){if(order.length!==n||new Set(order).size!==n||order.some(q=>!Number.isInteger(q)||q<0||q>=n))throw Error('Invalid wire permutation');this.n=n;this.operations=0;this.logicalSwaps=0;this.order=[...order];this.inverse=Array(n);order.forEach((q,i)=>this.inverse[q]=i);this.core=new ScientificDSIQ(n,budget)}
  apply(g){if(!Number.isInteger(g.q)||g.q<0||g.q>=this.n||!Array.isArray(g.controls)||g.controls.some(q=>!Number.isInteger(q)||q<0||q>=this.n))throw Error('Invalid gate operands');if(g.name==='swap'){if(g.controls.length!==1||g.controls[0]===g.q)throw Error('Invalid SWAP operands');const a=g.controls[0],b=g.q,pa=this.inverse[a],pb=this.inverse[b];this.order[pa]=b;this.order[pb]=a;this.inverse[a]=pb;this.inverse[b]=pa;this.operations++;this.logicalSwaps++;return}this.core.apply({...g,q:this.inverse[g.q],controls:g.controls.map(q=>this.inverse[q])});this.operations++}
  permute(bits){if(typeof bits!=='string'||bits.length!==this.n||!/^[01]+$/.test(bits))throw Error('Invalid bitstring');return this.order.slice().reverse().map(q=>bits[this.n-1-q]).join('')}
  restore(bits){return this.inverse.slice().reverse().map(q=>bits[this.n-1-q]).join('')}
  check(bits){this.permute(bits)}
  amplitude(bits){return this.core.amplitude(this.permute(bits))}
  *replay(bits,slice){return yield* this.core.replay(this.permute(bits),slice)}
  sample(random){return this.restore(this.core.sample(random))}
  norm(){return this.core.norm()}
  expectation(p){if(typeof p!=='string'||p.length!==this.n||!/^[IXYZ]+$/.test(p))throw Error('Invalid Pauli string');return this.core.expectation(this.order.slice().reverse().map(q=>p[this.n-1-q]).join(''))}
  probability(values){return this.core.probability(Object.fromEntries(Object.entries(values).map(([q,b])=>[this.inverse[q],b])))}
  measure(q,random){return this.core.measure(this.inverse[q],random)}
  reset(q,random){return this.core.reset(this.inverse[q],random)}
  collect(){this.core.collect()}
  get mode(){return this.core.mode}
  stats(){return {...this.core.stats(),kernelGates:this.core.gates.length,gates:this.operations,logicalSwaps:this.logicalSwaps,wireOrder:this.order,ordering:'lossless interaction-graph breadth-first'}}
}
