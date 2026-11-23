import fs from 'node:fs';
import {executeAdaptive} from '../../apps/web/public/dsiq/adaptive.mjs';

const {n,gates}=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const bits='0'.repeat(n);
const visitLimit=5000000;
function finish(iterator) {
  let step=iterator.next();
  while(!step.done) step=iterator.next();
  return step.value;
}
const state=finish(executeAdaptive(n,gates,32768,{shots:0,precision:'fp64'}));
try {
  const value=state.mode==='replay'
    ? finish(state.replay(bits,8192,visitLimit))
    : state.amplitude(bits);
  console.log(JSON.stringify({mode:state.mode,value}));
} catch (error) {
  console.log(JSON.stringify({mode:state.mode,visitLimit,error:error.message}));
  process.exitCode=2;
}
