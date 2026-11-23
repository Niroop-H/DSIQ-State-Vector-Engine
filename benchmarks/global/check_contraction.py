"""Reproduce the unchanged boundary fixture and validate or profile its amplitude."""
import hashlib
import json
from pathlib import Path
import random
import statistics
import sys
import time

import numpy as np
from dense_boundary import make_circuit
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'native'))
from qaoa_contraction import amplitude, contract_slice, factors, plan


def get_terms(n, bits):
    edges, gates = make_circuit(n)
    costs = sorted({g['theta'] for g in gates if g['name']=='rz'})
    mixers = sorted({g['theta'] for g in gates if g['name']=='rx'})
    # Check the factorization against every gate before applying it.
    rebuilt = [dict(name='h',q=q,controls=[]) for q in range(n)]
    for gamma,beta in zip(costs,mixers,strict=True):
        for i,j in edges:
            cx = dict(name='cx',q=j,controls=[i])
            rebuilt.extend([cx,dict(name='rz',q=j,controls=[],theta=gamma),cx])
        rebuilt.extend(dict(name='rx',q=i,controls=[],theta=beta) for i in range(n))
    assert rebuilt == gates
    digest = hashlib.sha256(json.dumps(gates, sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return factors(n,edges,costs,mixers,bits), gates, digest


def dense(n,gates):
    state = np.zeros(1<<n,complex)
    state[0] = 1
    index = np.arange(len(state))
    for g in gates:
        q,k = g['q'], g['name']
        if k=='cx':
            rows = index[((index>>g['controls'][0])&1 != 0) & ((index>>q)&1 == 0)]
            cols = rows^(1<<q)
            state[rows],state[cols] = state[cols],state[rows]
            continue
        if k=='h':
            mat = np.array([[1,1],[1,-1]])/np.sqrt(2)
        elif k=='rz':
            mat = np.diag(np.exp([-0.5j*g['theta'],0.5j*g['theta']]))
        elif k=='rx':
            c,s = np.cos(g['theta']/2),-1j*np.sin(g['theta']/2)
            mat = np.array([[c,s],[s,c]])
        else:
            raise ValueError(k)
        pairs = state.reshape(-1,2,1<<q)
        pairs[:] = mat @ pairs
    return state


def checks():
    rows=[]
    for n,axes in ((6,4),(10,7),(14,13),(18,18)):
        terms,gates,_ = get_terms(n,'0'*n)
        schedule = plan(terms,axes)
        ref = dense(n,gates)
        errors=[]
        for i in (0,1,int('10'*(n//2),2),(1<<n)-1):
            terms,_,_ = get_terms(n,format(i,f'0{n}b'))
            result = amplitude(terms,schedule,1<<15)
            error=abs(result-ref[i])
            assert error < 1e-12 and error <= 1e-9*abs(ref[i])
            errors.append(error)
        rows.append(dict(n=n,probes=len(errors),slices=schedule['slices'],max_abs=max(errors)))
    return rows


def profile():
    n=50
    terms,gates,digest = get_terms(n,'0'*n)
    schedule=plan(terms,max_axes=20)
    times=[]
    rng=random.Random(587)
    for _ in range(5):
        assignment={q:rng.randrange(2) for q in schedule['fixed']}
        start=time.perf_counter()
        piece=contract_slice(terms,schedule['order'],assignment)
        assert np.isfinite(piece)
        times.append(time.perf_counter()-start)
    return dict(n=n,gates=len(gates),edges=len(make_circuit(n)[0]),sha256=digest,
                schedule=schedule,pilot_seconds=times,median_seconds=statistics.median(times),
                complete=False,amplitude=None)


if __name__=='__main__':
    print(json.dumps(dict(checks=checks(),target=profile()),indent=2))
