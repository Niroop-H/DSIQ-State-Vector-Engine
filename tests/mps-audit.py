"""Test-only source-scatter dense and opt_einsum reference implementations."""
import json,sys,math,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native'))
from mps_exact import ExactMPS,Boundary,compile_ops,plan
import numpy as np
import opt_einsum as oe

def gate(name,q,cs=(),**kw):return dict(name=name,q=q,controls=list(cs),**kw)
def dense(n,gs):
    a=np.zeros(1<<n,complex);a[0]=1
    for g in gs:
        name,q,cs=g['name'],g['q'],g['controls'];b=np.zeros_like(a);t=g.get('theta',0);c=math.cos(t/2);s=math.sin(t/2)
        for x,v in enumerate(a):
            bit=(x>>q)&1;y=x^(1<<q)
            if name=='swap':
                z=cs[0];k=(x>>z)&1;b[x if k==bit else x^(1<<q)^(1<<z)]+=v;continue
            if name=='fsim':
                z=cs[0];k=(x>>z)&1
                if bit==k:b[x]+=v*(np.exp(-1j*g['phi']) if bit else 1)
                else:b[x]+=v*math.cos(t);b[x^(1<<q)^(1<<z)]+=-1j*math.sin(t)*v
                continue
            if cs and not (x>>cs[0])&1:b[x]+=v;continue
            if name in ('cx','x'):b[y]+=v
            elif name=='h':b[x]+=v*(-1 if bit else 1)/math.sqrt(2);b[y]+=v/math.sqrt(2)
            elif name=='ry':b[x]+=v*c;b[y]+=v*(-s if bit else s)
            elif name=='rx':b[x]+=v*c;b[y]+=-1j*s*v
            elif name=='rz':b[x]+=v*np.exp((1j if bit else -1j)*t/2)
            elif name in ('p','cp'):b[x]+=v*(np.exp(1j*t) if bit else 1)
            elif name=='cz':b[x]+=v*(-1 if bit else 1)
            elif name=='t':b[x]+=v*np.exp(1j*bit*math.pi/4)
            elif name=='y':b[y]+=v*(-1j if bit else 1j)
            else:raise ValueError(name)
        a=b
    return a

def dense_expect(a,p):
    s=0j
    for x,v in enumerate(a):
        y=x;w=1+0j
        for q,g in enumerate(p[::-1]):
            bit=(x>>q)&1
            if g in 'XY':y^=1<<q
            if g=='Y':w*=(-1j if bit else 1j)
            elif g=='Z':w*=(-1 if bit else 1)
        s+=a[y].conjugate()*w*v
    return s.real

def tensor_reference(n,gs,bits):
    wires=list(range(n));nextid=n;a=[]
    for x in wires:a.extend([np.array([1.,0.],complex),[x]])
    for g in gs:
        q=g['q'];cs=g['controls'];t=g.get('theta',0);name=g['name']
        if name=='ry':m=np.array([[np.cos(t/2),-np.sin(t/2)],[np.sin(t/2),np.cos(t/2)]])
        elif name=='rz':m=np.diag(np.exp(np.array([-1j,1j])*t/2))
        elif name=='rx':m=np.array([[np.cos(t/2),-1j*np.sin(t/2)],[-1j*np.sin(t/2),np.cos(t/2)]])
        elif name=='cp':m=np.diag([1,np.exp(1j*t)])
        elif name=='cz':m=np.diag([1,-1])
        elif name=='cx':m=np.array([[0,1],[1,0]])
        else:raise ValueError(name)
        if not cs:a.extend([m,[nextid,wires[q]]]);wires[q]=nextid;nextid+=1
        else:
            c=cs[0];u=np.zeros((2,2,2,2),complex);u[0,:,0,:]=np.eye(2);u[1,:,1,:]=m;a.extend([u,[nextid,nextid+1,wires[c],wires[q]]]);wires[c]=nextid;wires[q]=nextid+1;nextid+=2
    for q,x in enumerate(wires):a.extend([np.eye(2)[int(bits[n-1-q])],[x]])
    path,info=oe.contract_path(*a,[],optimize='greedy')
    if info.largest_intermediate>2**19 or info.opt_cost>2**28:raise RuntimeError('Reference budget exceeded')
    return complex(oe.contract(*a,[],optimize=path))

