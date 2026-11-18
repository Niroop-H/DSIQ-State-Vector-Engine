import assert from 'node:assert/strict';
let messages=[];globalThis.self={postMessage:m=>messages.push(m)};await import('../apps/web/public/dsiq/worker.mjs');
async function run(source,overrides={}){messages=[];await self.onmessage({data:{source,bits:'zeros',maxNodes:32768,shots:16,seed:42,pauli:'',maxReplayVisits:100000,...overrides}});const m=messages.at(-1);assert.ok(m.result,JSON.stringify(m));return m.result}
let r=await run('OPENQASM 2.0; qreg q[2]; h q[0]; p(pi/3) q[0];',{pauli:'IX'});assert.equal(r.mode,'phase-product');assert.ok(Math.abs(r.science.pauliExpectation-.5)<1e-13);
r=await run('OPENQASM 2.0; qreg q[2]; h q[0]; cx q[0],q[1];',{pauli:'XX'});assert.equal(r.mode,'dag');assert.ok(Math.abs(r.science.pauliExpectation-1)<1e-13);assert.ok(Object.keys(r.counts).every(k=>k==='00'||k==='11'));
r=await run('OPENQASM 2.0; qreg q[2]; creg c[1]; h q[0]; cx q[0],q[1]; measure q[0] -> c[0]; if(c==1) x q[1]; reset q[0];');assert.equal(r.mode,'trajectory-dag');assert.deepEqual(r.counts,{'00':16});assert.equal(r.shotsCompleted,16);assert.equal(r.measurementEvents.length,2);
r=await run('OPENQASM 2.0; qreg q[2]; h q[0]; cx q[0],q[1];',{pauli:'XX',observableOnly:true});assert.equal(r.mode,'adjoint-pauli');assert.equal(r.amplitude,null);assert.equal(r.shotsCompleted,0);assert.ok(Math.abs(r.science.pauliExpectation-1)<1e-13);
r=await run('OPENQASM 2.0; qreg q[5]; h q[0]; cx q[0],q[1];',{maxNodes:6,bits:'00011'});assert.equal(r.mode,'replay');assert.ok(Math.abs(r.amplitude.real-Math.SQRT1_2)<1e-13);assert.equal(r.shotsCompleted,0);console.log('worker: phase, DAG, trajectory, observable-only, forced replay passed');

r=await run('OPENQASM 2.0; qreg q[100]; h q; cx q[0],q[99];',{pauli:'X'.repeat(100)});assert.equal(r.mode,'affine-clifford');assert.equal(r.science.pauliExpectation,1);
r=await run('OPENQASM 2.0; qreg q[100]; h q; t q[99];',{pauli:'X'.repeat(100)});assert.equal(r.mode,'affine-phase');assert.ok(Math.abs(r.science.pauliExpectation-Math.SQRT1_2)<1e-13);
r=await run('OPENQASM 2.0; qreg q[100]; ry(.3) q; cx q[0],q[1];',{precision:'fp32'});assert.equal(r.mode,'factor-statevector');assert.match(r.precision,/Float32/);assert.ok(Math.abs(r.science.norm-1)<1e-5);console.log('worker: additional affine, affine-phase and FP32 paths passed');
