// DSIQ scientific workspace. All numerical output comes from worker.mjs.
const byId = id => document.getElementById(id);
const tabs = [...document.querySelectorAll('[data-tab]')];
const methods = {
  adaptive: 'Adaptive execution supports amplitude queries, Pauli observables, and seeded sampling when representation and budgets permit.',
  contracted: 'Contracted state evaluates amplitudes and observables through resource-bounded contraction. Sampling is available when the query budget permits.',
  frame: 'Clifford reference-frame factorization. Sampling may be unavailable for non-monomial final Clifford frames.',
  'rank-frame': 'Rank-reduced Clifford reference-frame factorization with a supported sampling path.',
  parity: 'Affine parity amplitude only. Set shots to zero and leave Pauli blank.',
  dyadic: 'Exact dyadic representation for amplitude queries. Set shots to zero and leave Pauli blank.',
  certified: 'Certified FP64 factor implementation. Error enclosure applies only to its admitted gate and numerical regime.',
  'certified-auto': 'Strict certified numerical queries. Sampling disabled; expects an admitted circuit and budget.',
  'certified-contraction': 'Certified connected contraction. Sampling disabled; expects an admitted circuit and budget.'
};
const noSampling = new Set(['parity','dyadic','certified-auto','certified-contraction']);
const amplitudeOnly = new Set(['parity','dyadic']);
let mainWorker = null;
let diagnosticWorker = null;
let lastEvidence = null;
let pending = false;
let diagnosticActive = false;
let diagnosticReject = null;
let runSequence = 0;

