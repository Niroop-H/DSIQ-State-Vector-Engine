import assert from 'node:assert/strict';
import {newCircuit,addGate,toQasm,fromQasm,validateAngle,MAX_VISUAL_QUBITS} from '../apps/web/public/dsiq/circuit-editor.mjs';
let s=addGate(addGate(newCircuit(2),'h',[0]),'cx',[0,1]);
assert.equal(toQasm(s),'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\ncx q[0],q[1];\n');
assert.deepEqual(fromQasm(toQasm(s)),s);
s=addGate(newCircuit(3),'ccx',[0,1,2]);assert.equal(fromQasm(toQasm(s)).steps[0].name,'ccx');
s=addGate(newCircuit(2),'swap',[1,0]);assert.deepEqual(fromQasm(toQasm(s)).steps[0].qubits,[1,0]);
s=addGate(newCircuit(1),'rx',[0],'pi/2');assert.equal(fromQasm(toQasm(s)).steps[0].theta,'pi/2');
for(const angle of ['pi','pi/2','-pi/4','1e-3','-.125','0.500'])assert.equal(validateAngle(angle),angle);
for(const angle of ['pi/0','7);x q[2]','foo','NaN','Infinity','10/2','pi/(2)'])assert.throws(()=>validateAngle(angle));
assert.throws(()=>addGate(newCircuit(2),'cx',[0,0]));assert.throws(()=>addGate(newCircuit(2),'cx',[0]));assert.throws(()=>addGate(newCircuit(2),'p',[1],'bogus'));assert.throws(()=>addGate(newCircuit(2),'h',[2]));
assert.throws(()=>newCircuit(MAX_VISUAL_QUBITS+1));assert.throws(()=>fromQasm('OPENQASM 2.0; qreg q[17]; h q[0];'));
assert.throws(()=>fromQasm('OPENQASM 2.0; qreg q[2]; measure q[0] -> c[0];'));
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
console.log('PASS circuit editor serialization, invalid inputs, import and worker numerical checks');
