// A uniform initial state, RX rotations and ZZ rotations commute with flipping
// every bit (the initial state is invariant). Complementary amplitudes agree.
function zzAt(gates, i) {
  const a=gates[i], b=gates[i+1], c=gates[i+2];
  return a?.name==='cx' && b?.name==='rz' && c?.name==='cx' &&
    a.q===b.q && a.q===c.q && a.controls[0]===c.controls[0];
}

export function complementSchedule(n,gates) {
  if (n<2 || n>24 || gates.length<=n) return null;
  // Read the next gate touching each wire. A CNOT sandwich may have
  // unrelated operations on other wires between its three gates.
  const next=new Int32Array(n).fill(-1);
  const nextTarget=new Int32Array(gates.length), nextControl=new Int32Array(gates.length);
  for (let i=gates.length-1;i>=0;i--) {
    const {name,q,controls}=gates[i];
    if (!['h','rx','rz','cx'].includes(name)) return null;
    nextTarget[i]=next[q]; next[q]=i;
    if (name==='cx') {
      const c=controls[0]; nextControl[i]=next[c]; next[c]=i;
    }
  }
  const prefix=[], used=new Uint8Array(gates.length);
  for (const i of next) {
    if (i<0 || gates[i].name!=='h') return null;
    used[i]=1; prefix.push(gates[i]);
  }
  const last=new Int32Array(n), layers=[];
  for (let i=0;i<gates.length;i++) {
    if (used[i]) continue;
    const g=gates[i], q=g.q;
    let level=last[q], block;
    if (g.name==='rx') {
      level|=1;
      block=[g];
    } else if (g.name==='cx') {
      const c=g.controls[0], j=nextTarget[i], k=nextControl[i];
      if (j<0 || k<0 || gates[j].name!=='rz' || nextTarget[j]!==k ||
          gates[k].name!=='cx' || gates[k].q!==q || gates[k].controls[0]!==c) return null;
      level=Math.max(level,last[c]); level+=level%2;
      used[j]=used[k]=1;
      last[c]=level;
      block=[g,gates[j],gates[k]];
    } else return null;
    last[q]=level;
    (layers[level]??=[]).push(...block);
  }
  // Even layers contain commuting ZZ interactions, odd layers commuting RXs.
  for (const layer of layers) if (layer) for (const gate of layer) prefix.push(gate);
  return prefix;
}

function popcount(x) {
  x-= (x>>>1)&0x55555555;
  x=(x&0x33333333)+((x>>>2)&0x33333333);
  return (((x+(x>>>4))&0x0f0f0f0f)*0x01010101)>>>24;
}

function rotateZZ(a,half,neighbors,count,angle) {
  // Gray order changes one bit at a time. The number of cut edges changes
  // by the number of equal neighbors minus the number of unequal neighbors.
  const re=new Float64Array(count+1), im=new Float64Array(count+1);
  // Build integer powers from the same half-angle as the elementary RZ.
  // This avoids multiplying an arbitrarily large angle before reduction.
  const phaseRe=new Float64Array(count+1), phaseIm=new Float64Array(count+1);
  phaseRe[0]=1;
  const c=Math.cos(angle/2), s=Math.sin(angle/2);
  for (let k=1;k<=count;k++) {
    phaseRe[k]=phaseRe[k-1]*c-phaseIm[k-1]*s;
    phaseIm[k]=phaseRe[k-1]*s+phaseIm[k-1]*c;
  }
  for (let k=0;k<=count;k++) {
    const power=2*k-count;
    re[k]=phaseRe[Math.abs(power)];
    im[k]=Math.sign(power)*phaseIm[Math.abs(power)];
  }
  const degree=neighbors.map(popcount);
  let bits=0,cut=0;
  for (let i=0;i<half;i++) {
    const j=2*bits, x=a[j],y=a[j+1];
    a[j]=x*re[cut]-y*im[cut]; a[j+1]=x*im[cut]+y*re[cut];
    if (i+1===half) break;
    const flip=(i+1)&-(i+1), q=31-Math.clz32(flip);
    const delta=degree[q]-2*popcount(bits&neighbors[q]);
    cut+=(bits&flip)?-delta:delta;
    bits^=flip;
  }
}

function rotateX(a,half,target,angle) {
  const c=Math.cos(angle/2), s=Math.sin(angle/2);
  const stride=2**target;
  const block=stride===half?half/2:stride;
  const xor=stride===half?half-1:stride;
  for (let base=0;base<half;base+=2*block) {
    for (let k=base;k<base+block;k++) {
      const i=2*k,j=2*(k^xor);
      const x=a[i],y=a[i+1],u=a[j],v=a[j+1];
      a[i]=c*x+s*v; a[i+1]=c*y-s*u;
      a[j]=c*u+s*y; a[j+1]=c*v-s*x;
    }
  }
}

export function* evolveComplement(state,gates) {
  const a=state.groups[0].a, n=state.n, half=2**(n-1);
  const scale=2**(-n/2);
  state.denseKernel.uniform(16*half,scale);
  let pos=n;
  while (pos<gates.length) {
    if (gates[pos].name==='rx') {
      const small=[], large=[];
      const tile=Math.min(2048,half);
      while (pos<gates.length && gates[pos].name==='rx') {
        const {q,theta}=gates[pos++];
        const op={q,theta,c:Math.cos(theta/2),s:Math.sin(theta/2)};
        (2**q<tile?small:large).push(op);
      }
      for (let start=0;start<half;start+=tile) {
        for (const op of small) {
          state.denseKernel.rx(16*start,16*(start+tile),16*2**op.q,op.c,op.s);
        }
      }
      for (const op of large) {
        if (op.q<n-1) state.denseKernel.rx(0,16*half,16*2**op.q,op.c,op.s);
        else rotateX(a,half,op.q,op.theta);
      }
    } else {
      const neighbors=new Uint32Array(n), angle=gates[pos+1].theta;
      let count=0;
      while (zzAt(gates,pos) && gates[pos+1].theta===angle) {
        const {q,controls:[c]}=gates[pos];
        if (neighbors[q]&(1<<c)) break;
        neighbors[q]|=1<<c; neighbors[c]|=1<<q; count++; pos+=3;
      }
      rotateZZ(a,half,neighbors,count,angle);
    }
    state.operations=pos;
    yield pos;
  }
  state.denseKernel.mirror(16*half);
}
