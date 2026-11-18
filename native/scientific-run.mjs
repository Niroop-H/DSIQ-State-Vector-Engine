// Audited public headless numerical interface. Never returns an uncertified
// amplitude or observable when requireCertificate is enabled. CPU only.
import {readFileSync,writeSync} from 'node:fs';
import {planIntervalState} from '../apps/web/public/dsiq/interval-auto.mjs';
import {createHash} from 'node:crypto';
import {executeAdaptive} from '../apps/web/public/dsiq/adaptive.mjs';
import {CertifiedFactorDSIQ} from '../apps/web/public/dsiq/certified-factor.mjs';
import {CertifiedContraction} from '../apps/web/public/dsiq/certified-contraction.mjs';
import {FactorBudget} from '../apps/web/public/dsiq/factor.mjs';
import {ContractionState} from '../apps/web/public/dsiq/contract-state.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
const fail=msg=>{throw Error(msg)};
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const asComplex=v=>typeof v==='number'?{real:v,imag:0}:v;
const positive=(x,max)=>Number.isSafeInteger(x)&&x>0&&x<=max;
const modes=['adaptive','contracted','certified-factor','certified-contraction','certified-auto'];
const started=performance.now(),cpuStart=process.cpuUsage();
let raw='',request,events=[],completed=0,applied=0,outputs=[],status='FAILED',error=null;
function metrics(){const m=process.memoryUsage(),u=process.resourceUsage();return {elapsedMs:performance.now()-started,cpuMicros:process.cpuUsage(cpuStart),rssBytes:m.rss,peakRssKiB:u.maxRSS,heapUsedBytes:m.heapUsed,externalBytes:m.external,arrayBuffersBytes:m.arrayBuffers};}
function journal(kind,data){if(process.env.DSIQ_STREAM_AUDIT==='1')writeSync(2,'DSIQ-AUDIT '+JSON.stringify({kind,data})+'\n')}
function event(prefix,kind,details={}){const e={sequence:events.length,prefix,kind,...metrics(),...details};events.push(e);journal('event',e)}
function ensure(v){return JSON.parse(JSON.stringify(v,(_,x)=>{if(typeof x==='number'&&!Number.isFinite(x))fail('Nonfinite scientific output');return x}))}
let checkpointEvery=1;
function checkQuery(q,n,len){if(!q||typeof q.id!=='string'||!q.id||q.id.length>128||!['amplitude','pauli','norm'].includes(q.kind)||!Number.isSafeInteger(q.prefix)||q.prefix<0||q.prefix>len)fail('Invalid query');if(q.kind==='amplitude'&&(typeof q.bits!=='string'||q.bits.length!==n||!/^[01]+$/.test(q.bits)))fail('Invalid bitstring');if(q.kind==='pauli'&&(typeof q.pauli!=='string'||q.pauli.length!==n||!/^[IXYZ]+$/.test(q.pauli)))fail('Invalid Pauli');}
function make(n,gs,method,opts,needCert){if(method==='certified-factor'||method==='certified-auto'){try{const d=new CertifiedFactorDSIQ(n,gs,opts);for(const g of gs)d.apply(g);return d}catch(e){if(method!=='certified-auto'||!(e instanceof FactorBudget))throw e}}
 if(method==='certified-contraction'||method==='certified-auto')return new CertifiedContraction(n,gs,opts);
 if(needCert)fail('Uncertified method refused');if(method==='contracted')return new ContractionState(n,gs,opts);
 const it=executeAdaptive(n,gs,opts.maxNodes,{shots:0,maxCoefficientBytes:opts.maxBytes,maxWork:opts.maxWork});let step;while(!(step=it.next()).done){}const d=step.value;if(d.mode==='replay')fail('No queryable state completed');return d;
}
function query(d,q,n,needCert){let a=asComplex(q.kind==='amplitude'?d.amplitude(q.bits):q.kind==='pauli'?d.expectation(q.pauli):typeof d.norm==='function'?d.norm():d.expectation('I'.repeat(n)));if(!finite(a?.real)||!finite(a?.imag??0))fail('Invalid numerical output');if(needCert&&(!finite(a.absoluteErrorBound)||a.absoluteErrorBound<0))fail('No finite error certificate');return ensure(a)}
try{
 raw=readFileSync(0,'utf8');if(raw.length>32*1024**2)fail('Request too large');request=JSON.parse(raw);const {n,gates,queries,method='certified-auto',requireCertificate=true,maxBytes=67108864,maxWork=50000000,maxNodes=32768}=request;checkpointEvery=request.checkpointEvery??1;
 if(!positive(n,4096)||!Array.isArray(gates)||gates.length>100000||!Array.isArray(queries)||!queries.length||queries.length>10000||!modes.includes(method)||typeof requireCertificate!=='boolean'||!positive(maxBytes,536870912)||maxBytes<256||!positive(maxWork,1000000000)||!positive(checkpointEvery,100000)||!positive(maxNodes,1000000)||maxNodes<n+1)fail('Invalid request or resource limit');
 if(requireCertificate&&!method.startsWith('certified-'))fail('Certified execution may not use an uncertified method');if(new Set(queries.map(q=>q?.id)).size!==queries.length)fail('Duplicate query IDs');for(const q of queries)checkQuery(q,n,gates.length);
 const opts={maxBytes,maxWork,maxNodes,maxVariables:100000};const prefixes=new Set([0,gates.length,...queries.map(q=>q.prefix)]);for(let p=checkpointEvery;p<gates.length;p+=checkpointEvery)prefixes.add(p);if(prefixes.size>10001)fail('Too many required checkpoints');
 journal('begin',{inputSHA256:sha(raw),runtime:process.version,requestedGates:gates.length,checkpointEvery});
 // Certified-factor incremental evolution uses its preplanned complete circuit;
 // each norm is measured on the actual intermediate state, not assumed = 1.
 let d=null;
 // Select by gate signatures and graph structure, never by circuit IDs or answers.
 // Explicit rational-pi metadata retains the existing symbolic execution route.
 if(['adaptive','certified-auto'].includes(method))d=planIntervalState(n,gates,opts,(kind,data)=>event(0,kind,data));
 if(!d&&(method==='certified-factor'||method==='certified-auto')){try{d=new CertifiedFactorDSIQ(n,gates,opts)}catch(e){if(method!=='certified-auto'||!(e instanceof FactorBudget))throw e;event(0,'representation-boundary',{reason:e.message})}}
 event(0,'start',{requestedGates:gates.length,checkpointEvery,requireCertificate});
 for(const p of [...prefixes].sort((a,b)=>a-b)){
  let state;if(d){for(let j=completed;j<p;j++){d.apply(gates[j]);applied=j+1}state=d}else{state=make(n,gates.slice(0,p),method==='certified-auto'?'certified-contraction':method,opts,requireCertificate)}
  const norm=query(state,{kind:'norm'},n,requireCertificate);completed=p;event(p,'checkpoint',{norm,stats:ensure(state.stats()),execution:d?'incremental':'prefix evaluation'});
  for(const q of queries.filter(q=>q.prefix===p)){const value=query(state,q,n,requireCertificate);const record={id:q.id,kind:q.kind,prefix:p,value};outputs.push(record);journal('output',record);event(p,'query',{id:q.id,certified:finite(value.absoluteErrorBound)})}
 }
 if(outputs.length!==queries.length)fail('Missing query outputs');status='COMPLETED';
}catch(e){error=String(e.message??e);event(completed,'failure',{reason:error});}
const report={schema:'DSIQ-scientific-run-v1',status,error,inputSHA256:sha(raw),runtime:process.version,host:{platform:process.platform,arch:process.arch},requestedGates:request?.gates?.length??null,completedPrefix:completed,appliedPrefix:applied,checkpointEvery,outputs,events,metrics:metrics(),coverage:{cpuCycles:null,cpuCyclesReason:'Use the Linux audit wrapper for hardware counter measurement',gpu:{used:false,cycles:null,reason:'CPU-only execution'},scope:'Headless unitary circuit query interface; not all browser/native representations'}};
console.log(JSON.stringify(report));if(status!=='COMPLETED')process.exitCode=1;
