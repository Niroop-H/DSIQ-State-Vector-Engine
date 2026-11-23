"""Single-thread selected-amplitude benchmark. All adapters consume the same normalized gates."""
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import resource
import statistics
import subprocess
import sys
import tempfile
import time

import numpy as np

HERE=Path(__file__).resolve().parent
ENGINES=['quest','dsiq','aer','qsim','qulacs']
REPS=3

def build(name,n):
    from mqt.bench import get_benchmark, BenchmarkLevel
    qc=get_benchmark(name,BenchmarkLevel.ALG,n).remove_final_measurements(inplace=False)
    qc=qc.assign_parameters({p:0.317+0.241*i for i,p in enumerate(qc.parameters)})
    gates=[]
    def add(name,q,controls=(),angle=None):
        g=dict(name=name,q=q,controls=list(controls))
        if angle is not None:g['theta']=float(angle)
        gates.append(g)
    def lower(op,wires):
        name=op.name
        if name in ('measure','reset'):raise ValueError(name)
        if name in ('barrier','id'):return
        if name in ('h','x','p','cp','rz','ry','rx','cx','swap','mcx','ccx','u1','mcp','mcphase'):
            q=wires[-1]; c=wires[:-1]
            if getattr(op,'ctrl_state',(1<<len(c))-1)!=(1<<len(c))-1:raise ValueError("open control")
            if name in ('mcp','mcphase'):
                if float(op.params[0])!=math.pi:raise ValueError("unsupported multi-control angle")
                add('h',q);add('mcx',q,c);add('h',q)
            else:add({'ccx':'mcx','u1':'p'}.get(name,name),q,c,op.params[0] if op.params else None)
        elif name in ('u','u3'):
            t,p,l=map(float,op.params)
            add('p',wires[0],angle=l);add('ry',wires[0],angle=t);add('p',wires[0],angle=p)
        else:
            circ=op.definition
            if circ is None:raise ValueError(name)
            for inst in circ.data:
                lower(inst.operation,[wires[circ.find_bit(q).index] for q in inst.qubits])
    for inst in qc.data:
        lower(inst.operation,[qc.find_bit(q).index for q in inst.qubits])
    n=qc.num_qubits
    probes=sorted({0,(1<<n)-1,1<<(n-1),*random.Random(87916+n).sample(range(1<<n),64)})
    return dict(n=n,gates=gates,indices=probes)

def worker(engine,path):
    d=json.loads(path.read_text());n=d['n'];ids=d['indices']
    if engine=='aer':
        from qiskit import QuantumCircuit
        from qiskit_aer import AerSimulator
        t=time.perf_counter();qc=QuantumCircuit(n)
        for g in d['gates']:
            q=g['q'];c=g['controls'];name=g['name']
            if name=='mcx':qc.mcx(c,q)
            else:getattr(qc,name)(*([g['theta']] if 'theta' in g else []),*c,q)
        qc.save_amplitudes(ids)
        sim=AerSimulator(method='statevector',precision='double',enable_truncation=False,max_parallel_threads=1,zero_threshold=0)
        res=sim.run(qc,shots=1).result()
        if not res.success:raise ValueError(res.status)
        vals=res.data(0)['amplitudes']
    elif engine=='qsim':
        import cirq,qsimcirq
        t=time.perf_counter();w=cirq.LineQubit.range(n);qc=cirq.Circuit()
        for g in d['gates']:
            q=w[g['q']];c=[w[i] for i in g['controls']];k=g['name'];a=g.get('theta',0)
            if k=='swap':op=cirq.SWAP(c[0],q)
            else:
                if k in ('x','cx','mcx'):op=cirq.X(q)
                elif k=='h':op=cirq.H(q)
                elif k in ('p','cp'):op=cirq.ZPowGate(exponent=a/math.pi)(q)
                else:op=getattr(cirq,k)(a)(q)
                if c:op=op.controlled_by(*c)
            qc.append(op)
        sim=qsimcirq.QSimSimulator(qsim_options=qsimcirq.QSimOptions(cpu_threads=1))
        vals=sim.compute_amplitudes(qc,bitstrings=ids,qubit_order=w[::-1])
    else:
        from qulacs import QuantumState,QuantumCircuit
        from qulacs.gate import DenseMatrix
        from qulacs.circuit import QuantumCircuitOptimizer
        t=time.perf_counter();qc=QuantumCircuit(n);state=QuantumState(n)
        for g in d['gates']:
            k=g['name'];q=g['q'];c=g['controls'];a=g.get('theta',0)
            if k=='cx':qc.add_CNOT_gate(c[0],q)
            elif k=='swap':qc.add_SWAP_gate(c[0],q)
            elif k in ('x','h'):getattr(qc,'add_'+k.upper()+'_gate')(q)
            elif k in ('rx','ry','rz'):getattr(qc,'add_'+k.upper()+'_gate')(q,-a)
            else:
                m=[[0,1],[1,0]] if k=='mcx' else [[1,0],[0,np.exp(1j*a)]]
                gate=DenseMatrix(q,np.array(m,complex))
                for control in c:gate.add_control_qubit(control,1)
                qc.add_gate(gate)
        # Light optimizer avoids exponential gate matrices for high-control Grover.
        if max((len(g['controls']) for g in d['gates']),default=0)<=5:
            QuantumCircuitOptimizer().optimize_light(qc)
        qc.update_quantum_state(state);vals=[state.get_amplitude(i) for i in ids]
    print(json.dumps(dict(ms=1000*(time.perf_counter()-t),values=[[z.real,z.imag] for z in vals])))

