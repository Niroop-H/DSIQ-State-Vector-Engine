"""Single-thread FP64, same path-QAOA amplitudes and norm, three new processes."""
import importlib.metadata
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'benchmarks/global'))
from wide_qaoa import amplitude, fixture


def worker(engine,doc):
    if engine=='quimb':
        from quimb.tensor import CircuitMPS
        start=time.perf_counter()
        circuit=CircuitMPS(doc['n'],gate_opts={'cutoff':0.0,'max_bond':None})
        for g in doc['gates']:
            name='CNOT' if g['name']=='cx' else g['name'].upper()
            args=([g['theta']] if 'theta' in g else [])+g['controls']+[g['q']]
            circuit.apply_gate(name,*args)
        state=circuit.psi
        if doc['n']==1:
            vector=np.asarray(state.to_dense()).reshape(2)
            values=[complex(vector[int(bits,2)]) for bits in doc['queries']]
            norm=float(np.vdot(vector,vector).real)
        else:
            values=[complex(state.amplitude(bits[::-1])) for bits in doc['queries']]
            norm=float(abs(state.norm())**2)
    else:
        sys.path.insert(0,str(ROOT/'native'))
        from mps_exact import execute
        start=time.perf_counter()
        r=execute(**doc)
        values=[complex(v['real'],v['imag']) for v in r['amplitudes']]
        norm=r['norm']
    return dict(ms=1000*(time.perf_counter()-start),norm=norm,amplitudes=[[z.real,z.imag] for z in values])


def compare(n):
    seed=381011+n
    doc,edges,mixer=fixture(n,seed)
    oracle=np.array([amplitude(b,edges,mixer) for b in doc['queries']])
    rows={'dsiq':[],'quimb':[]}
    for rep in range(3):
        for name in (('dsiq','quimb') if rep%2==0 else ('quimb','dsiq')):
            start=time.perf_counter()
            p=subprocess.run([sys.executable,__file__,'worker',name],input=json.dumps(doc),
                             text=True,capture_output=True,timeout=120,check=True)
            elapsed=time.perf_counter()-start
            obs=json.loads(p.stdout);v=np.array(obs.pop('amplitudes'))
            error=abs(v[:,0]+1j*v[:,1]-oracle)
            rows[name].append(dict(**obs,process_ms=1000*elapsed,max_abs=float(max(error)),
                                   max_relative=float(max(error/abs(oracle)))))
    engines={}
    for name,samples in rows.items():
        engines[name]=dict(samples=samples,ms=statistics.median(s['ms'] for s in samples),
          passed=all(s['max_abs']<1e-13 and s['max_relative']<1e-9 and abs(s['norm']-1)<1e-12 for s in samples))
    return dict(n=n,seed=seed,engines=engines,versions={p:importlib.metadata.version(p) for p in ('numpy','quimb')},
                cpu=next(s for s in Path('/proc/cpuinfo').read_text().splitlines() if s.startswith('model name')))


if __name__=='__main__':
    if sys.argv[1]=='worker':
        print(json.dumps(worker(sys.argv[2],json.load(sys.stdin))))
    else:
        result=compare(int(sys.argv[1]))
        Path('result.json').write_text(json.dumps(result,indent=2))
        sys.exit(any(not x['passed'] for x in result['engines'].values()))
