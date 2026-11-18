"""Original random-matching topology at reduced width; never promotes #70.
The full 100-wire fixture is planned with the same seed and gates as Diamond #70.
"""
import json, math, sys, time, resource
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native'))
from mps_exact import ExactMPS, Boundary, compile_ops, plan
import random
import numpy as np

def make(n,seed):
    # Exact Mulberry32 generator matching worker.rng; verify seed in JS fixture.
    s=seed
    def rng():
        nonlocal s
        s=(s+0x6D2B79F5)&0xffffffff
        t=s;t=((t^(t>>15))*(t|1))&0xffffffff
        t=(t^((t+(((t^(t>>7))*(t|61))&0xffffffff))&0xffffffff))&0xffffffff
        return ((t^(t>>14))&0xffffffff)/4294967296
    gs=[]
    for _ in range(100):
        for q in range(n):gs.append(dict(name='ry',q=q,controls=[],theta=rng()*2-1))
        inds=list(range(n))
        for i in range(n-1,0,-1):
            j=int(rng()*(i+1));inds[i],inds[j]=inds[j],inds[i]
        for i in range(0,n,2):gs.append(dict(name='cx',q=inds[i+1],controls=[inds[i]]))
    return gs

def inverse(gs):return [{**g,'theta':-g['theta']} if 'theta' in g else dict(g) for g in gs[::-1]]
def dense(n,gates):
    # Source-gather vector reference; does not call MPS or its gate matrices.
    a=np.zeros(1<<n,complex);a[0]=1;ids=np.arange(len(a));z=np.zeros_like(a)
    for g in gates:
        q=g['q'];flip=ids^(1<<q);one=(ids>>q)&1
        if g['name']=='cx':a=a[np.where(((ids>>g['controls'][0])&1)!=0,flip,ids)]
        else:
            c=math.cos(g['theta']/2);s=math.sin(g['theta']/2)
            a=c*a+np.where(one!=0,s,-s)*a[flip]
    return a

def main():
    start=time.monotonic();n=10;gs=make(n,8377);d=ExactMPS(n,gs,max_bytes=64*2**20,max_work=2**42);ref=dense(n,gs)
    out=np.empty_like(ref)
    for j in range(len(ref)):
        a=d.amplitude(format(j,f'0{n}b'));out[j]=complex(a['real'],a['imag'])
    max_error=float(np.max(np.abs(out-ref)));l2=float(np.linalg.norm(out-ref));assert max_error<1e-12 and l2<1e-11,(max_error,l2)
    inv=inverse(gs);recovered=ExactMPS(n,gs+inv,max_bytes=64*2**20,max_work=2**42)
    v=np.empty_like(ref)
    for j in range(len(ref)):
        a=recovered.amplitude(format(j,f'0{n}b'));v[j]=complex(a['real'],a['imag'])
    target=np.zeros_like(ref);target[0]=1;err=float(np.max(np.abs(v-target)));norm=float(recovered.expectation('I'*n));assert err<1e-12 and abs(norm-1)<1e-12,(err,norm)
    full=make(100,8377);reason=None
    try:plan(100,compile_ops(100,full+inverse(full)),1024*2**20,2**42)
    except Boundary as e:reason=str(e)
    assert reason is not None,'Full-width plan admitted; execute separately before claiming completion'
    return dict(qubits=n,depth=100,forwardGates=len(gs),fullGateOperations=len(gs+inv),forwardAllAmplitudes=len(ref),inverseAllAmplitudes=len(ref),forwardMaxAbsoluteError=max_error,forwardL2Error=l2,recoveredMaxAbsoluteError=err,recoveredNorm=norm,forwardStats=d.stats(),inverseStats=recovered.stats(),original100QubitGates=len(full)*2,original100QubitPreflightRefusal=reason,scope='Reduced-width random matching stress; original 100-qubit workload remains FAIL; no cancellation or truncation.',elapsedSeconds=time.monotonic()-start,peakRSSKiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
if __name__=='__main__':print(json.dumps(main(),allow_nan=False))
