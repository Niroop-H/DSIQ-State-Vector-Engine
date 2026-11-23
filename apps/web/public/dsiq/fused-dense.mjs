// FP64 connected dense state, |0...0> input. The factor planner validates
// gate signatures, wire mapping and allocation before this executor runs.
import {matrix} from './engine.mjs';

const hadamard = matrix({name:'h'}).flat();
function localMatrix(gate) {
  if (gate.name==='h') return hadamard;
  if (gate.name==='rz') {
    const c=Math.cos(gate.theta/2), s=Math.sin(gate.theta/2);
    return [c,-s,0,0,0,0,c,s];
  }
  if (gate.name==='p') return [1,0,0,0,0,0,Math.cos(gate.theta),Math.sin(gate.theta)];
  return matrix(gate).flat();
}

function compose(after, before) {
  if (!before) return after;
  const out = new Array(8);
  for (let row = 0; row < 2; row++) {
    for (let col = 0; col < 2; col++) {
      const i = 4*row, j = 2*col;
      out[i+j] = after[i]*before[j] - after[i+1]*before[j+1]
               + after[i+2]*before[j+4] - after[i+3]*before[j+5];
      out[i+j+1] = after[i]*before[j+1] + after[i+1]*before[j]
                 + after[i+2]*before[j+5] + after[i+3]*before[j+4];
    }
  }
  return out;
}

// Generated from native/fused-dense.wat with wat2wasm, then base64.
const kernelBytes = "AGFzbQEAAAABFAJgCn9/fHx8fHx8fHwAYAN/f38AAg8BA2VudgZtZW1vcnkCAAEDAwIAAQcOAgVsb2NhbAAAAmN4AAEKqQICxQECA38EfANAIAohCwNAIAsgAWohDCALKwMAIQ0gCysDCCEOIAwrAwAhDyAMKwMIIRAgCyACIA2iIAMgDqKhIAQgD6IgBSAQoqGgOQMAIAsgAiAOoiADIA2ioCAEIBCiIAUgD6KgoDkDCCAMIAYgDaIgByAOoqEgCCAPoiAJIBCioaA5AwAgDCAGIA6iIAcgDaKgIAggEKIgCSAPoqCgOQMIIAtBEGohCyALIAogAWpJDQALIAogAUEBdGohCiAKIABJDQALC2ACAn8CfgNAIAMgAXFFIAMgAnFBAEdxBEAgAyABciEEIAMpAwAhBSADKQMIIQYgAyAEKQMANwMAIAMgBCkDCDcDCCAEIAU3AwAgBCAGNwMICyADQRBqIQMgAyAASQ0ACws=";
let compiled;
export function denseStorage(length, budget) {
  const pages = Math.ceil(length*8/65536);
  if (typeof WebAssembly === 'undefined' || pages*65536 > budget) return null;
  try {
    compiled ??= new WebAssembly.Module(Uint8Array.from(atob(kernelBytes), ch=>ch.charCodeAt(0)));
    const memory = new WebAssembly.Memory({initial:pages,maximum:pages});
    const {exports:kernel} = new WebAssembly.Instance(compiled,{env:{memory}});
    return {a:new Float64Array(memory.buffer,0,length),kernel};
  } catch (error) {
    if (error instanceof WebAssembly.CompileError) return null; // Browser CSP.
    throw error;
  }
}

export function* evolveFusedDense(state, gates) {
  const a=state.groups[0].a, pending=Array(state.n).fill(null);
  const possiblyOne=new Uint8Array(state.n);
  function flush(q) {
    if (!pending[q]) return;
    state.denseKernel.local(a.byteLength,16*2**q,...pending[q]);
    pending[q]=null;
  }
  for (const gate of gates) {
    const {q,name}=gate;
    if (name==='cx') {
      const c=gate.controls[0];
      if (possiblyOne[c]) {
        flush(c); flush(q);
        state.denseKernel.cx(a.byteLength,16*2**q,16*2**c);
        possiblyOne[q]=1;
      }
    } else {
      const m=localMatrix(gate);
      pending[q]=compose(m,pending[q]);
      // Only an exactly nonzero |1><0| matrix entry can leave |0>.
      if (m[4]!==0 || m[5]!==0) possiblyOne[q]=1;
    }
    state.operations++;
    if (state.operations%64===0) yield state.operations;
  }
  for (let q=0; q<state.n; q++) flush(q);
}
