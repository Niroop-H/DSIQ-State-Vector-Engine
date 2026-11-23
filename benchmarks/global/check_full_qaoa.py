"""Full dense NumPy oracle for previously unused graph instances at 21/22 qubits."""
import json
import math
import os
from pathlib import Path
import random
import subprocess
import tempfile
import numpy as np


def check(n):
    seed=107399+n
    rng=random.Random(seed)
    edges=[(i,j) for i in range(n) for j in range(i+1,n) if rng.random()<0.5]
    gates=[dict(name='h',q=q,controls=[]) for q in range(n)]
    indices=np.arange(1<<n,dtype=np.uint32)
    energy=np.zeros(len(indices),dtype=np.int16)
    for i,j in edges:
        odd=((indices>>i)^(indices>>j))&1
        energy+=1-2*odd.astype(np.int16)
    state=np.full(len(indices),2**(-n/2),dtype=np.complex128)
    for _ in range(2):
        theta=rng.uniform(-3,3)
        for i,j in edges:
            cx=dict(name='cx',q=j,controls=[i])
            gates.extend([cx,dict(name='rz',q=j,controls=[],theta=theta),cx])
        state*=np.exp(-0.5j*theta*energy.astype(np.float64))
        for q in range(n):
            beta=rng.uniform(-2,2)
            gates.append(dict(name='rx',q=q,controls=[],theta=beta))
            groups=state.reshape(-1,2,1<<q)
            x=groups[:,0,:].copy();y=groups[:,1,:].copy()
            c=math.cos(beta/2);s=-1j*math.sin(beta/2)
            groups[:,0,:]=c*x+s*y
            groups[:,1,:]=s*x+c*y
    probes=rng.sample(range(len(indices)),256)
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'circuit.json'
        path.write_text(json.dumps(dict(n=n,gates=gates,indices=probes)))
        p=subprocess.run(['node',str(Path(__file__).with_name('dsiq.mjs')),str(path)],
                         capture_output=True,text=True,check=True,timeout=120)
    row=json.loads(p.stdout);v=np.array(row['values'])
    error=abs(v[:,0]+1j*v[:,1]-state[probes])
    relative=float(max(error/abs(state[probes])))
    return dict(n=n,seed=seed,edges=len(edges),probes=len(probes),gates=len(gates),
                dsiq_ms=row['ms'],max_abs=float(max(error)),max_relative=relative,
                passed=bool(max(error)<1e-11 and relative<1e-7))


if __name__=='__main__':
    rows=[check(n) for n in (21,22)]
    print(json.dumps(rows,indent=2))
    raise SystemExit(any(not r['passed'] for r in rows))
