// Export closed, exact 192-bit grid enclosures for native ball contraction.
import {readFileSync} from 'node:fs';
import {fixedMatrix} from '../apps/web/public/dsiq/fixed-interval.mjs';
const gs=JSON.parse(readFileSync(0,'utf8'));
if(!Array.isArray(gs)||gs.length>100000)throw Error('Invalid gate matrix request');
const result=gs.map(g=>{if(g.piTheta||g.piPhi||g.piLambda)throw Error('Rational pi not admitted in this certificate path');return fixedMatrix(g)});
console.log(JSON.stringify(result,(_,v)=>typeof v==='bigint'?v.toString():v));
