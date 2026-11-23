import fs from 'node:fs';
import {performance} from 'node:perf_hooks';
import {executeAdaptive} from '../../apps/web/public/dsiq/adaptive.mjs';
const {n,gates,indices}=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const start=performance.now();
const iter=executeAdaptive(n,gates,32768,{shots:0,precision:'fp64'});
let step;
do {step=iter.next();} while(!step.done);
const state=step.value;
const values=indices.map(i=>{
  const a=state.amplitude(i.toString(2).padStart(n,'0'));
  return [a.real,a.imag];
});
console.log(JSON.stringify({ms:performance.now()-start,mode:state.mode,values}));
