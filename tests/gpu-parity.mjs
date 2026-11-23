import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {matrix} from '../apps/web/public/dsiq/engine.mjs';
import {FactorDSIQ} from '../apps/web/public/dsiq/factor.mjs';
import {randomBlocks} from './factor.test.mjs';

export function gpuParity() {
  const {n, gates, refs} = randomBlocks(50, 10, 24, 792317);
  const cpu = new FactorDSIQ(n, gates);
  const input = [cpu.groups.length+' '+gates.length, cpu.groups.map(g=>g.qs.length).join(' ')];
  for (const g of gates) {
    cpu.apply(g);
    const [group,target] = cpu.mapped[g.q];
    let mask = 0;
    for (const q of g.controls) {
      assert.equal(cpu.mapped[q][0], group);
      mask |= 1 << cpu.mapped[q][1];
    }
    input.push([group,target,mask,...matrix(g).flat()].join(' '));
  }
  const payload = input.join('\n')+'\n';
  const output = execFileSync(process.env.DSIQ_D3D11_FACTOR, [], {
    input:payload, encoding:'utf8', timeout:180000, maxBuffer:32*1024*1024
  }).trim().split(/\r?\n/);
  const [vendorId,deviceId,dispatched,reportedCount] = output.shift().split(' ').map(Number);
  const count = cpu.groups.reduce((sum,g)=>sum+g.a.length/2,0);
  assert.equal(dispatched,gates.length);
  assert.equal(reportedCount,count);
  assert.equal(output.length,count);
  let index=0, maxError=0, maxOracleError=0, fullBasisBound=0, cpuMagnitude=1;
  for (const [group,{a}] of cpu.groups.entries()) {
    let delta=0, cpuMax=0, gpuMax=0;
    for (let j=0;j<a.length/2;j++) {
      const parts=output[index++].split(' ').map(Number);
      assert.equal(parts.length,2);
      const [re,im]=parts;
      const error=Math.hypot(re-a[2*j],im-a[2*j+1]);
      delta=Math.max(delta,error);
      maxOracleError=Math.max(maxOracleError,Math.hypot(re-refs[group][j][0],im-refs[group][j][1]));
      cpuMax=Math.max(cpuMax,Math.hypot(a[2*j],a[2*j+1]));
      gpuMax=Math.max(gpuMax,Math.hypot(re,im));
    }
    // Tensor-product difference identity: append one factor without enumerating its cross product.
    fullBasisBound=fullBasisBound*gpuMax+cpuMagnitude*delta;
    cpuMagnitude*=cpuMax;
    maxError=Math.max(maxError,delta);
  }
  assert.ok(maxError<=1e-13 && fullBasisBound<=1e-13 && maxOracleError<=1e-13);
  return {qubits:n,gates:dispatched,groups:cpu.groups.length,complexCoefficients:count,
    vendorId,deviceId,maxError,maxOracleError,fullBasisBound,
    inputSHA256:createHash('sha256').update(payload).digest('hex'),
    scope:'Hardware D3D11 FP64 factor state, five interacting ten-wire blocks'};
}
if (process.argv[1]===fileURLToPath(import.meta.url)) console.log(JSON.stringify(gpuParity()));
