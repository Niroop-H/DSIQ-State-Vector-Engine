"""Deep connected stress on bounded chain crossings. Not the full #70 fixture."""
import json, math, random, sys, time, resource
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native'))
from mps_exact import ExactMPS,Boundary,compile_ops,plan
from importlib.machinery import SourceFileLoader
ref=SourceFileLoader('mps_audit',str(Path(__file__).with_name('mps-audit.py'))).load_module()
gate=ref.gate

def main():
    n=100;r=random.Random(37921);bonds=list(range(n-1));r.shuffle(bonds);gs=[]
    for layer in range(100):
        for q in range(n):gs.append(gate(r.choice(['rx','ry','rz']),q,theta=r.uniform(-1.4,1.4)))
        if layer<len(bonds):
            q=bonds[layer];a,b=(q,q+1) if r.random()<.5 else (q+1,q);gs.append(gate('cx',b,[a]))
    inv=[{**g,'theta':-g['theta']} if 'theta' in g else dict(g) for g in gs[::-1]]
    start=time.monotonic();d=ExactMPS(n,gs,max_bytes=256*2**20,max_work=2**40);forward_norm=d.expectation('I'*n);assert abs(forward_norm-1)<1e-12;errs=[];phases=[]
    # Full gate tensor oracle for the forward midpoint; no use of inverse.
    for _ in range(4):
        b=d.sample(r);a=d.amplitude(b);z=ref.tensor_reference(n,gs,b)
        assert z!=0 and a['log2Magnitude'] is not None
        e=abs(a['log2Magnitude']-math.log2(abs(z)));p=abs(math.remainder(a['phase']-math.atan2(z.imag,z.real),2*math.pi));assert e<1e-10 and p<1e-10,(e,p);errs.append(e);phases.append(p)
    s=ExactMPS(n,gs+inv,max_bytes=256*2**20,max_work=2**40);z=s.amplitude('0'*n);p=z['real']**2+z['imag']**2;assert abs(p-1)<1e-12 and abs(z['real']-1)<1e-12 and abs(z['imag'])<1e-12,(p,z)
    norm=s.expectation('I'*n);assert abs(norm-1)<1e-12
    for q in range(n):
        pauli='I'*(n-q-1)+'Z'+'I'*q;assert abs(s.expectation(pauli)-1)<1e-12
    samples=[s.sample(r) for _ in range(64)];assert set(samples)=={'0'*n}
    return dict(qubits=n,forwardLayers=100,forwardGates=len(gs),inverseGates=len(inv),fullGateOperations=len(gs)+len(inv),distinctConnectedChainBonds=len(bonds),forwardNorm=forward_norm,forwardQueryComparisons=4,maxLog2Error=max(errs),maxPhaseError=max(phases),recoveredAmplitude=z,recoveredProbability=p,recoveredNorm=norm,checkedPauliZ=100,recoveredSamples=len(samples),forwardStats=d.stats(),inverseStats=s.stats(),elapsedSeconds=time.monotonic()-start,peakProcessRSSKiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,scope='100 layers with random local rotations and one distinct chain-bond entangler per layer, not the original 50-random-matchings-per-layer stress; no cancellation; independent forward midpoint oracle')
if __name__=='__main__':print(json.dumps(main(),allow_nan=False))
