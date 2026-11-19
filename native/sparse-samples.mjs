// Offline sampling of a bounded exact-support representation. No reference
// files or circuit IDs enter the worker; RNG seed is explicit and recorded.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {IntervalSparse} from '../apps/web/public/dsiq/interval-sparse.mjs';
const start=performance.now(),cpu=process.cpuUsage();
try{
 const raw=readFileSync(0,'utf8');if(raw.length>32*1024**2)throw Error('Input size limit');const {request:r,shots,seed}=JSON.parse(raw);
 if(!r||!Number.isSafeInteger(r.n)||r.n<1||r.n>4096||!Array.isArray(r.gates)||r.gates.length>100000||!Number.isSafeInteger(shots)||shots<1||shots>100000||typeof seed!=='string'||!/^[0-9a-f]{64}$/.test(seed))throw Error('Invalid sampling request');
 const opts={maxBytes:r.maxBytes??67108864,maxWork:r.maxWork??50000000,maxNodes:r.maxNodes??32768};if(!Number.isSafeInteger(opts.maxBytes)||opts.maxBytes<256||opts.maxBytes>536870912||!Number.isSafeInteger(opts.maxWork)||opts.maxWork<1||opts.maxWork>1000000000||!Number.isSafeInteger(opts.maxNodes)||opts.maxNodes<r.n+1||opts.maxNodes>1000000)throw Error('Invalid budget');
 if(r.gates.some(g=>g.piTheta||g.piPhi||g.piLambda))throw Error('Symbolic rational angle outside sparse sampler');
 const d=new IntervalSparse(r.n,r.gates,opts);for(const g of r.gates)d.apply(g);const norm=d.norm();const {outcomes,total,tvUpperBound}=d.distribution();
 // Rejection generates an exactly uniform integer in [0,total) from the
 // seeded hash stream, without floating-point probability or modulo bias.
 let counter=0n;const bits=total.toString(2).length,blocks=Math.ceil(bits/256),mask=(1n<<BigInt(bits))-1n;
 const draw=()=>{for(;;){let u=0n;for(let k=0;k<blocks;k++){const b=Buffer.alloc(8);b.writeBigUInt64BE(counter++);d.charge(1);const h=createHash('sha256').update('DSIQ-SHA256-COUNTER-v1\0').update(Buffer.from(seed,'hex')).update(b).digest('hex');u=(u<<256n)|BigInt('0x'+h);}u&=mask;if(u<total)return u;}};
 const counts=Object.create(null),bitstrings=[];for(let i=0;i<shots;i++){const u=draw();let l=0,h=outcomes.length;while(l<h){d.charge(1);const m=(l+h)>>1;if(u<outcomes[m].cumulative)h=m;else l=m+1;}const x=outcomes[l].bits;counts[x]=(counts[x]??0)+1;bitstrings.push(x);}
 const resource=process.resourceUsage();console.log(JSON.stringify({schema:'DSIQ-sparse-sampling-v1',status:'COMPLETED',inputSHA256:createHash('sha256').update(raw).digest('hex'),seed,rngAlgorithm:'SHA-256 seed/counter stream v1, rejection sampling; deterministic pseudorandom',shotsRequested:shots,shotsCompleted:shots,counts,bitstrings,measuredNorm:norm,distributionTVUpperBound:tvUpperBound,stats:d.stats(),elapsedMs:performance.now()-start,cpuMicros:process.cpuUsage(cpu),peakRssKiB:resource.maxRSS}));
}catch(e){console.log(JSON.stringify({schema:'DSIQ-sparse-sampling-v1',status:'FAILED',error:String(e.message??e)}));process.exitCode=1;}
