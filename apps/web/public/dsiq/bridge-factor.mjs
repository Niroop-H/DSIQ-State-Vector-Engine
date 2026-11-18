// Coherent block forest. A graph bridge used exactly once admits the exact
// bond decomposition |0><0|⊗I+|1><1|⊗U. Local branch vectors retain every
// coefficient. Tree messages sum all active bond assignments (and both
// independent bra/ket assignments for norms/observables).
import {fixedMatrix,iz,Z,O,ca,cm,cj,cn,zero,timesI,local,result} from './fixed-interval.mjs';
import {operands,ProductBoundary} from './interval-product.mjs';
export class BridgeBoundary extends Error{}
const key=(a,b)=>a<b?`${a}:${b}`:`${b}:${a}`;
export function bridgePlan(n,gates,maxBytes){
 if(!Number.isInteger(n)||n<1||n>4096||!Array.isArray(gates)||gates.length>100000||!Number.isSafeInteger(maxBytes)||maxBytes<1)throw Error('Invalid bridge configuration');
 const edges=new Map(),adj=Array.from({length:n},()=>[]);for(let i=0;i<gates.length;i++){const g=gates[i];operands(n,g);if(!g.controls.length)continue;const c=g.controls[0],k=key(g.q,c);if(!edges.has(k)){const edge={a:g.q,b:c,indices:[]};edges.set(k,edge);adj[g.q].push(edge);adj[c].push(edge)}edges.get(k).indices.push(i)}
 const tin=Array(n).fill(-1),low=Array(n),cut=new Set();let clock=0;
 function visit(v,parent){tin[v]=low[v]=clock++;for(const e of adj[v]){if(e===parent)continue;const w=e.a===v?e.b:e.a;if(tin[w]>=0){low[v]=Math.min(low[v],tin[w]);continue}visit(w,e);low[v]=Math.min(low[v],low[w]);if(low[w]>tin[v]&&e.indices.length===1&&gates[e.indices[0]].name!=='swap')cut.add(e)}}
 for(let q=0;q<n;q++)if(tin[q]<0)visit(q,null);
 const map=Array(n),groups=[];for(let q=0;q<n;q++){if(map[q])continue;const j=groups.length,qs=[],stack=[q];map[q]=[j,0];while(stack.length){const v=stack.pop();map[v]=[j,qs.length];qs.push(v);for(const e of adj[v]){if(cut.has(e))continue;const w=e.a===v?e.b:e.a;if(!map[w]){map[w]=[j,-1];stack.push(w)}}}groups.push({qs,edges:[]})}
 const at=new Map(),bonds=[];for(const e of cut){const a=map[e.a][0],b=map[e.b][0],bond={id:bonds.length,a,b,pa:groups[a].edges.length,pb:groups[b].edges.length,active:false};groups[a].edges.push(bond);groups[b].edges.push(bond);bonds.push(bond);at.set(e.indices[0],bond)}
 const width=Math.max(...groups.map(g=>g.qs.length)),degree=Math.max(...groups.map(g=>g.edges.length));if(width>10||degree>6||groups.some(g=>g.qs.length+2*g.edges.length>20))throw new BridgeBoundary('Bridge local width/degree limit');const bytes=groups.reduce((sum,g)=>sum+256*2**(g.qs.length+g.edges.length),0);if(bytes>maxBytes)throw new BridgeBoundary('Bridge coefficient estimate exceeds budget');return {groups,map,at,bonds,bytes,width,degree};
}
export class BridgeFactor {
 constructor(n,gates,{maxBytes=67108864,maxWork=50000000}={}){if(!Number.isSafeInteger(maxWork)||maxWork<1)throw Error('Invalid bridge work budget');this.n=n;this.plan=bridgePlan(n,gates,maxBytes);this.gates=gates;this.groups=this.plan.groups;this.work=0;this.maxWork=maxWork;this.operations=0;this.mode='interval-bridge-forest';for(const g of this.groups){g.states=Array.from({length:2**g.edges.length},()=>Array.from({length:2**g.qs.length},(_,x)=>x?Z:O))}}
 charge(k){this.work+=k;if(this.work>this.maxWork)throw new BridgeBoundary('Bridge work budget')}
 apply(g){operands(this.n,g);if(g!==this.gates[this.operations])throw Error('Gate sequence differs from planned circuit');const [a,q]=this.plan.map[g.q],c=g.controls[0],b=c===undefined?a:this.plan.map[c][0],p=c===undefined?-1:this.plan.map[c][1],m=g.name==='swap'?null:fixedMatrix(g),bond=this.plan.at.get(this.operations);
 const transform=(group,q,ctrl,m,branch=-1)=>{for(let k=0;k<group.states.length;k++){const v=group.states[k];this.charge(v.length);if(branch>=0&&!(k&(1<<branch)))continue;for(let x=0;x<v.length;x++)if(!(x&(1<<q))&&(ctrl<0||(x&(1<<ctrl)))){const y=x|(1<<q);if(m===null){if(ctrl>=0&&!(x&(1<<ctrl)))continue;const z=(x^(1<<ctrl))|(1<<q);[v[x],v[z]]=[v[z],v[x]]}else [v[x],v[y]]=local([v[x],v[y]],m)}}};
 if(bond){const caa=this.groups[b],tar=this.groups[a],cb=b===bond.a?bond.pa:bond.pb,tb=a===bond.a?bond.pa:bond.pb;for(let k=0;k<caa.states.length;k++){const v=caa.states[k],bit=(k>>cb)&1;this.charge(v.length);for(let x=0;x<v.length;x++)if(((x>>p)&1)!==bit)v[x]=Z}transform(tar,q,-1,m,tb);bond.active=true}
 else{if(a!==b)throw Error('Non-bridge gate crosses blocks');transform(this.groups[a],q,p,m)}this.operations++}
 contract(bits,pauli){const double=pauli!==null,dim=double?4:2,visited=new Set();let total=O;
 const localValue=(g,k,l)=>{const ket=g.states[k];if(!double){let i=0;for(let j=0;j<g.qs.length;j++)if(bits[this.n-1-g.qs[j]]==='1')i|=1<<j;return ket[i]}const bra=g.states[l];let flip=0,z=0,ys=0;for(let j=0;j<g.qs.length;j++){const p=pauli[this.n-1-g.qs[j]];if(p==='X'||p==='Y')flip|=1<<j;if(p==='Y'||p==='Z')z|=1<<j;if(p==='Y')ys++}let out=Z;this.charge(ket.length);for(let x=0;x<ket.length;x++){let val=cm(cj(bra[x^flip]),ket[x]);for(let j=0;j<ys%4;j++)val=timesI(val);let t=x&z,par=0;while(t){t&=t-1;par^=1}out=ca(out,par?cn(val):val)}return out};
 const visit=(idx,parent)=>{if(visited.has(idx))throw Error('Bridge graph not a forest');visited.add(idx);const g=this.groups[idx],child=[];let pp=-1;for(let j=0;j<g.edges.length;j++){const e=g.edges[j];if(!e.active)continue;if(e===parent){pp=j;continue}child.push([j,visit(e.a===idx?e.b:e.a,e)])}const active=g.edges.map((e,j)=>e.active?j:-1).filter(j=>j>=0),out=Array(pp<0?1:dim).fill(Z);for(let mask=0;mask<dim**active.length;mask++){let p=mask,k=0,l=0,o=0,weight=O;for(const j of active){const x=p%dim;p=Math.floor(p/dim);k|=(x&1)<<j;if(double)l|=(x>>1)<<j;if(j===pp)o=x;else{const v=child.find(c=>c[0]===j)[1];weight=cm(weight,v[x])}}this.charge(active.length+1);if(!zero(weight))out[o]=ca(out[o],cm(weight,localValue(g,k,l)))}return out};
 for(let i=0;i<this.groups.length;i++)if(!visited.has(i))total=cm(total,visit(i,null)[0]);return result(double?[total[0],iz]:total)}
 amplitude(bits){if(typeof bits!=='string'||bits.length!==this.n||!/^[01]+$/.test(bits))throw Error('Invalid bridge bits');return this.contract(bits,null)}
 expectation(p){if(typeof p!=='string'||p.length!==this.n||!/^[IXYZ]+$/.test(p))throw Error('Invalid bridge Pauli');return this.contract(null,p)}
 norm(){return this.expectation('I'.repeat(this.n))}
 stats(){return {mode:this.mode,gates:this.operations,qubits:this.n,blocks:this.groups.length,bridges:this.plan.bonds.length,activeBridges:this.plan.bonds.filter(e=>e.active).length,maxBlockWidth:this.plan.width,maxBlockDegree:this.plan.degree,estimatedCoefficientBytes:this.plan.bytes,work:this.work,precision:'192-bit outward interval; full coherent bridge sums'}}
}
