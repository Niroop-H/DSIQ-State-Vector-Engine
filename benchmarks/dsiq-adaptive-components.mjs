import {executeAdaptive} from '../apps/web/public/dsiq/adaptive.mjs';
const gs=[];const n=20;
for(let d=0;d<8;d++)for(let off=0;off<n;off+=5){for(let q=0;q<5;q++)gs.push({name:['rx','ry','rz'][(d+q)%3],q:off+q,controls:[],theta:(d+q)*.031});for(let q=d%2;q<4;q+=2)gs.push({name:'cx',q:off+q+1,controls:[off+q]});}
let t=performance.now(),it=executeAdaptive(n,gs,32768,{query:'0'.repeat(n),shots:0,precision:'fp64'}),step;do {step=it.next()}while(!step.done);let d=step.value;console.log(JSON.stringify({ms:performance.now()-t,mode:d.mode,gates:gs.length,stats:d.stats(),amp:d.amplitude('0'.repeat(n))}));