function activateTab(name){
  for(const button of tabs){const selected=button.dataset.tab===name;button.classList.toggle('active',selected);if(selected)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current')}
  for(const pane of document.querySelectorAll('.pane'))pane.classList.toggle('active',pane.id===name);
}
tabs.forEach(button=>button.addEventListener('click',()=>activateTab(button.dataset.tab)));

const ghz = n => `OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[${n}];\nh q[0];\n` + Array.from({length:n-1},(_,i)=>`cx q[${i}],q[${i+1}];`).join('\n');
const cases = {
  bell: {source:'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\ncx q[0],q[1];',query:'11',pauli:'XX',shots:128},
  ghz50: {source:ghz(50),query:'ones',pauli:'X'.repeat(50),shots:0},
  ghz100: {source:ghz(100),query:'ones',pauli:'X'.repeat(100),shots:0},
  interference: {source:'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\nh q[0];\nt q[0];\nh q[0];',query:'0',pauli:'Z',shots:128},
  product100: {source:'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[100];\nry(pi/3) q;',query:'zeros',pauli:'',shots:0}
};
function editorLines(){const s=byId('source').value;byId('editor-lines').textContent=`${s.split('\n').length} lines  /  ${new Blob([s]).size.toLocaleString()} bytes`}
function useTemplate(){
  if(pending)return;
  const entry=cases[byId('template').value];if(!entry)return;
  byId('source').value=entry.source;byId('query').value=entry.query;byId('pauli').value=entry.pauli;byId('shots').value=String(entry.shots);
  byId('method').value='adaptive';byId('precision').value='fp64';applyMethodConstraints();editorLines();
  byId('status-sub').textContent='Reference experiment loaded. Execute to calculate its result.';
}
byId('load-template').addEventListener('click',useTemplate);
byId('source').addEventListener('input',editorLines);

function applyMethodConstraints(){
  const method=byId('method').value;const precision=byId('precision');const shots=byId('shots');const pauli=byId('pauli');
  byId('method-note').textContent=methods[method]||'The requested method must be supported by the engine.';
  if(method!=='adaptive'){precision.value='fp64';precision.disabled=true}else precision.disabled=false;
  if(noSampling.has(method)){shots.value='0';shots.disabled=true}else shots.disabled=false;
  if(amplitudeOnly.has(method)){pauli.value='';pauli.disabled=true}else pauli.disabled=false;
}
byId('method').addEventListener('change',applyMethodConstraints);

function numericId(id){const n=Number(byId(id).value);if(!Number.isSafeInteger(n))throw Error(`${id}: supply a valid integer`);return n}
function getSettings(kind='full'){
  const source=byId('source').value;
  if(!source.trim())throw Error('Enter an OpenQASM circuit before executing.');
  if(new Blob([source]).size>750000)throw Error('Circuit source exceeds 750 KB.');
  const method=byId('method').value;
  const shots=kind==='full'?numericId('shots'):0;
  const pauli=kind==='amplitude'?'':byId('pauli').value.trim().toUpperCase();
  const data={source,bits:byId('query').value.trim(),maxNodes:numericId('budget'),shots,seed:numericId('seed'),pauli,maxReplayVisits:numericId('visits'),maxTensorBytes:numericId('tensorbytes'),maxSlices:numericId('slices'),precision:byId('precision').value,method:kind==='full'?method:'adaptive',ordering:byId('ordering').value,observableOnly:kind==='pauli',contractionOnly:kind==='amplitude'};
  if(!data.bits)throw Error('Enter a basis query: zeros, ones or a binary bitstring.');
  if(data.maxNodes<2||data.maxNodes>1000000)throw Error('DAG node budget must be 2–1,000,000.');
  if(data.maxReplayVisits<1||data.maxReplayVisits>1000000000)throw Error('Work limit must be 1–1,000,000,000.');
  if(data.maxTensorBytes<256||data.maxTensorBytes>536870912)throw Error('Coefficient-byte limit must be 256–536,870,912.');
  if(data.maxSlices<1||data.maxSlices>65536)throw Error('Maximum slices must be 1–65,536.');
  if(data.shots<0||data.shots>1024)throw Error('Shots must be between 0 and 1024.');
  if(data.seed<0||data.seed>4294967295)throw Error('PRNG seed must be in unsigned 32-bit range.');
  if(kind==='pauli'&&!pauli)throw Error('Pauli-only execution requires an observable.');
  if(data.method!=='adaptive'&&data.precision!=='fp64')throw Error('This method requires FP64 execution.');
  if(noSampling.has(data.method)&&shots>0)throw Error('This method requires zero shots.');
  if(amplitudeOnly.has(data.method)&&pauli)throw Error('Amplitude-only method cannot evaluate a Pauli observable.');
  return data;
}
function setBusy(active){pending=active;for(const id of ['run','observable','contraction','load-template'])byId(id).disabled=active;byId('cancel').disabled=!active;byId('export').disabled=active||!lastEvidence}
function status(message,sub='',error=false){byId('status').textContent=message;byId('status').classList.toggle('error',error);byId('status-sub').textContent=sub}
function progress(value){const bar=byId('progress');const fill=bar.firstElementChild;if(value===null){bar.classList.add('indeterminate');fill.style.width='40%';return}bar.classList.remove('indeterminate');fill.style.width=`${Math.max(0,Math.min(100,value*100))}%`}
function resetRunFields(){
  for(const id of ['n','gates','elapsed','mode'])byId(id).textContent='—';
  for(const id of ['query-out','amp-real','amp-imag','amp-log','amp-bound','norm','expectation','peak','shots-out'])byId(id).textContent='Not evaluated';
  byId('sample-count').textContent='NO DATA';byId('science-note').textContent='Waiting for numerical execution.';
  byId('histogram').replaceChildren();const note=document.createElement('p');note.className='inline-note';note.textContent='No sampled outcomes yet.';byId('histogram').append(note);
}
function scalar(v,places=12){
  if(v===null||v===undefined)return 'Not evaluated';
  if(typeof v!=='number')return String(v);
  if(!Number.isFinite(v))return 'Unavailable';
  if(v===0)return '0';
  if(Math.abs(v)>=1e6||Math.abs(v)<1e-5)return v.toExponential(9);
  return String(Number(v.toPrecision(places)));
}
function renderHistogram(counts,completed){
  const host=byId('histogram');host.replaceChildren();
  if(!completed||!counts||Object.keys(counts).length===0){const p=document.createElement('p');p.className='inline-note';p.textContent='Sampling was not performed for this execution.';host.append(p);byId('sample-count').textContent='0 SHOTS';return}
  const pairs=Object.entries(counts).filter(([key,value])=>typeof key==='string'&&Number.isFinite(value)&&value>=0).sort((a,b)=>b[1]-a[1]);
  const max=Math.max(1,...pairs.map(p=>p[1]));
  for(const [key,count] of pairs.slice(0,18)){
    const row=document.createElement('div');row.className='hist-row';
    const name=document.createElement('span');name.className='hist-label';name.title=key;name.textContent=key;
    const track=document.createElement('div');track.className='hist-track';
    const bar=document.createElement('div');bar.className='hist-bar';bar.style.width=`${100*count/max}%`;track.append(bar);
    const value=document.createElement('span');value.className='hist-value';value.textContent=String(count);
    row.append(name,track,value);host.append(row);
  }
  if(pairs.length>18){const other=document.createElement('p');other.className='micro';other.textContent=`${pairs.length-18} additional outcomes in evidence export.`;host.append(other)}
  byId('sample-count').textContent=`${completed.toLocaleString()} SHOTS / ${pairs.length} OUTCOMES`;
}
function renderResult(d){
  byId('n').textContent=scalar(d.qubits);byId('gates').textContent=scalar(d.gates);byId('elapsed').textContent=Number.isFinite(d.elapsedMs)?`${scalar(d.elapsedMs,7)} ms`:'Not evaluated';byId('mode').textContent=d.mode||'Not reported';
  byId('query-out').textContent=d.query??'Not evaluated';
  const a=d.amplitude||{};
  byId('amp-real').textContent=scalar(a.real);
  byId('amp-imag').textContent=scalar(a.imag);
  byId('amp-log').textContent=scalar(a.log2Magnitude);
  byId('amp-bound').textContent=Number.isFinite(a.absoluteErrorBound)?scalar(a.absoluteErrorBound):'Not reported for this method';
  const s=d.science||{};
  byId('norm').textContent=scalar(s.norm);
  byId('expectation').textContent=scalar(s.pauliExpectation);
  const peakKey=[['peakTensorBytes','coefficient bytes'],['coefficientBytes','coefficient bytes'],['peakDyadicPayloadBytes','coefficient bytes'],['peakRank','rank'],['peakNodes','DAG nodes'],['peakTerms','terms'],['phaseFactors','phase factors']].find(([k])=>d[k]!==undefined&&d[k]!==null);
  byId('peak').textContent=peakKey?`${Number(d[peakKey[0]]).toLocaleString()} ${peakKey[1]}`:'Not reported';
  byId('shots-out').textContent=scalar(d.shotsCompleted??0);
  byId('science-note').textContent=s.status||'No additional scientific note reported by worker.';
  renderHistogram(d.counts,d.shotsCompleted);
  byId('run-id').textContent=`RUN ${String(++runSequence).padStart(3,'0')}`;
  progress(1);status('Execution completed',`${d.mode||'Engine'} · ${scalar(d.elapsedMs,7)} ms · computed locally`);
}
async function sourceHash(source){const bytes=new TextEncoder().encode(source);const hash=await crypto.subtle.digest('SHA-256',bytes);return Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('')}
function cancelMain(){if(mainWorker){mainWorker.terminate();mainWorker=null}setBusy(false);progress(0);status('Execution cancelled','No partial values are treated as completed results.');byId('run-id').textContent='CANCELLED'}
function submit(kind){
  if(pending)return;
  let data;try{data=getSettings(kind)}catch(e){status('Input rejected',String(e.message||e),true);return}
  lastEvidence=null;resetRunFields();setBusy(true);progress(null);status('Executing in local worker','Compiling and evaluating the submitted OpenQASM source.');
  const worker=new Worker(new URL('./worker.mjs',import.meta.url),{type:'module'});mainWorker=worker;let completed=false;
  worker.onmessage=async event=>{
    if(mainWorker!==worker||completed)return;
    const msg=event.data;
    if(msg.error){completed=true;worker.terminate();mainWorker=null;progress(0);status('Execution failed',String(msg.error),true);setBusy(false);return}
    if(msg.result){completed=true;worker.terminate();mainWorker=null;const result=msg.result;renderResult(result);
      lastEvidence={schema:'DSIQ-scientific-workspace-v1',browserEngine:'DSIQ JavaScript research worker',timestampUTC:new Date().toISOString(),parameters:{...data},result};
      try{lastEvidence.sourceSHA256=await sourceHash(data.source)}catch(e){lastEvidence.digestError=String(e)}
      setBusy(false);return;
    }
    if(msg.stage==='compile'){const total=Number(msg.total)||0;const done=Number(msg.completed)||0;progress(total?done/total:null);status('Executing circuit',total?`${done.toLocaleString()} / ${total.toLocaleString()} expanded operations`:'Preparing state representation');return}
    if(msg.stage==='contraction-boundary'){progress(null);status('Evaluating fallback representation',String(msg.reason||'Resource boundary reached'));return}
    if(msg.stage==='replay'){progress(null);status('Evaluating coherent replay',`${Number(msg.visits||0).toLocaleString()} visited paths`);return}
    progress(null);status('Worker computation in progress',msg.stage?String(msg.stage):'Evaluating bounded operation');
  };
  worker.onerror=e=>{if(mainWorker!==worker||completed)return;completed=true;worker.terminate();mainWorker=null;progress(0);status('Worker error',e.message||'Module execution failed',true);setBusy(false)};
  worker.postMessage(data);
}
byId('run').addEventListener('click',()=>submit('full'));
byId('observable').addEventListener('click',()=>submit('pauli'));
byId('contraction').addEventListener('click',()=>submit('amplitude'));
byId('cancel').addEventListener('click',cancelMain);
byId('source').addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();submit('full')}});
byId('export').addEventListener('click',()=>{
  if(!lastEvidence)return;
  const data=JSON.stringify(lastEvidence,null,2);const url=URL.createObjectURL(new Blob([data],{type:'application/json'}));const link=document.createElement('a');link.download=`DSIQ-experiment-${new Date().toISOString().replace(/[:.]/g,'-')}.json`;link.href=url;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),500);
});

