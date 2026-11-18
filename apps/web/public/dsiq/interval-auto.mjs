// Lossless structure-driven selection. No test identifiers or references.
import {IntervalProduct,ProductBoundary} from './interval-product.mjs';
import {BridgeFactor,BridgeBoundary} from './bridge-factor.mjs';
export function planIntervalState(n,gates,opts,onEvent=()=>{}){
 // Preserve existing symbolic rational-pi semantics and unsupported-angle routes.
 if(gates.some(g=>g.piTheta||g.piPhi||g.piLambda||['theta','phi','lambda'].some(k=>g[k]!==undefined&&(!Number.isFinite(g[k])||Math.abs(g[k])>1e6))))return null;
 try{return new BridgeFactor(n,gates,opts)}catch(e){if(!(e instanceof BridgeBoundary||e instanceof ProductBoundary))throw e;onEvent('representation-boundary',{reason:e.message})}
 try{const probe=new IntervalProduct(n,opts);for(const g of gates)probe.apply(g);const left=opts.maxWork-probe.work;if(left<=0)throw new ProductBoundary('Preflight work budget');onEvent('preflight',{work:probe.work});return new IntervalProduct(n,{...opts,maxWork:left})}catch(e){if(!(e instanceof ProductBoundary))throw e;onEvent('representation-boundary',{reason:e.message});return null}
}