def trial(engine,doc,path,text_input):
    if engine=='quest': cmd=[os.environ['QUEST_BIN']]
    elif engine=='dsiq': cmd=['node',str(HERE.parent/'global/dsiq.mjs'),str(path)]
    else:cmd=[sys.executable,__file__,'worker',engine,str(path)]
    rss=path.with_suffix('.rss')
    t=time.perf_counter()
    p=subprocess.run(['/usr/bin/time','-f','%M','-o',str(rss),*cmd],input=text_input if engine=='quest' else '',text=True,capture_output=True,timeout=75)
    elapsed=1000*(time.perf_counter()-t)
    if p.returncode:raise RuntimeError((p.stderr or p.stdout)[-900:])
    row=json.loads(p.stdout);row.update(process_ms=elapsed,rss_kib=int(rss.read_text()));return row

def compare(name,n):
    d=build(name,n);encoded=json.dumps(d);rows={k:[] for k in ENGINES};errors={};values={}
    args=[f"{d['n']} {len(d['gates'])} {len(d['indices'])}"]
    for g in d['gates']:args.append(' '.join(map(str,[g['name'],g['q'],g.get('theta',0),len(g['controls']),*g['controls']])))
    data='\n'.join(args+list(map(str,d['indices'])))
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'input.json';path.write_text(encoded)
        for rep in range(REPS):
            for k in ENGINES[rep:]+ENGINES[:rep]:
                if k in errors:continue
                try:
                    row=trial(k,d,path,data);v=np.asarray(row.pop('values'))
                    if v.shape!=(len(d['indices']),2) or not np.isfinite(v).all():raise ValueError('invalid output')
                    values.setdefault(k,[]).append(v[:,0]+1j*v[:,1]);rows[k].append(row)
                except Exception as e:errors[k]=str(e)
    ref=next((v[0] for k in ('quest','aer') if (v:=values.get(k)) and k not in errors),None)
    report={}
    for k,obs in rows.items():
        if k in errors or ref is None:report[k]=dict(error=errors.get(k,'reference unavailable'));continue
        e=max(float(max(abs(v-ref))) for v in values[k])
        mask=abs(ref)>1e-10
        rel=max((float(max(abs((v-ref)[mask]/ref[mask]))) if mask.any() else 0) for v in values[k])
        passed=(e<=5e-4 if k=='qsim' else e<=1e-11 and rel<=1e-7)
        report[k]=dict(samples=obs,ms=statistics.median(o['ms'] for o in obs),process_ms=statistics.median(o['process_ms'] for o in obs),abs_error=e,relative_error=rel,passed=passed)
    return dict(family=name,n=d['n'],gates=len(d['gates']),probes=d['indices'],sha256=hashlib.sha256(encoded.encode()).hexdigest(),engines=report)

if __name__=='__main__':
    if sys.argv[1]=='worker':worker(sys.argv[2],Path(sys.argv[3]));sys.exit()
    name=sys.argv[1];n=int(sys.argv[2]);out=Path('result.json')
    try:r=compare(name,n)
    except Exception as exc:r=dict(family=name,n=n,error=repr(exc))
    r['cpu']=next(s.strip() for s in Path('/proc/cpuinfo').read_text().splitlines() if s.startswith('model name'))
    r['versions']={p:importlib.metadata.version(p) for p in ('mqt.bench','qiskit','qiskit-aer','qsimcirq','qulacs','numpy')}
    out.write_text(json.dumps(r,indent=2))
    print(name,n,{k:(v.get('ms'),v.get('passed'),v.get('error')) for k,v in r.get('engines',{}).items()},r.get('error'),flush=True)
