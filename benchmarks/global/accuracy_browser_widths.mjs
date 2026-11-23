import {executeAdaptive} from '../../apps/web/public/dsiq/adaptive.mjs';

const rows=[];
function finish(iterator) {
  let step=iterator.next();
  while (!step.done) step=iterator.next();
  return step.value;
}
for (let n=1;n<=100;n++) {
  const theta=0.61+n/251;
  const gates=[{name:'ry',q:0,theta,controls:[]}];
  for(let q=1;q<n;q++) gates.push({name:'cx',q,controls:[q-1]});
  let sum=0, mask=0n;
  for(let q=0;q<n;q++){
    const angle=Math.sin(q+0.1*n);
    sum+=angle;
    gates.push({name:'rz',q,theta:angle,controls:[]});
    if(q%3===0){gates.push({name:'x',q,controls:[]});mask|=1n<<BigInt(q);}
  }
  try {
    const state=finish(executeAdaptive(n,gates,32768,{shots:0,precision:'fp64'}));
    const universe=(1n<<BigInt(n))-1n;
    const probes=new Set([mask,mask^universe,mask^1n,(mask^universe)^1n]);
    let maxAbs=0,maxRelative=0,zeroLeakage=0;
    for(const id of probes) {
      const bits=id.toString(2).padStart(n,'0');
      const got=state.mode==='replay'?finish(state.replay(bits,8192,5000000)):state.amplitude(bits);
      const magnitude=id===mask?Math.cos(theta/2):id===(mask^universe)?Math.sin(theta/2):0;
      const phase=id===mask?-sum/2:sum/2;
      const err=Math.hypot(got.real-magnitude*Math.cos(phase),got.imag-magnitude*Math.sin(phase));
      maxAbs=Math.max(maxAbs,err);
      if(magnitude) maxRelative=Math.max(maxRelative,err/magnitude);
      else zeroLeakage=Math.max(zeroLeakage,err);
    }
    const normError=Math.abs(state.norm()-1);
    rows.push({n,mode:state.mode,probes:probes.size,maxAbs,maxRelative,zeroLeakage,normError,
               passed:maxAbs<1e-13 && maxRelative<1e-9 && normError<1e-12});
  } catch(error) {rows.push({n,passed:false,error:error.message});}
}
console.log(JSON.stringify(rows));
if(rows.some(r=>!r.passed))process.exitCode=1;
