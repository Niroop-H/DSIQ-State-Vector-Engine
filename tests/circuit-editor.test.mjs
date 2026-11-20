import assert from 'node:assert/strict';
import {newCircuit,addGate,toQasm,fromQasm,validateAngle,MAX_VISUAL_QUBITS,MAX_VISUAL_GATES,VISIBLE_GATE_COLUMNS,nextAppendScrollLeft} from '../apps/web/public/dsiq/circuit-editor.mjs';
// Auto-advance keeps the next gate insertion column visible without moving vertically.
assert.equal(nextAppendScrollLeft({scrollLeft:0,scrollWidth:1600,clientWidth:500,appendRight:370}),0);
assert.equal(nextAppendScrollLeft({scrollLeft:0,scrollWidth:1600,clientWidth:500,appendRight:600}),116);
assert.equal(nextAppendScrollLeft({scrollLeft:700,scrollWidth:1600,clientWidth:500,appendRight:590}),806);
assert.equal(nextAppendScrollLeft({scrollLeft:1050,scrollWidth:1600,clientWidth:500,appendRight:590}),1100);
assert.equal(nextAppendScrollLeft({scrollLeft:0,scrollWidth:320,clientWidth:500,appendRight:320}),0);
console.log('PASS automatic next-gate scroll geometry and boundary limits');

let s=addGate(addGate(newCircuit(2),'h',[0]),'cx',[0,1]);
assert.equal(toQasm(s),'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\ncx q[0],q[1];\n');
assert.deepEqual(fromQasm(toQasm(s)),s);
s=addGate(newCircuit(3),'ccx',[0,1,2]);assert.equal(fromQasm(toQasm(s)).steps[0].name,'ccx');
s=addGate(newCircuit(2),'swap',[1,0]);assert.deepEqual(fromQasm(toQasm(s)).steps[0].qubits,[1,0]);
s=addGate(newCircuit(1),'rx',[0],'pi/2');assert.equal(fromQasm(toQasm(s)).steps[0].theta,'pi/2');
for(const angle of ['pi','pi/2','-pi/4','1e-3','-.125','0.500'])assert.equal(validateAngle(angle),angle);
for(const angle of ['pi/0','7);x q[2]','foo','NaN','Infinity','10/2','pi/(2)'])assert.throws(()=>validateAngle(angle));
assert.throws(()=>addGate(newCircuit(2),'cx',[0,0]));assert.throws(()=>addGate(newCircuit(2),'cx',[0]));assert.throws(()=>addGate(newCircuit(2),'p',[1],'bogus'));assert.throws(()=>addGate(newCircuit(2),'h',[2]));
assert.throws(()=>newCircuit(MAX_VISUAL_QUBITS+1));assert.throws(()=>fromQasm('OPENQASM 2.0; qreg q[101]; h q[0];'));
assert.throws(()=>fromQasm('OPENQASM 2.0; qreg q[2]; measure q[0] -> c[0];'));

// 100-wire composer roundtrip with endpoints and page-bounded view contract.
assert.equal(MAX_VISUAL_QUBITS,100);assert.equal(VISIBLE_GATE_COLUMNS,12);assert.equal(MAX_VISUAL_GATES,2048);
let large=newCircuit(100);
large=addGate(large,'h',[0]);large=addGate(large,'cx',[0,99]);
large=addGate(large,'ccx',[0,50,99]);large=addGate(large,'rz',[99],'pi/4');
assert.deepEqual(fromQasm(toQasm(large)),large);
assert.match(toQasm(large),/cx q\[0\],q\[99\];/);
let ghz100=addGate(newCircuit(100),'h',[0]);
for(let i=0;i<99;i++)ghz100=addGate(ghz100,'cx',[i,i+1]);
assert.equal(ghz100.steps.length,100);assert.deepEqual(fromQasm(toQasm(ghz100)),ghz100);
let many=newCircuit(100);for(let i=0;i<MAX_VISUAL_GATES;i++)many=addGate(many,'z',[i%100]);
assert.equal(fromQasm(toQasm(many)).steps.length,MAX_VISUAL_GATES);
assert.throws(()=>addGate(many,'z',[0]),/limit/);
console.log('PASS 100-wire gates, 100Q GHZ, 2048 operation roundtrip');

let modes=[
 ['OPENQASM 2.0; qreg q[2]; h q[0]; cx q[0],q[1];','11','XX',Math.SQRT1_2,1],
 ['OPENQASM 2.0; qreg q[1]; h q[0]; rz(pi/2) q[0]; h q[0];','0','Z',Math.SQRT1_2,0],
 ['OPENQASM 2.0; qreg q[2]; x q[0]; swap q[0],q[1];','10','ZI',1,-1],
];
let msgs=[];globalThis.self={postMessage:m=>msgs.push(m)};
await import('../apps/web/public/dsiq/worker.mjs');
for(const [source,bits,pauli,real,observable] of modes){
  msgs=[];await globalThis.self.onmessage({data:{source,bits,pauli,shots:24,seed:42,maxNodes:32768,maxReplayVisits:10000000,maxTensorBytes:67108864,maxSlices:256,precision:'fp64',method:'adaptive',ordering:'degree'}});
  const out=msgs.at(-1);assert.ok(out.result,JSON.stringify(out));assert.ok(Math.abs(out.result.amplitude.real-real)<1e-10,JSON.stringify(out.result));assert.ok(Math.abs(out.result.science.pauliExpectation-observable)<1e-10,JSON.stringify(out.result));assert.equal(out.result.shotsCompleted,24);console.log('PASS worker numerical circuit',bits,source.slice(0,70));
}
const bigModes=[
  [toQasm(ghz100),'ones','X'.repeat(100),Math.SQRT1_2,1],
  [toQasm(addGate(addGate(newCircuit(100),'h',[0]),'cx',[0,99])),'1'+'0'.repeat(98)+'1','',Math.SQRT1_2,null],
  [toQasm(addGate(newCircuit(100),'x',[99])),'1'+'0'.repeat(99),'',1,null],
];
for(const [source,bits,pauli,real,observable] of bigModes){
  msgs=[];await globalThis.self.onmessage({data:{source,bits,pauli,shots:0,seed:42,maxNodes:32768,maxReplayVisits:10000000,maxTensorBytes:67108864,maxSlices:256,precision:'fp64',method:'adaptive',ordering:'degree'}});
  const out=msgs.at(-1);assert.ok(out.result,JSON.stringify(out));
  assert.equal(out.result.qubits,100);assert.ok(Math.abs(out.result.amplitude.real-real)<1e-10,JSON.stringify(out.result.amplitude));
  if(observable!==null)assert.ok(Math.abs(out.result.science.pauliExpectation-observable)<1e-10);
  console.log('PASS 100-qubit numerical result',out.result.mode,out.result.amplitude.real);
}
console.log('PASS circuit editor serialization, invalid inputs, import and worker numerical checks');
