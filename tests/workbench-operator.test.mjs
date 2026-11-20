import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {inspectCircuit} from '../apps/web/public/dsiq/worker.mjs';

const root=new URL('../apps/web/public/dsiq/',import.meta.url);
const read=path=>readFileSync(new URL(path,root),'utf8');
const html=read('index.html'),css=read('workbench.css'),ops=read('workbench-ui.mjs'),ui=read('ui.mjs');
const vercel=JSON.parse(read('vercel.json'));
for(const id of ['qc-editor','qc-expand','source','qasm-file','inspect','inspect-metrics','inspect-status','execution-results','amp-prob','history-rows','history-export','history-clear','history-repeat']){
  assert.ok(html.includes('id="'+id+'"'),'missing '+id);
}
assert.ok(html.includes('./workbench.css')&&html.includes('./workbench-ui.mjs'));
assert.ok(html.indexOf('id="qc-editor"')<html.indexOf('id="execution-results"'));
assert.ok(html.indexOf('id="execution-results"')<html.indexOf('id="history-rows"'));
assert.match(css,/\.workspace-grid\{display:flex;flex-direction:column/);
assert.match(css,/background:#000/);
assert.match(ops,/new Worker\(new URL\('\.\/worker\.mjs',import\.meta\.url\)/);
assert.match(ops,/inspectOnly:true/);
assert.match(ops,/dsiq:completed/);
assert.match(ui,/dispatchEvent\(new CustomEvent\('dsiq:completed'/);
assert.match(ui,/sourceHash\(data.source\)/);
const policy=vercel.headers.flatMap(e=>e.headers).find(h=>h.key==='Content-Security-Policy');
assert.ok(policy?.value.includes("worker-src 'self'"));
assert.ok(policy?.value.includes("frame-ancestors 'none'"));

const bell=inspectCircuit('OPENQASM 2.0;qreg q[2];h q[0];cx q[0],q[1];');
assert.equal(bell.qubits,2);assert.equal(bell.expandedOperations,2);
assert.equal(bell.structuralQubitDepth,2);assert.equal(bell.multiQubitGateOperations,1);
const large='OPENQASM 2.0;qreg q[100];h q[0];'+Array.from({length:99},(_,i)=>'cx q['+i+'],q['+(i+1)+'];').join('');
const ghz=inspectCircuit(large);
assert.equal(ghz.qubits,100);assert.equal(ghz.expandedOperations,100);
assert.equal(ghz.structuralQubitDepth,100);assert.equal(ghz.multiQubitGateOperations,99);
const last=inspectCircuit('OPENQASM 2.0;qreg q[100];x q[99];');
assert.equal(last.activeQubits,1);assert.equal(last.structuralQubitDepth,1);
const parallel=inspectCircuit('OPENQASM 2.0;qreg q[10];h q;z q;');
assert.equal(parallel.expandedOperations,20);assert.equal(parallel.structuralQubitDepth,2);
assert.throws(()=>inspectCircuit('OPENQASM 2.0;qreg q[2];cx q[0],q[3];'),/out of range/);
console.log('PASS full width workbench, parser-backed preflight, 100Q inspection, session evidence hooks, CSP');