def circuit(n,depth,seed):
    r=random.Random(seed);gs=[]
    for d in range(depth):
        for q in range(n):gs.append(gate(('rx','ry','rz')[(q+d)%3],q,theta=r.uniform(-2,2)))
        for q in range(d%2,n-1,2):gs.append(gate(('cx','cz','cp')[(q+d)%3],q+1,[q],theta=r.uniform(-1,1)))
    return gs

def main():
    r=random.Random(97413);mx=mp=0;na=no=0;tot=[]
    for trial in range(32):
        n=6;gs=[]
        for _ in range(30):
            name=r.choice(['h','x','y','rx','ry','rz','t','cx','cz','cp','swap','fsim']);q=r.randrange(n);c=r.choice([i for i in range(n) if i!=q]);gs.append(gate(name,q,[c] if name in ('cx','cz','cp','swap','fsim') else [],theta=r.uniform(-2,2),phi=r.uniform(-2,2)))
        d=ExactMPS(n,gs);a=dense(n,gs);assert abs(d.expectation('I'*n)-1)<1e-12
        for x,v in enumerate(a):
            u=d.amplitude(format(x,'06b'));e=abs(complex(u['real'],u['imag'])-v);mx=max(mx,e);na+=1;assert e<1e-13,(trial,x,e)
        for _ in range(24):
            p=''.join(r.choices('IXYZ',k=n));e=abs(d.expectation(p)-dense_expect(a,p));mp=max(mp,e);no+=1;assert e<1e-12,(trial,p,e)
        if trial<4:
            shots=4096;counts=np.zeros(1<<n);pr=abs(a)**2
            for i in range(shots):counts[int(d.sample(r),2)]+=1
            tv=float(np.sum(abs(counts/shots-pr))/2);assert tv<.1;tot.append(tv)
    print('dense tests complete',file=sys.stderr,flush=True)
    wide=[]
    for n,depth in ((100,8),(1024,4)):
        gs=circuit(n,depth,723+n);d=ExactMPS(n,gs,max_bytes=256*2**20,max_work=2**39);norm=d.expectation('I'*n);assert abs(norm-1)<2e-11,(n,norm);samples=[d.sample(r) for _ in range(32)];assert len(set(samples))==32
        # Sampling gives non-negligible wide outcomes, avoiding underflow in reference.
        queries=samples[:3];maxlog=maxphase=0;probes=[]
        for bits in queries:
            got=d.amplitude(bits);ref=tensor_reference(n,gs,bits)
            if ref and got['log2Magnitude'] is not None:
                logerr=abs(got['log2Magnitude']-math.log2(abs(ref)));phaseerr=abs(math.remainder(got['phase']-math.atan2(ref.imag,ref.real),2*math.pi));maxlog=max(maxlog,logerr);maxphase=max(maxphase,phaseerr);assert logerr<1e-7 and phaseerr<1e-7,(n,logerr,phaseerr);probes.append(dict(log2=got['log2Magnitude'],logError=logerr,phaseError=phaseerr))
        assert len(probes)==len(queries),('Reference underflow',n)
        wide.append(dict(n=n,depth=depth,gates=len(gs),norm=norm,maxLogError=maxlog,maxPhaseError=maxphase,referenceQueries=len(probes),uniqueSamples=len(set(samples)),stats=d.stats()));print('wide',n,'complete',file=sys.stderr,flush=True)
    rejected=0
    for args in [(8,circuit(8,8,5),1024,2**36),(8,circuit(8,8,5),2**24,1)]:
        try:plan(args[0],compile_ops(args[0],args[1]),*args[2:])
        except Boundary:rejected+=1
        else:raise AssertionError('Budget accepted')
    for theta in (float('nan'),float('inf'),-float('inf')):
        try:ExactMPS(1,[gate('ry',0,theta=theta)])
        except ValueError:rejected+=1
        else:raise AssertionError('Invalid angle accepted')
    return dict(denseCircuits=32,amplitudeComparisons=na,observableComparisons=no,maxAmplitudeError=mx,maxObservableError=mp,sampledShots=16384,samplingTV=tot,wide=wide,explicitRejections=rejected)
if __name__=='__main__':print(json.dumps(main(),allow_nan=False))