const analyticCases=[
  {name:'Bell state amplitude and XX parity',source:cases.bell.source,bits:'11',pauli:'XX',expected:Math.SQRT1_2,observable:1},
  {name:'8-qubit GHZ correlation',source:ghz(8),bits:'ones',pauli:'X'.repeat(8),expected:Math.SQRT1_2,observable:1},
  {name:'100-qubit separable rotation amplitude',source:cases.product100.source,bits:'zeros',pauli:'',expected:Math.cos(Math.PI/6)**100,observable:null}
];
function diagnosticPayload(test){return {source:test.source,bits:test.bits,pauli:test.pauli,maxNodes:32768,shots:0,seed:42,maxReplayVisits:10000000,maxTensorBytes:67108864,maxSlices:256,precision:'fp64',method:'adaptive',ordering:'degree',observableOnly:false,contractionOnly:false}}
function runDiagnostic(test){return new Promise((resolve,reject)=>{
  const worker=new Worker(new URL('./worker.mjs',import.meta.url),{type:'module'});diagnosticWorker=worker;diagnosticReject=reject;
  worker.onmessage=({data})=>{if(data.error){worker.terminate();if(diagnosticWorker===worker){diagnosticWorker=null;diagnosticReject=null}reject(Error(data.error));return}if(data.result){worker.terminate();if(diagnosticWorker===worker){diagnosticWorker=null;diagnosticReject=null}resolve(data.result)}};
  worker.onerror=e=>{worker.terminate();if(diagnosticWorker===worker){diagnosticWorker=null;diagnosticReject=null}reject(Error(e.message||'Worker failed'))};
  worker.postMessage(diagnosticPayload(test));
})}
async function diagnostics(){
  if(diagnosticActive||pending)return;
  diagnosticActive=true;byId('diagnose').disabled=true;byId('diag-cancel').disabled=false;byId('diag-summary').textContent='Running analytical comparisons';byId('diag-log').textContent='';
  let pass=0,done=0;const rows=[...byId('diagnostic-list').querySelectorAll('li')];
  rows.forEach(row=>row.lastElementChild.textContent='PENDING');
  for(const [index,test] of analyticCases.entries()){
    if(!diagnosticActive)break;
    rows[index].lastElementChild.textContent='RUNNING';
    try{
      const r=await runDiagnostic(test);if(!diagnosticActive)break;
      const a=r.amplitude||{},obs=r.science?.pauliExpectation;
      const error=Math.hypot(Number(a.real||0)-test.expected,Number(a.imag||0));
      const obsError=test.observable===null?0:Math.abs(Number(obs)-test.observable);
      const ok=Number.isFinite(error)&&error<=1e-10&&Number.isFinite(obsError)&&obsError<=1e-10&&r.qubits===(index===0?2:index===1?8:100);
      done++;if(ok)pass++;
      rows[index].lastElementChild.textContent=ok?'PASS':'FAIL';
      byId('diag-log').textContent+=`${test.name}\n  amplitude error: ${scalar(error)}\n  Pauli error: ${test.observable===null?'n/a':scalar(obsError)}\n  execution: ${scalar(r.elapsedMs,7)} ms / ${r.mode}\n\n`;
    }catch(e){if(!diagnosticActive)break;done++;rows[index].lastElementChild.textContent='ERROR';byId('diag-log').textContent+=`${test.name}\n  ${String(e.message||e)}\n\n`}
    byId('diag-summary').textContent=`${pass}/${done} completed checks passed`;
  }
  if(diagnosticActive){byId('diag-summary').textContent=`${pass}/${analyticCases.length} analytical checks passed`;byId('diag-meta').textContent='Results are from this browser session. These three tests do not replace the Diamond-105 qualification.'}
  diagnosticActive=false;byId('diagnose').disabled=false;byId('diag-cancel').disabled=true;
}
byId('diagnose').addEventListener('click',diagnostics);
byId('diag-cancel').addEventListener('click',()=>{diagnosticActive=false;if(diagnosticWorker){diagnosticWorker.terminate();diagnosticWorker=null}if(diagnosticReject){const reject=diagnosticReject;diagnosticReject=null;reject(Error('Diagnostic run cancelled'))}byId('diagnose').disabled=false;byId('diag-cancel').disabled=true;byId('diag-summary').textContent='Diagnostic suite cancelled';byId('diag-meta').textContent='The partial diagnostic record is retained for inspection.'});
useTemplate();applyMethodConstraints();progress(0);
