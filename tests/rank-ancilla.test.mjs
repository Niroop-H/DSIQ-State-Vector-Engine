import assert from 'node:assert/strict';
import {buildRankFrame} from '../apps/web/public/dsiq/frame-factor.mjs';
import {gate,near,reference} from './factor.test.mjs';
import {rng} from '../apps/web/public/dsiq/worker.mjs';
// Independent formula: after the controlled parity fanout, H on every
// ancilla gives uniform classical outcomes conditional on the data word,
// with an analytically determined phase. All n output bits are sampled.
const n=1024,k=4,r=rng(187351),local=[],network=[],masks=[];
for(let j=0;j<120;j++){let q=j%k;local.push(gate('ry',q,[],{theta:r()*2-1}),gate('t',q),gate('h',q));if(j%3===0)local.push(gate('cx',(q+1)%k,[q]));}
for(let q=k;q<n;q++){const m=1+Math.floor(r()*(2**k-1));masks.push(m);for(let j=0;j<k;j++)if(m>>j&1)network.push(gate('cx',q,[j]));}
const gs=[...local,...network,...Array.from({length:n-k},(_,j)=>gate('h',j+k))],d=buildRankFrame(n,gs,{maxBytes:67108864,maxWork:500000000}),v=reference(k,local),sampler=d.sampler();
assert.equal(d.plan.flipRank,k);assert.equal(d.rankSampling.inactiveUniformBits,n-k);assert.equal(d.rankSampling.logicalMeasurements,k);const shots=1024,seen=new Set(),count=new Uint32Array(2**k);let maxLog=0,probabilityQueries=0,uniformOnes=0;
for(let j=0;j<shots;j++){const b=sampler.sample(r),x=parseInt(b.slice(-k),2);count[x]++;seen.add(b);for(const c of b.slice(0,n-k))uniformOnes+=c==='1';if(j<32){const p=sampler.probabilityOf(b),expected=Math.log2(v[x][0]**2+v[x][1]**2)-(n-k);near(p.log2Probability,expected,1e-10);maxLog=Math.max(maxLog,Math.abs(p.log2Probability-expected));probabilityQueries++}}
assert.equal(seen.size,shots);let maxDeviation=0;for(let i=0;i<count.length;i++){const p=v[i][0]**2+v[i][1]**2;const delta=Math.abs(count[i]/shots-p),bound=6*Math.sqrt(p*(1-p)/shots)+6/shots;assert.ok(delta<bound);maxDeviation=Math.max(maxDeviation,delta)}assert.ok(Math.abs(uniformOnes/(shots*(n-k))-.5)<.003);
console.log(JSON.stringify({qubits:n,gates:gs.length,shots,unique:seen.size,probabilityQueries,maxLog2ProbabilityError:maxLog,uniformInactiveOnesFraction:uniformOnes/(shots*(n-k)),maxDataFrequencyDeviation:maxDeviation,...d.stats()},null,2));
