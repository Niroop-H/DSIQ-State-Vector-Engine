/**
 * DSIQ circuit composer. Pure state/QASM functions are exported for independent tests.
 * The browser UI serializes operations into OpenQASM consumed by the existing worker.
 * No synthetic computation or fabricated measurement data is produced here.
 */
export const MAX_VISUAL_QUBITS = 100;
export const VISIBLE_GATE_COLUMNS = 12;

// Horizontal position needed to keep the next ADD column fully in view.
// Inputs are measured relative to the current scroll viewport, not the page.
export function nextAppendScrollLeft({scrollLeft,scrollWidth,clientWidth,appendRight,padding=16}){
  const values=[scrollLeft,scrollWidth,clientWidth,appendRight,padding];
  if(!values.every(Number.isFinite)||clientWidth<=0)return scrollLeft;
  const maximum=Math.max(0,scrollWidth-clientWidth);
  const desired=scrollLeft+appendRight-clientWidth+padding;
  return Math.min(maximum,Math.max(0,scrollLeft,desired));
}

export const MAX_VISUAL_GATES = 2048;
export const GATE_SPEC = Object.freeze({
  h:{arity:1},x:{arity:1},y:{arity:1},z:{arity:1},s:{arity:1},sdg:{arity:1},t:{arity:1},tdg:{arity:1},sx:{arity:1},
  rx:{arity:1,angle:true},ry:{arity:1,angle:true},rz:{arity:1,angle:true},p:{arity:1,angle:true},
  cx:{arity:2},cy:{arity:2},cz:{arity:2},swap:{arity:2},cp:{arity:2,angle:true},ccx:{arity:3}
});
const angleValue = /^(?:-?pi(?:\/[1-9]\d*)?|-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)$/;
export function validateAngle(input){
  const value=String(input??'').trim();
  if(!angleValue.test(value))throw Error('Angle must be a decimal, pi, pi/2, -pi/4, or another pi divided by a positive integer.');
  const number=value.includes('pi')?(value.startsWith('-')?-1:1)*Math.PI/(Number(value.split('/')[1])||1):Number(value);
  if(!Number.isFinite(number))throw Error('Angle must be finite.');
  return value;
}
export function normalizeQubits(n){
  if(!Number.isInteger(Number(n))||Number(n)<1||Number(n)>MAX_VISUAL_QUBITS)throw Error(`Visual composer supports 1 to ${MAX_VISUAL_QUBITS} qubits. Larger experiments remain supported in OpenQASM.`);
  return Number(n);
}
export function newCircuit(n=2){return {n:normalizeQubits(n),steps:[]};}
export function addGate(state,name,qubits,theta){
  const spec=GATE_SPEC[name];if(!spec)throw Error('Unsupported gate: '+name);
  const n=normalizeQubits(state.n);
  if(!Array.isArray(qubits)||qubits.length!==spec.arity||qubits.some(q=>!Number.isInteger(q)||q<0||q>=n)||new Set(qubits).size!==qubits.length)throw Error('Gate requires '+spec.arity+' distinct qubit'+(spec.arity===1?'':'s')+' in range.');
  if(state.steps.length>=MAX_VISUAL_GATES)throw Error(`Visual editor limit is ${MAX_VISUAL_GATES} gates. OpenQASM remains available for longer circuits.`);
  const step={name,qubits:[...qubits]};if(spec.angle)step.theta=validateAngle(theta);
  return {n,steps:[...state.steps,step]};
}
export function toQasm(state){
  const n=normalizeQubits(state.n);
  const rows=['OPENQASM 2.0;','include "qelib1.inc";',`qreg q[${n}];`];
  for(const op of state.steps){const spec=GATE_SPEC[op.name];if(!spec)throw Error('Unsupported gate');if(op.qubits.length!==spec.arity||op.qubits.some(q=>!Number.isInteger(q)||q<0||q>=n)||new Set(op.qubits).size!==op.qubits.length)throw Error('Invalid qubit operands');rows.push(`${op.name}${spec.angle?'('+validateAngle(op.theta)+')':''} ${op.qubits.map(q=>`q[${q}]`).join(',')};`)}
  return rows.join('\n')+'\n';
}
export function fromQasm(source){
  if(typeof source!=='string'||source.length>750000)throw Error('Invalid circuit source.');
  const clean=source.replace(/\/\*[\s\S]*?\*\//g,' ').replace(/\/\/[^\n]*/g,'').trim();
  if(!clean.endsWith(';'))throw Error('OpenQASM source must end with a semicolon.');
  const lines=clean.split(';').map(s=>s.trim()).filter(Boolean);
  if(!/^OPENQASM 2\.0$/.test(lines.shift()||''))throw Error('Visual import currently accepts OpenQASM 2.0. OpenQASM 3 remains executable in source mode.');
  let n=null,state=null;
  for(const row of lines){
    if(/^include "qelib1\.inc"$/.test(row))continue;
    const reg=/^qreg\s+q\[(\d+)\]$/.exec(row);
    if(reg){if(n!==null)throw Error('Only one q register can be imported.');n=normalizeQubits(Number(reg[1]));state=newCircuit(n);continue;}
    if(n===null)throw Error('Circuit must declare qreg q[n].');
    const match=/^([a-z][a-z0-9]*)(?:\(([^()]*)\))?\s+(.+)$/.exec(row);
    if(!match||!GATE_SPEC[match[1]])throw Error('This circuit includes instructions outside the visual palette. It is preserved and remains executable in source mode.');
    const name=match[1],spec=GATE_SPEC[name],qubits=match[3].split(',').map(v=>{const m=/^q\[(\d+)\]$/.exec(v.trim());if(!m)throw Error('Visual import requires individually indexed q wires.');return Number(m[1]);});
    if((!!match[2])!==!!spec.angle)throw Error('Gate angle specification is invalid.');
    state=addGate(state,name,qubits,match[2]);
  }
  if(state===null)throw Error('Missing qreg statement.');
  return state;
}

function setupComposer(){
  const byId=id=>document.getElementById(id);
  const host=byId('qc-editor');if(!host)return;
  const source=byId('source');
  let state=newCircuit(2),picked='h',waiting=[],selected=-1,undoStack=[],redoStack=[],lastWritten='',synced=false,page=0;
  const clone=s=>({n:s.n,steps:s.steps.map(x=>({...x,qubits:[...x.qubits]}))});
  const info=(message,isError=false)=>{const el=byId('qc-message');el.textContent=message;el.classList.toggle('qc-error',isError);};
  const make=(tag,cls,text)=>{const element=document.createElement(tag);if(cls)element.className=cls;if(text!==undefined)element.textContent=text;return element;};
  const selectable=()=>!byId('run').disabled;
  function save(){undoStack.push(clone(state));if(undoStack.length>100)undoStack.shift();redoStack=[];}
  function sync(){
    lastWritten=toQasm(state);source.value=lastWritten;source.dispatchEvent(new Event('input',{bubbles:true}));synced=true;
    byId('qc-code-state').textContent='OPENQASM SYNCHRONIZED';
    byId('qc-wire-count').value=String(state.n);
    const pauli=byId('pauli');if(pauli.value.trim().length!==state.n)pauli.value='';
    const query=byId('query');if(!['zeros','ones'].includes(query.value)&&query.value.length!==state.n)query.value='zeros';
  }
  function commit(next,message,followAppend=false){save();state=next;selected=-1;waiting=[];page=Math.floor(Math.max(0,state.steps.length-1)/VISIBLE_GATE_COLUMNS);sync();render(followAppend);info(message||'Circuit compiled into OpenQASM. Execute to calculate numerical results.');}
  function apply(newState){state=newState;selected=-1;waiting=[];page=Math.floor(Math.max(0,state.steps.length-1)/VISIBLE_GATE_COLUMNS);render();}
  function importSource(silent=false){try{const imported=fromQasm(source.value);state=imported;selected=-1;waiting=[];page=0;undoStack=[];redoStack=[];synced=true;lastWritten=source.value;render();byId('qc-code-state').textContent='VISUAL MODEL MATCHES SOURCE';if(!silent)info(`Imported ${state.steps.length} gates on ${state.n} qubits. The executable source has not been changed.`);return true;}catch(e){synced=false;render();byId('qc-code-state').textContent='SOURCE-ONLY MODE';info(`Visual import: ${e.message} The source editor and execution remain available.`,!silent);return false;}}
  function selectGate(name){if(!GATE_SPEC[name])return;picked=name;waiting=[];render();info(`Selected ${name.toUpperCase()}. ${GATE_SPEC[name].arity===1?'Click a wire in the + column.':`Click ${GATE_SPEC[name].arity} distinct wires in order: ${name==='ccx'?'control 1, control 2, target':name==='swap'?'first and second wire':'control, then target'}.`}`);}
  function place(wire){if(!synced){info('Source has unsynchronized edits. Select “Import QASM” or “New circuit” before editing the diagram.',true);return;}if(!selectable()){info('Finish or cancel the current computation before modifying the circuit.',true);return;}
    if(waiting.includes(wire)){waiting=[];render();info('Selection cleared. Choose distinct wires.');return;}
    const next=[...waiting,wire],spec=GATE_SPEC[picked];if(next.length<spec.arity){waiting=next;render();info(`Selected q[${wire}]. Choose ${spec.arity-next.length} more wire(s) to place ${picked.toUpperCase()}.`);return;}
    try{const nextState=addGate(state,picked,next,byId('qc-angle').value);commit(nextState,`Placed ${picked.toUpperCase()} at step ${nextState.steps.length}. Ready for numerical execution.`,true);}catch(e){waiting=[];render();info(e.message,true)}
  }
  function render(followAppend=false){
    const pages=Math.max(1,Math.ceil(state.steps.length/VISIBLE_GATE_COLUMNS));page=Math.max(0,Math.min(page,pages-1));
    byId('qc-page-info').textContent=`${page+1} / ${pages} · steps ${state.steps.length?String(page*VISIBLE_GATE_COLUMNS+1)+'–'+String(Math.min((page+1)*VISIBLE_GATE_COLUMNS,state.steps.length)):'0'}`;
    byId('qc-page-prev').disabled=page===0;byId('qc-page-next').disabled=page>=pages-1;
    byId('qc-page-index').max=String(pages);byId('qc-page-index').value=String(page+1);
    byId('qc-wire-jump').max=String(state.n-1);
    byId('qc-gates').textContent=String(state.steps.length);byId('qc-qubits').textContent=String(state.n);
    byId('qc-wire-count').value=String(state.n);
    byId('qc-undo').disabled=!undoStack.length;byId('qc-redo').disabled=!redoStack.length;
    byId('qc-remove').disabled=selected<0;byId('qc-left').disabled=selected<=0;byId('qc-right').disabled=selected<0||selected>=state.steps.length-1;
    for(const b of host.querySelectorAll('[data-qc-gate]'))b.classList.toggle('active',b.dataset.qcGate===picked);
    byId('qc-angle-wrap').classList.toggle('hidden',!GATE_SPEC[picked].angle);
    const board=byId('qc-board'),scroller=byId('qc-scroll'),scrollY=scroller.scrollTop,scrollX=scroller.scrollLeft;board.replaceChildren();
    const labels=make('div','qc-labels');labels.append(make('div','qc-step-cap','QUBIT'));
    for(let q=0;q<state.n;q++){const b=make('button','qc-wire-label',`q[${q}]  |0⟩`);b.type='button';b.title=`Append ${picked.toUpperCase()} to q[${q}]`;b.addEventListener('click',()=>place(q));labels.append(b)}board.append(labels);
    const timeline=make('div','qc-timeline');
    for(let index=page*VISIBLE_GATE_COLUMNS;index<Math.min(state.steps.length,(page+1)*VISIBLE_GATE_COLUMNS);index++){
      const op=state.steps[index];
      const column=make('div','qc-step'+(index===selected?' selected':'') );
      const cap=make('button','qc-step-cap',String(index+1).padStart(2,'0'));cap.type='button';cap.title=`Select operation ${index+1} for reordering or removal`;cap.addEventListener('click',()=>{selected=index;render();info(`Selected step ${index+1}: ${op.name.toUpperCase()} ${op.qubits.map(q=>'q['+q+']').join(', ')}.`)});column.append(cap);
      const min=Math.min(...op.qubits),max=Math.max(...op.qubits);
      for(let q=0;q<state.n;q++){
        const cell=make('div','qc-cell');const wire=make('span','qc-wire-line');cell.append(wire);
        if(op.qubits.length>1&&q>=min&&q<=max){const v=make('span','qc-vertical');if(q===min)v.classList.add('qc-stem-start');if(q===max)v.classList.add('qc-stem-end');cell.append(v)}
        if(op.qubits.includes(q)){
          let label=op.name.toUpperCase();
          if(op.name==='cx'||op.name==='cy'||op.name==='cz'||op.name==='cp'||op.name==='ccx')label=q===op.qubits.at(-1)?({cx:'⊕',ccx:'⊕',cy:'Y',cz:'Z',cp:'P'}[op.name]):'●';
          if(op.name==='swap')label='×';
          const gate=make('button','qc-gate',label);gate.type='button';gate.title=`${op.name.toUpperCase()} ${op.qubits.map(q=>'q['+q+']').join(', ')}${op.theta?' ('+op.theta+')':''}`;gate.addEventListener('click',()=>{selected=index;render();info('Selected gate at step '+(index+1)+'. Move, remove, or modify the circuit.')});cell.append(gate);
        }
        column.append(cell);
      }
      timeline.append(column);
    }
    const extra=make('div','qc-step qc-new-step');extra.append(make('div','qc-step-cap','ADD'));
    for(let q=0;q<state.n;q++){
      const cell=make('button','qc-cell qc-add'+(waiting.includes(q)?' pending':''),'');cell.type='button';cell.dataset.wire=String(q);cell.title=`Add ${picked.toUpperCase()} on q[${q}]`;
      const line=make('span','qc-wire-line');const plus=make('span','qc-plus',waiting.includes(q)?'●':'+');cell.append(line,plus);
      cell.addEventListener('click',()=>place(q));cell.addEventListener('dragover',e=>{if(e.dataTransfer?.types?.includes('text/plain'))e.preventDefault()});cell.addEventListener('drop',e=>{e.preventDefault();const name=e.dataTransfer?.getData('text/plain');if(GATE_SPEC[name])selectGate(name);place(q)});
      extra.append(cell);
    }
    timeline.append(extra);board.append(timeline);
    // Rebuilding the diagram must never reset the operator's qubit position.
    scroller.scrollTop=scrollY;scroller.scrollLeft=scrollX;
    if(followAppend){
      const viewport=scroller.getBoundingClientRect();
      const right=extra.getBoundingClientRect().right-viewport.left;
      const target=nextAppendScrollLeft({scrollLeft:scroller.scrollLeft,scrollWidth:scroller.scrollWidth,clientWidth:scroller.clientWidth,appendRight:right});
      if(target>scroller.scrollLeft+1){
        const reducedMotion=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches===true;
        scroller.scrollTo({left:target,top:scrollY,behavior:reducedMotion?'auto':'smooth'});
      }
    }
    byId('qc-board-caption').textContent=`${state.n} wires · ${state.steps.length} ordered operations · page ${page+1}/${pages} · 100-qubit circuit authoring`; 
  }
  function applyHistory(stack,opposite,message){if(!stack.length)return;if(!synced){info('Import or reset manually edited source first.',true);return;}opposite.push(clone(state));apply(stack.pop());sync();render();info(message);}
  host.querySelectorAll('[data-qc-gate]').forEach(b=>{b.type='button';b.draggable=true;b.addEventListener('click',()=>selectGate(b.dataset.qcGate));b.addEventListener('dragstart',e=>{e.dataTransfer?.setData('text/plain',b.dataset.qcGate);selectGate(b.dataset.qcGate)})});
  byId('qc-new').addEventListener('click',()=>{if(!selectable())return;const n=Number(byId('qc-wire-count').value);try{const s=newCircuit(n);save();state=s;selected=-1;waiting=[];page=0;sync();render();info('Created an empty '+n+'-qubit circuit. Select a gate and click a wire in the ADD column.');}catch(e){info(e.message,true)}});
  byId('qc-example-bell').addEventListener('click',()=>{if(!selectable())return;commit(addGate(addGate(newCircuit(2),'h',[0]),'cx',[0,1]),'Loaded a Bell-state circuit. Run to obtain actual amplitudes and samples.');byId('query').value='00';byId('pauli').value='XX';byId('shots').value='128';byId('method').value='adaptive';byId('method').dispatchEvent(new Event('change'));});
  byId('qc-example-ghz').addEventListener('click',()=>{if(!selectable())return;let s=addGate(newCircuit(4),'h',[0]);for(let i=0;i<3;i++)s=addGate(s,'cx',[i,i+1]);commit(s,'Loaded a four-qubit GHZ circuit.');byId('query').value='ones';byId('pauli').value='XXXX';byId('shots').value='128';byId('method').value='adaptive';byId('method').dispatchEvent(new Event('change'));});
  byId('qc-example-ghz100').addEventListener('click',()=>{if(!selectable())return;let s=addGate(newCircuit(100),'h',[0]);for(let i=0;i<99;i++)s=addGate(s,'cx',[i,i+1]);commit(s,'Loaded 100-qubit GHZ circuit with 100 real gate operations. Run to evaluate a basis amplitude and global correlation.');page=0;render();byId('query').value='ones';byId('pauli').value='X'.repeat(100);byId('shots').value='0';byId('method').value='adaptive';byId('method').dispatchEvent(new Event('change'));});
  byId('qc-example-phase').addEventListener('click',()=>{if(!selectable())return;let s=addGate(newCircuit(1),'h',[0]);s=addGate(s,'rz',[0],'pi/2');s=addGate(s,'h',[0]);commit(s,'Loaded a phase-interference circuit.');byId('query').value='0';byId('pauli').value='Z';byId('shots').value='128';byId('method').value='adaptive';byId('method').dispatchEvent(new Event('change'));});
  byId('qc-import').addEventListener('click',()=>{if(!selectable())return;importSource()});
  byId('qc-resize').addEventListener('click',()=>{if(!synced){info('Import or reset the source before changing qubits.',true);return;}if(!selectable())return;try{const n=normalizeQubits(byId('qc-wire-count').value);if(state.steps.some(op=>op.qubits.some(q=>q>=n)))throw Error('Remove gates using higher-numbered wires before reducing qubit count, or select New circuit.');if(n!==state.n){commit({n,steps:state.steps},`Resized quantum register to ${n} qubits.`);}else render();}catch(e){info(e.message,true)}});
  byId('qc-page-prev').addEventListener('click',()=>{if(page>0){page--;render()}});
  byId('qc-page-next').addEventListener('click',()=>{if((page+1)*VISIBLE_GATE_COLUMNS<state.steps.length){page++;render()}});
  byId('qc-page-go').addEventListener('click',()=>{const desired=Number(byId('qc-page-index').value)-1;if(!Number.isInteger(desired)||desired<0||desired>=Math.max(1,Math.ceil(state.steps.length/VISIBLE_GATE_COLUMNS))){info('Page number is outside the circuit operation range.',true);return}page=desired;render()});
  byId('qc-wire-go').addEventListener('click',()=>{const q=Number(byId('qc-wire-jump').value);if(!Number.isInteger(q)||q<0||q>=state.n){info('Select a valid qubit from 0 through '+(state.n-1)+'.',true);return}const scroller=byId('qc-scroll');scroller.scrollTop=Math.max(0,q*52-52);info(`Showing q[${q}]. Select a gate, then click the ADD cell on this wire to append an operation.`)});
  byId('qc-undo').addEventListener('click',()=>applyHistory(undoStack,redoStack,'Undo applied. OpenQASM regenerated.'));
  byId('qc-redo').addEventListener('click',()=>applyHistory(redoStack,undoStack,'Redo applied. OpenQASM regenerated.'));
  byId('qc-remove').addEventListener('click',()=>{if(selected<0||!selectable())return;const steps=state.steps.filter((_,i)=>i!==selected);commit({n:state.n,steps},'Removed selected operation.');});
  function move(delta){if(selected<0||!selectable())return;const j=selected+delta;if(j<0||j>=state.steps.length)return;save();const steps=[...state.steps];[steps[selected],steps[j]]=[steps[j],steps[selected]];state={n:state.n,steps};selected=j;waiting=[];page=Math.floor(j/VISIBLE_GATE_COLUMNS);sync();render();info('Gate order updated. The exact execution sequence is reflected in OpenQASM.');}
  byId('qc-left').addEventListener('click',()=>move(-1));byId('qc-right').addEventListener('click',()=>move(1));
  byId('qc-run').addEventListener('click',()=>{if(!synced){info('Diagram and QASM differ. Import the current QASM or create a new circuit first.',true);return;}byId('run').click();});
  byId('qc-download').addEventListener('click',()=>{const s=source.value;if(!s.trim())return;const link=document.createElement('a'),url=URL.createObjectURL(new Blob([s],{type:'text/plain;charset=utf-8'}));link.href=url;link.download='DSIQ-circuit.qasm';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)});
  source.addEventListener('input',()=>{if(source.value!==lastWritten){synced=false;byId('qc-code-state').textContent='SOURCE CHANGED';info('The QASM source was edited. The diagram is not automatically overwritten. Select Import QASM to synchronize.',false)}});
  byId('load-template').addEventListener('click',()=>queueMicrotask(()=>importSource(true)));
  if(!importSource(true)){info('Visual mode is available for new circuits. The loaded QASM remains executable; use New circuit to start a visual experiment.');}
  render();
}
if(typeof document!=='undefined')setupComposer();
