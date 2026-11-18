import assert from 'node:assert/strict';
import {buildRankFrame,buildFrame,FrameBudget} from '../apps/web/public/dsiq/frame-factor.mjs';
import {frameDifferential} from './frame-factor.test.mjs';
import {gate,near,reference} from './factor.test.mjs';
import {spawnSync} from 'node:child_process';
import {rng} from '../apps/web/public/dsiq/worker.mjs';
const bits=(n,x)=>x.toString(2).padStart(n,'0');
// Independently evaluate the k active physical wires and encode their full
// state using the known classical linear map. No frame kernel in the oracle.
export function encoded(n=1024,k=8,tCount=1000,seed=693167){
 const r=rng(seed),network=[],masks=[],gs=[],local=[];
 for(let q=k;q<n;q++) {let mask=1+Math.floor(r()*(2**k-1));masks.push(mask);for(let j=0;j<k;j++)if(mask>>j&1)network.push(gate('cx',q,[j]));}
 // Two nontrivial encoders surround an actual sequence of interleaved
 // H/T, arbitrary rotations and entanglers. The intermediate frame has
 // large physical Pauli supports even though only k flip dimensions exist.
 gs.push(...network);for(let i=0;i<tCount;i++){const q=Math.floor(r()*k),c=(q+1+Math.floor(r()*(k-1)))%k;
 local.push(gate('h',q),gate(i%2?'t':'tdg',q),gate('ry',q,[],{theta:r()*2-1}));if(i%3===0)local.push(gate('cx',q,[c]));if(i%7===0)local.push(gate('rz',q,[],{theta:r()*2-1}));}
 gs.push(...local,...network);let oldBoundary=false;try{buildFrame(n,gs,{maxBytes:67108864})}catch(e){if(!(e instanceof FrameBudget))throw e;oldBoundary=true}assert.ok(oldBoundary);
 const t=performance.now(),d=buildRankFrame(n,gs,{maxBytes:67108864,maxWork:500000000}),ms=performance.now()-t;
 assert.equal(d.plan.flipRank,k);assert.ok(d.plan.largest<=k);near(d.norm(),1,1e-11);const oracle=spawnSync('python',[new URL('./rank-reference.py',import.meta.url).pathname],{input:JSON.stringify({n:k,gates:local}),encoding:'utf8',timeout:120000,maxBuffer:1024*1024});assert.equal(oracle.status,0,oracle.stderr);const ref=JSON.parse(oracle.stdout),v=ref.amplitudes;near(ref.norm,1,1e-13);let max=0,maxPhase=0;const queries=[];
 for(let x=0;x<v.length;x++){let y=BigInt(x);for(let p=0;p<masks.length;p++){let z=x&masks[p],par=0;while(z){z&=z-1;par^=1}if(par)y|=1n<<BigInt(p+k)} const b=bits(n,y),a=d.amplitude(b),w=v[x],e=Math.hypot(a.real-w[0],a.imag-w[1]);near(e,0,1e-13);max=Math.max(e,max);const m=Math.hypot(...w);if(m>1e-8){const p=Math.atan2(w[1],w[0]);const e=Math.abs(Math.atan2(Math.sin(a.phase-p),Math.cos(a.phase-p)));near(e,0,1e-10);maxPhase=Math.max(e,maxPhase)}if(x<16){const bad=bits(n,y^(1n<<BigInt(n-1)));const b=d.amplitude(bad);assert.equal(b.log2Magnitude,null)}queries.push({bits:b,real:a.real,imag:a.imag});}
 // Sample the complete encoded output, including nonmonomial Clifford frames.
 const sampler=d.sampler(),lookup=new Map(queries.map((q,i)=>[q.bits,i])),freq=new Uint32Array(v.length),draws=n===1024?512:2048;let probabilityMax=0;
 for(let j=0;j<draws;j++){const b=sampler.sample(r);assert.ok(lookup.has(b),'Sample outside encoded support');freq[lookup.get(b)]++}
 if(sampler.probabilityOf)for(let j=0;j<queries.length;j++){const p=sampler.probabilityOf(queries[j].bits).probability,expected=v[j][0]**2+v[j][1]**2;near(p,expected,1e-12);probabilityMax=Math.max(probabilityMax,Math.abs(p-expected))}
 return {n,k,tCount,gates:gs.length,oracleAmplitudes:v.length,oracleMantissaBits:ref.mantissaBits,referenceNorm:ref.norm,draws,probabilityMax,zeroSupportQueries:16,maxError:max,maxPhaseError:maxPhase,ms,oldBoundary,stats:d.stats()};
}
export function rankMeasurements(){const r=rng(175739);let max=0,queries=0,circuits=0,draws=0;for(let j=0;j<40;j++){const n=6,gs=[];for(let a=0;a<48;a++){const q=Math.floor(r()*n),c=(q+1+Math.floor(r()*(n-1)))%n,name=['h','rx','ry','rz','t','tdg','cx','cz'][Math.floor(r()*8)];gs.push(gate(name,q,['cx','cz'].includes(name)?[c]:[],{theta:r()*3-1.5}))}gs.push(gate('h',j%n));const d=buildRankFrame(n,gs),v=reference(n,gs);if(d.monomial)continue;const sampler=d.sampler();let sum=0;for(let x=0;x<v.length;x++){const a=sampler.probabilityOf(bits(n,x)).probability,b=v[x][0]**2+v[x][1]**2;near(a,b,1e-12);max=Math.max(max,Math.abs(a-b));sum+=a;queries++}near(sum,1,1e-12);for(let i=0;i<128;i++){const x=parseInt(sampler.sample(r),2);assert.ok(v[x][0]**2+v[x][1]**2>0);draws++}circuits++}assert.ok(circuits>=30);return {circuits,queries,draws,maxProbabilityError:max}}
export function rankSuite(){const differential=frameDifferential(buildRankFrame),wide=encoded(),scaling=[500,1000,5000].map(t=>encoded(100,5,t,4236));return {differential,wide,scaling,measurement:rankMeasurements()}}
if(process.argv[1]===new URL(import.meta.url).pathname)console.log(JSON.stringify(rankSuite(),null,2));
