// Optional exact-in-real-arithmetic fusion of consecutive single-qubit gates.
// No cancellation inference for verification workloads; audit reports rounded
// matrix products, gate count and distinct compile/execute timings.
import {matrix} from './engine.mjs';
import {FactorDSIQ,factorPlan} from './factor.mjs';
const mul=(a,b)=>[a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0]],add=(a,b)=>[a[0]+b[0],a[1]+b[1]];
export function compileFactorProgram(n,gates,options={}){const plan=factorPlan(n,gates,options.precision??'fp64',options.maxBytes??4194304),compiled=[];for(const g of gates){const prev=compiled.at(-1);if(g.controls.length===0&&g.name!=='swap'){const m=matrix(g);if(prev?.matrix&&prev.q===g.q){prev.matrix=Array.from({length:4},(_,i)=>{const r=Math.floor(i/2),c=i%2;return add(mul(m[2*r],prev.matrix[c]),mul(m[2*r+1],prev.matrix[c+2]))});prev.sourceCount++}else compiled.push({q:g.q,matrix:m,sourceCount:1})}else compiled.push({gate:g,sourceCount:1})}return {n,gates,options,compiled,plan,sourceCount:gates.length}}
export function executeFactorProgram(p){const d=new FactorDSIQ(p.n,p.gates,p.options);for(const op of p.compiled)if(op.matrix)d.applyUnitary([op.q],op.matrix);else d.apply(op.gate);return d}
