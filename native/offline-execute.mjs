// Local numerical worker for independently instrumented headless execution.
import {readFileSync,openSync,closeSync} from 'node:fs';
import {FrameFactorDSIQ} from '../apps/web/public/dsiq/frame-factor.mjs';
import {ContractionState} from '../apps/web/public/dsiq/contract-state.mjs';
import {FactorDSIQ} from '../apps/web/public/dsiq/factor.mjs';
import {parityAmplitude} from '../apps/web/public/dsiq/parity-contraction.mjs';
import {exactDyadicAmplitude} from '../apps/web/public/dsiq/contraction.mjs';
function proc(path){return Object.fromEntries(readFileSync(path,'utf8').split('\n').filter(x=>x.includes(':')).map(x=>{const [k,...v]=x.split(':');return [k,v.join(':').trim()]}))}
try{
 const input=JSON.parse(readFileSync(0,'utf8')), {n,gates,mode,bits='0'.repeat(n),maxBytes=67108864,maxWork=500000000,pauli,masks=[]}=input;
 if(!Array.isArray(gates)||gates.length>100000||!Array.isArray(masks)||masks.length>1000||maxBytes>536870912||maxWork>1000000000)throw Error('Invalid offline request');
 let diskWriteDenied=false;try{const fd=openSync('/tmp','w');closeSync(fd)}catch(e){diskWriteDenied=e.code==='EPERM'} // read-only policy must reject before filesystem even sees the directory
 const beforeIO=proc('/proc/self/io'),beforeUsage=process.resourceUsage(),start=performance.now(),cpu=process.cpuUsage();let amplitude,norm=null,expectation=null,marginals=[],stats={},checkpoints=[];
 if(mode==='frame'){const d=new FrameFactorDSIQ(n,gates,{maxBytes,maxWork});for(const _ of d.execute()){}amplitude=d.amplitude(bits);norm=d.norm();if(pauli)expectation=d.expectation(pauli);stats=d.stats()}else if(mode==='contracted'){const d=new ContractionState(n,gates,{maxBytes,maxWork});amplitude=d.amplitude(bits);norm=d.norm();if(pauli)expectation=d.expectation(pauli);for(const m of masks)marginals.push(d.marginal(m));stats=d.stats()}
 else if(mode==='factor'){const d=new FactorDSIQ(n,gates,{maxBytes});for(let j=0;j<gates.length;j++){d.apply(gates[j]);if((j+1)%Math.max(1,Math.floor(gates.length/100))===0||j===gates.length-1)checkpoints.push({gate:j+1,norm:d.norm()})}amplitude=d.amplitude(bits);norm=d.norm();if(pauli)expectation=d.expectation(pauli);stats=d.stats()}
 else if(mode==='parity'){amplitude=parityAmplitude(n,gates,bits,{maxBytes,maxWork,ordering:'search'});stats={mode:amplitude.mode,peakTensorBytes:amplitude.peakTensorBytes,work:amplitude.work}}
 else if(mode==='dyadic'){amplitude=exactDyadicAmplitude(n,gates,bits,{maxBytes,maxWork});stats={mode:amplitude.mode,peakDyadicPayloadBytes:amplitude.peakDyadicPayloadBytes,work:amplitude.work}}
 else throw Error('Unknown offline mode');
 const usage=process.resourceUsage(),memory=process.memoryUsage(),status=proc('/proc/self/status'),io=proc('/proc/self/io'),limit=readFileSync('/proc/self/limits','utf8').split('\n').find(s=>s.startsWith('Max address space'));
 const result={amplitude,norm,expectation,marginals,stats,checkpoints};const guard=(_,v)=>{if(typeof v==='number'&&!Number.isFinite(v))throw Error('Nonfinite result rejected');return v};
 console.log(JSON.stringify({result,audit:{elapsedMs:performance.now()-start,cpuMicros:process.cpuUsage(cpu),usage,memory,vmHwm:status.VmHWM,vmSwap:status.VmSwap,seccomp:status.Seccomp,seccompFilters:status.Seccomp_filters,io,computeIODelta:Object.fromEntries(['read_bytes','write_bytes'].map(k=>[k,Number(io[k])-Number(beforeIO[k])])),computeMajorFaults:usage.majorPageFault-beforeUsage.majorPageFault,addressSpaceLimit:limit,diskWriteDenied}},guard));
}catch(e){console.error('DSIQ offline worker:',e.message);process.exitCode=2}
