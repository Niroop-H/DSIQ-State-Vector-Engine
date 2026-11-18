// DSIQ deterministic multi-start binary elimination planner. Only scopes are
// inspected; no amplitude values or target-circuit identities drive planning.
// Forecast includes the currently live coefficient arrays plus a new output.
export function planElimination(scopes,{trials=16,maxPlannerWork=100000000,seed=0x5d51,bytes=16}={}){
 if(!Number.isSafeInteger(trials)||trials<1||trials>128||!Number.isSafeInteger(maxPlannerWork)||maxPlannerWork<1)throw Error('Invalid planner budget');let work=0,best=null,completed=0,exhausted=false;
 function tick(n=1){work+=n;if(work>maxPlannerWork)throw Error('PLANNER_LIMIT')}
 function rng(s){let x=s>>>0;return ()=>{x=(x+0x6d2b79f5)>>>0;let t=x;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296}}
 for(let trial=0;trial<trials;trial++){try{
  const links=new Map(),factors=new Map(),adj=new Map(),order=[];let id=0,live=0,peak=0,width=0,ops=0;
  const insert=vars=>{const size=bytes*2**vars.length;live+=size;peak=Math.max(peak,live);if(!vars.length){live-=size;return}const f={vars,id:id++,size};factors.set(f.id,f);for(const v of vars){if(!links.has(v))links.set(v,new Set());links.get(v).add(f.id);if(!adj.has(v))adj.set(v,new Set())}for(let i=0;i<vars.length;i++)for(let j=i+1;j<vars.length;j++){adj.get(vars[i]).add(vars[j]);adj.get(vars[j]).add(vars[i]);tick()} };
  for(const s of scopes)insert(s);const random=rng(seed+trial*104729),policy=trial%4;
  while(links.size){let min=Infinity;for(const a of adj.values()){min=Math.min(min,a.size);tick()}let chosen=null,score=Infinity,tie=0;for(const [v,a] of adj){tick();const d=a.size;if(d>min+(policy===0?0:policy===1?2:policy===2?4:6))continue;let fill=0;if(policy!==0){const s=[...a];for(let i=0;i<s.length;i++)for(let j=i+1;j<s.length;j++){tick();if(!adj.get(s[i]).has(s[j]))fill++}}
   const cost=policy===0?d:policy===1?fill+.5*d:policy===2?fill+2*d:fill+Math.pow(d,1.25);const u=trial===0?0:random();if(cost<score||cost===score&&u>tie){chosen=v;score=cost;tie=u}}
   const ns=[...adj.get(chosen)],source=[...links.get(chosen)].map(i=>factors.get(i)),d=ns.length;order.push(chosen);width=Math.max(width,d);peak=Math.max(peak,live+bytes*2**d);ops+=2**(d+1)*source.length;
   // Once a candidate is strictly worse, its peak cannot improve.
   if(best&&peak>best.peakTensorBytes&&width>=best.maxSeparatorVariables)break;
   for(const f of source){live-=f.size;factors.delete(f.id);for(const v of f.vars)links.get(v).delete(f.id)}links.delete(chosen);adj.delete(chosen);for(const v of ns)adj.get(v).delete(chosen);insert(ns);
   // Every neighbor is present in the new factor; its other edges remain.
   tick(source.length+ns.length);
  }
  completed++;if(links.size===0){const p={order,peakTensorBytes:peak,maxSeparatorVariables:width,estimatedProducts:ops,trial,policy};if(!best||p.peakTensorBytes<best.peakTensorBytes||p.peakTensorBytes===best.peakTensorBytes&&p.estimatedProducts<best.estimatedProducts)best=p}
 }catch(e){if(e.message!=='PLANNER_LIMIT')throw e;exhausted=true;break}}
 if(!best)throw Error('No complete elimination plan within planner budget');return {...best,plannerWork:work,trialsCompleted:completed,plannerExhausted:exhausted}
}
