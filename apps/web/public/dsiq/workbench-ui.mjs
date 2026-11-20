// DSIQ operator workbench. Every statistic is derived from the real parser or worker.
// The session record is volatile local memory, not a protected audit system.
const element=id=>document.getElementById(id);
let inspectWorker=null,sessionRecords=[],selection=-1;

function clearInspection(message='Source modified. Validate the current circuit.'){
  element('inspect-metrics').replaceChildren();
  element('inspect-inventory').replaceChildren();
  element('inspect-status').textContent='NOT VALIDATED';
  element('inspect-summary').textContent=message;
}
function inspectionMetrics(data){
  const definitions=[
    ['Qubits',data.qubits],['Expanded operations',data.expandedOperations],
    ['Dependency depth',data.structuralQubitDepth],
    ['Multi-qubit gates',data.multiQubitGateOperations],
    ['Active wires',data.activeQubits],['Measurement ops',data.measurements],
    ['Reset ops',data.resets],['Conditional ops',data.conditionalOperations]
  ];
  const host=element('inspect-metrics');host.replaceChildren();
  for(const [label,value] of definitions){
    const item=document.createElement('dl');item.className='inspect-metric';
    const title=document.createElement('dt');title.textContent=label;
    const number=document.createElement('dd');number.textContent=Number(value).toLocaleString();
    item.append(title,number);host.append(item);
  }
  const inventory=element('inspect-inventory');inventory.replaceChildren();
  for(const gate of data.gateInventory){
    const row=document.createElement('span');row.className='inventory-item';
    row.textContent=gate.name.toUpperCase()+' / '+Number(gate.count).toLocaleString();
    inventory.append(row);
  }
  element('inspect-status').textContent='VALID CIRCUIT';
  element('inspect-summary').textContent=data.kind+' · '+data.expandedOperations.toLocaleString()+' operations · depth '+data.structuralQubitDepth;
}
function validateCircuit(){
  if(element('run').disabled||inspectWorker)return;
  const source=element('source').value;
  if(!source.trim()){clearInspection('Enter a circuit first.');return;}
  const worker=new Worker(new URL('./worker.mjs',import.meta.url),{type:'module'});
  inspectWorker=worker;element('inspect').disabled=true;
  element('inspect-status').textContent='PARSING';
  element('inspect-summary').textContent='Checking gate signatures, operands and expanded circuit structure.';
  function finish(){worker.terminate();if(inspectWorker===worker)inspectWorker=null;element('inspect').disabled=element('run').disabled;}
  worker.onmessage=event=>{
    if(inspectWorker!==worker)return;
    const message=event.data;finish();
    if(source!==element('source').value){clearInspection();return;}
    if(message?.error){clearInspection(String(message.error));element('inspect-status').textContent='REJECTED';return;}
    if(message?.inspection){inspectionMetrics(message.inspection);return;}
    clearInspection('Unexpected parser response.');element('inspect-status').textContent='UNAVAILABLE';
  };
  worker.onerror=event=>{
    if(inspectWorker!==worker)return;
    finish();clearInspection(event.message||'Circuit inspection worker failed.');
    element('inspect-status').textContent='ERROR';
  };
  worker.postMessage({inspectOnly:true,source});
}
element('inspect').addEventListener('click',validateCircuit);
element('source').addEventListener('input',()=>{
  if(inspectWorker){inspectWorker.terminate();inspectWorker=null;element('inspect').disabled=element('run').disabled;}
  clearInspection();
});

