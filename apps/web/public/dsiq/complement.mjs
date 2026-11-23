// A uniform initial state, RX rotations and ZZ rotations commute with flipping
// every bit (the initial state is invariant). Complementary amplitudes agree.
function zzAt(gates, i) {
  const a=gates[i], b=gates[i+1], c=gates[i+2];
  return a?.name==='cx' && b?.name==='rz' && c?.name==='cx' &&
    a.q===b.q && a.q===c.q && a.controls[0]===c.controls[0];
}

export function complementEligible(n,gates) {
  if (n<2 || n>24 || gates.length<=n) return false;
  const seen=new Set();
  for (let i=0;i<n;i++) {
    if (gates[i].name!=='h' || seen.has(gates[i].q)) return false;
    seen.add(gates[i].q);
  }
  for (let i=n;i<gates.length;) {
    if (gates[i].name==='rx') i++;
    else if (zzAt(gates,i) && Math.abs(gates[i+1].theta)<=2*Math.PI) i+=3;
    else return false;
  }
  return true;
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
  for (let k=0;k<=count;k++) {
    const t=angle*(k-count/2);
    re[k]=Math.cos(t); im[k]=Math.sin(t);
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
  for (let i=0;i<half;i++) a[2*i]=scale;
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
  for (let i=0;i<half;i++) {
    const j=2*(2*half-1-i);
    a[j]=a[2*i]; a[j+1]=a[2*i+1];
  }
}
