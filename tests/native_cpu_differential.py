"""Complete-state differential tests for the product-to-dense executable."""
import argparse
import json
import math
import random
import subprocess
from pathlib import Path

import numpy as np


def check(exe, n, seed):
    rng=random.Random(seed)
    gates=[]
    # Known zero/one controls, nontrivial local phases, and two kinds of SWAP.
    if n>=2:
        gates.extend([('cp',0,0.23,[1]),('x',1,0,[]),('h',0,0,[]),
                      ('cp',1,-1.7,[0]),('swap',0,0,[1]),('h',0,0,[]),
                      ('cx',1,0,[0]),('swap',0,0,[1])])
    for _ in range(40):
        q=rng.randrange(n);name=rng.choice(['h','x','rx','ry','rz','p']+
                                           (['cx','cp','swap','mcx'] if n>=2 else []))
        count=(rng.randrange(1,n) if name=='mcx' else int(name in ('cx','cp','swap')))
        controls=rng.sample([i for i in range(n) if i!=q],count)
        gates.append((name,q,rng.uniform(-8,8),controls))
    ref=np.zeros(1<<n,complex);ref[0]=1
    idx=np.arange(len(ref))
    for name,q,t,c in gates:
        stride=1<<q
        if name=='swap':
            partner=1<<c[0]
            lookup=np.where(((idx>>q)^(idx>>c[0]))&1,idx^stride^partner,idx)
            ref=ref[lookup];continue
        mask=sum(1<<i for i in c)
        low=idx[((idx&stride)==0)&((idx&mask)==mask)]
        high=low+stride
        a,b=math.cos(t/2),math.sin(t/2)
        matrices={'h':np.array([[1,1],[1,-1]])/math.sqrt(2),'x':[[0,1],[1,0]],
                  'rx':[[a,-1j*b],[-1j*b,a]],'ry':[[a,-b],[b,a]],
                  'rz':np.diag(np.exp(np.array([-0.5j,0.5j])*t)),
                  'p':np.diag([1,np.exp(1j*t)])}
        mat=matrices[{'cx':'x','mcx':'x','cp':'p'}.get(name,name)]
        ref[low],ref[high]=mat@np.stack((ref[low],ref[high]))
    lines=[f'{n} {len(gates)} {len(ref)}']
    lines+=[' '.join(map(str,[k,q,t,len(cs),*cs])) for k,q,t,cs in gates]
    lines+=list(map(str,idx))
    p=subprocess.run([exe],input='\n'.join(lines),text=True,capture_output=True,check=True)
    raw=np.asarray(json.loads(p.stdout)['values'])
    v=raw[:,0]+1j*raw[:,1]
    return float(max(abs(v-ref))),float(abs(np.vdot(v,v)-1))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('executable',type=Path)
    exe=parser.parse_args().executable.resolve()
    rows=[check(exe,n,126743+100*n+seed) for n in range(1,13) for seed in range(10)]
    err,norm=np.max(rows,axis=0)
    print(json.dumps(dict(circuits=len(rows),coefficients=10*sum(2**n for n in range(1,13)),
                          max_abs=err,max_norm_error=norm)))
    if err>1e-13 or norm>1e-12:raise SystemExit(1)
