"""Matched CPU comparison using the same QASMBench fixtures and queried amplitudes."""
import importlib.metadata
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

import numpy as np
from run import prepare, baseline, CASES, REV

HERE=Path(__file__).resolve().parent


def canonical(doc):
    gates=[]
    for source in doc['gates']:
        g=source.copy()
        if g['name'] in ('z','s','t','cz'):
            g['theta']={'z':math.pi,'s':math.pi/2,'t':math.pi/4,'cz':math.pi}[g['name']]
            g['name']='cp' if g['controls'] else 'p'
        if g['name']=='ccx':g['name']='mcx'
        gates.append(g)
    return dict(doc,gates=gates)


def worker(engine,doc):
    n=doc['n']
    if engine=='aer':
        from qiskit import QuantumCircuit
        from qiskit_aer import AerSimulator
        t=time.perf_counter();qc=QuantumCircuit(n)
        for g in doc['gates']:
            c,q,k=g['controls'],g['q'],g['name']
            if k=='mcx':qc.mcx(c,q)
            else:getattr(qc,k)(*([g['theta']] if 'theta' in g else []),*c,q)
        qc.save_amplitudes(doc['indices'])
        sim=AerSimulator(method='statevector',precision='double',max_parallel_threads=1,
                         enable_truncation=False,zero_threshold=0)
        vals=sim.run(qc,shots=1).result().data(0)['amplitudes']
    else:
        import qibo
        from qibo import gates,Circuit
        t=time.perf_counter()
        if engine=='qibo-jit':qibo.set_backend('qibojit',platform='numba')
        else:qibo.set_backend('numpy')
        qc=Circuit(n)
        for g in doc['gates']:
            wires=[n-1-q for q in [*g['controls'],g['q']]]
            k=g['name']
            if k=='mcx':op=gates.X(wires[-1]).controlled_by(*wires[:-1])
            else:
                factory={'h':gates.H,'x':gates.X,'cx':gates.CNOT,'swap':gates.SWAP,
                         'rx':gates.RX,'ry':gates.RY,'rz':gates.RZ,'p':gates.U1,'cp':gates.CU1}[k]
                op=factory(*wires,*([g['theta']] if 'theta' in g else []))
            qc.add(op)
        state=np.asarray(qc().state())
        if state.dtype!=np.complex128:raise ValueError(f'Unexpected precision {state.dtype}')
        vals=state[doc['indices']]
    print(json.dumps(dict(ms=1000*(time.perf_counter()-t),values=[[z.real,z.imag] for z in vals])))


def compare(case):
    orig,sha=prepare(case)
    ref=baseline(orig,None)[orig['indices']]
    doc=canonical(orig)
    engines=['dsiq-native','qibo-jit','aer','qibo-numpy','dsiq-js']
    rows={k:[] for k in engines};errors={}
    lines=[f"{doc['n']} {len(doc['gates'])} {len(doc['indices'])}"]
    lines+=[' '.join(map(str,[g['name'],g['q'],g.get('theta',0),len(g['controls']),*g['controls']])) for g in doc['gates']]
    lines+=list(map(str,doc['indices']))
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'input.json';path.write_text(json.dumps(doc))
        for rep in range(3):
            for k in engines[rep:]+engines[:rep]:
                if k in errors:continue
                cmd=([os.environ['DSIQ_NATIVE_BIN']] if k=='dsiq-native' else
                     ['node',str(HERE/'dsiq.mjs'),str(path)] if k=='dsiq-js' else
                     [sys.executable,__file__,'worker',k,str(path)])
                try:
                    t=time.perf_counter()
                    proc=subprocess.run(cmd,input='\n'.join(lines) if k=='dsiq-native' else '',
                                        text=True,capture_output=True,timeout=150)
                    wall=1000*(time.perf_counter()-t)
                    if proc.returncode:raise RuntimeError(proc.stderr[-1200:])
                    # Qibo may print its backend banner to stdout.
                    obs=json.loads(proc.stdout.strip().splitlines()[-1]);v=np.asarray(obs['values'])
                    if v.shape!=(len(ref),2) or not np.isfinite(v).all():raise ValueError('Invalid output')
                    delta=abs(v[:,0]+1j*v[:,1]-ref);mask=abs(ref)>1e-14
                    rows[k].append(dict(ms=obs['ms'],process_ms=wall,max_abs=float(max(delta)),
                                        max_relative=float(max(delta[mask]/abs(ref[mask]),default=0))))
                except Exception as e:errors[k]=str(e)
    results={}
    for k,samples in rows.items():
        if k in errors:results[k]=dict(error=errors[k]);continue
        results[k]=dict(samples=samples,ms=statistics.median(v['ms'] for v in samples),
                        passed=all(v['max_abs']<=1e-12 and v['max_relative']<=1e-9 for v in samples))
    return dict(case=case,n=doc['n'],gates=len(doc['gates']),probes=doc['indices'],sha256=sha,
                revision=REV,engines=results,cpu=next(s for s in Path('/proc/cpuinfo').read_text().splitlines() if s.startswith('model name')),
                versions={k:importlib.metadata.version(k) for k in ('qibo','qibojit','qiskit','qiskit-aer','numpy')})


if __name__=='__main__':
    if sys.argv[1]=='worker':
        worker(sys.argv[2],json.loads(Path(sys.argv[3]).read_text()))
    else:
        # qibojit chooses its initial thread count from the affinity mask.
        # Bind the parent and all five child adapters to the same single CPU.
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        result=compare(CASES[int(sys.argv[1])])
        Path('result.json').write_text(json.dumps(result,indent=2))
        raise SystemExit(any(not e.get('passed') for e in result['engines'].values()))