function downloadJSON(name,value){
  const blob=new Blob([JSON.stringify(value,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');link.href=url;link.download=name;
  document.body.append(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),750);
}
function textCell(value,full){
  const cell=document.createElement('td');cell.textContent=String(value);
  if(full)cell.title=full;
  return cell;
}
function renderHistory(){
  const body=element('history-rows');body.replaceChildren();
  element('history-export').disabled=!sessionRecords.length;
  element('history-clear').disabled=!sessionRecords.length;
  element('history-repeat').disabled=selection<0||!sessionRecords[selection]||element('run').disabled;
  if(!sessionRecords.length){
    const row=document.createElement('tr'),cell=document.createElement('td');
    cell.colSpan=7;cell.className='history-empty';cell.textContent='No completed executions in this browser session.';
    row.append(cell);body.append(row);return;
  }
  for(let index=sessionRecords.length-1;index>=0;index--){
    const evidence=sessionRecords[index],out=evidence.result||{},params=evidence.parameters||{};
    const row=document.createElement('tr'),choice=document.createElement('td'),radio=document.createElement('input');
    radio.type='radio';radio.name='dsiq-history-choice';radio.checked=index===selection;
    radio.setAttribute('aria-label','Select execution '+(index+1));
    radio.addEventListener('change',()=>{selection=index;renderHistory()});
    choice.append(radio);row.append(choice);
    row.append(textCell(evidence.timestampUTC||'unknown'));
    const hash=evidence.sourceSHA256||'not available';
    row.append(textCell(hash.slice(0,16),hash));
    row.append(textCell(out.qubits??'n/a'));
    row.append(textCell(params.method??'n/a'));
    row.append(textCell(out.query??'n/a'));
    row.append(textCell(Number.isFinite(out.elapsedMs)?out.elapsedMs.toFixed(2)+' ms':'n/a'));
    body.append(row);
  }
}
window.addEventListener('dsiq:completed',event=>{
  const evidence=event.detail;
  if(!evidence?.result||!evidence?.parameters)return;
  sessionRecords.push(evidence);
  if(sessionRecords.length>12)sessionRecords.shift();
  selection=sessionRecords.length-1;renderHistory();
});
element('history-export').addEventListener('click',()=>{
  if(sessionRecords.length)downloadJSON('DSIQ-session-evidence.json',{
    schema:'DSIQ-local-session-v1',
    exportedUTC:new Date().toISOString(),
    recordCount:sessionRecords.length,
    records:sessionRecords
  });
});
element('history-clear').addEventListener('click',()=>{sessionRecords=[];selection=-1;renderHistory()});
element('history-repeat').addEventListener('click',()=>{
  if(element('run').disabled||selection<0||!sessionRecords[selection])return;
  const params=sessionRecords[selection].parameters;
  element('source').value=params.source;
  element('source').dispatchEvent(new Event('input',{bubbles:true}));
  element('query').value=params.bits;
  element('method').value=params.method;
  element('method').dispatchEvent(new Event('change',{bubbles:true}));
  element('precision').value=params.precision;
  element('shots').value=String(params.shots);
  element('seed').value=String(params.seed);
  element('pauli').value=params.pauli||'';
  element('budget').value=String(params.maxNodes);
  element('visits').value=String(params.maxReplayVisits);
  element('tensorbytes').value=String(params.maxTensorBytes);
  element('slices').value=String(params.maxSlices);
  element('ordering').value=params.ordering;
  element(params.observableOnly?'observable':params.contractionOnly?'contraction':'run').click();
});
const upload=element('qasm-file');
if(upload)upload.addEventListener('change',async ()=>{
  const file=upload.files?.[0];if(!file)return;
  try{
    if(file.size>750000)throw Error('OpenQASM file exceeds the 750 KB parser limit.');
    const data=await file.text();
    if(!/^\s*OPENQASM\s+(?:2\.0|3(?:\.0)?)\s*;/.test(data))throw Error('File must begin with OPENQASM 2.0 or 3.0.');
    if(element('run').disabled)throw Error('Finish the current execution before loading a file.');
    element('source').value=data;
    element('source').dispatchEvent(new Event('input',{bubbles:true}));
    element('source-pane').open=true;
    element('inspect-status').textContent='FILE LOADED';
    element('inspect-summary').textContent=file.name+' is ready for source inspection and execution.';
  }catch(error){
    clearInspection(String(error.message||error));
    element('inspect-status').textContent='IMPORT ERROR';
  }finally{upload.value='';}
});
// Expand circuit authoring for long 100-qubit sequences.
const expand=element('qc-expand');
if(expand){
  function setExpanded(on){
    element('qc-editor').classList.toggle('qc-maximized',on);
    expand.textContent=on?'Exit expanded view':'Expand workspace';
    expand.setAttribute('aria-pressed',String(on));
  }
  expand.addEventListener('click',()=>setExpanded(!element('qc-editor').classList.contains('qc-maximized')));
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&element('qc-editor').classList.contains('qc-maximized'))setExpanded(false);
  });
}
element('load-template').addEventListener('click',()=>queueMicrotask(()=>clearInspection('Reference experiment loaded. Run validation for the new circuit.')));
renderHistory();
