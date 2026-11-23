"""Linux CPU selected-amplitude benchmark, fresh process for each observation."""
import hashlib, importlib.metadata, json, os, pathlib, platform, random
import statistics, subprocess, sys, tempfile, time, urllib.request
from qiskit import qasm2, QuantumCircuit
from qiskit_aer import AerSimulator
import numpy as np

HERE=pathlib.Path(__file__).resolve().parent
REV='357b942396d5c2b7cbc1c229c585a6ef5ccaebac'
CASES=('small/ising_n10','medium/multiplier_n15','medium/qft_n18','medium/bv_n19','medium/cat_state_n22')

def baseline(doc, probes):
    circuit=QuantumCircuit(doc['n'])
    for g in doc['gates']:
        args=[g['theta']] if 'theta' in g else []
        getattr(circuit,g['name'])(*args,*g['controls'],g['q'])
    if probes is None: circuit.save_statevector()
    else: circuit.save_amplitudes(probes)
    sim=AerSimulator(method='statevector',precision='double',max_parallel_threads=1,
                     enable_truncation=False,zero_threshold=0)
    start=time.perf_counter()
    result=sim.run(circuit,shots=1).result()
    if not result.success: raise RuntimeError(result.status)
    if probes is None:return np.asarray(result.data(0)['statevector'])
    values=[[z.real,z.imag] for z in result.data(0)['amplitudes']]
    return dict(ms=1000*(time.perf_counter()-start),values=values)

def prepare(path):
    name=path.split('/')[-1]
    url=f'https://raw.githubusercontent.com/pnnl/QASMBench/{REV}/{path}/{name}.qasm'
    raw=urllib.request.urlopen(url,timeout=30).read()
    circuit=qasm2.loads(raw.decode(),custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    clean=circuit.remove_final_measurements(inplace=False)
    gates=[]
    for inst in clean.data:
        op=inst.operation
        if op.name=='barrier':continue
        if op.name not in ('h','x','z','s','t','cx','ccx','rz','ry','rx','u1','p','swap','cz','id'):
            raise ValueError(f'Unsupported operation {op.name}')
        wires=[clean.find_bit(q).index for q in inst.qubits]
        g=dict(name={'u1':'p'}.get(op.name,op.name),controls=wires[:-1],q=wires[-1])
        if op.name=='id':continue
        if op.params:g['theta']=float(op.params[0])
        gates.append(g)
    n=clean.num_qubits
    doc=dict(n=n,gates=gates)
    # Include a populated output on sparse circuits; setup excluded for both engines.
    vector=baseline(doc,None)
    indices=sorted({0,2**n-1,int(np.argmax(abs(vector))),*random.Random(20261123).sample(range(2**n),64)})
    doc['indices']=indices
    return doc,hashlib.sha256(raw).hexdigest()

def compare(path,tmp):
    doc,digest=prepare(path)
    inp=tmp/'input.json';inp.write_text(json.dumps(doc))
    samples={'aer':[],'dsiq':[]}
    for rep in range(5):
        outputs={}
        for engine in (('aer','dsiq') if rep%2==0 else ('dsiq','aer')):
            cmd=[sys.executable,__file__,'aer',str(inp)] if engine=='aer' else ['node',str(HERE/'dsiq.mjs'),str(inp)]
            rss=tmp/'rss.txt';start=time.perf_counter()
            run=subprocess.run(['/usr/bin/time','-f','%M','-o',str(rss),*cmd],capture_output=True,text=True,timeout=180)
            wall=1000*(time.perf_counter()-start)
            if run.returncode:raise RuntimeError(run.stderr[-1500:])
            row=json.loads(run.stdout);values=np.asarray(row.pop('values'),dtype=float)
            if values.shape!=(len(doc['indices']),2) or not np.isfinite(values).all():raise ValueError('Incomplete output')
            outputs[engine]=values[:,0]+1j*values[:,1]
            samples[engine].append(dict(**row,process_ms=wall,peak_rss_kib=int(rss.read_text())))
        err=abs(outputs['aer']-outputs['dsiq']);mask=abs(outputs['aer'])>1e-14
        absolute=float(max(err));relative=float(max(err[mask]/abs(outputs['aer'][mask])))
        if absolute>1e-12 or relative>1e-9:raise ValueError(f'Accuracy failure: {absolute}, {relative}')
        samples['dsiq'][-1].update(max_abs_error=absolute,max_rel_error=relative)
    return dict(case=path,sha256=digest,qubits=doc['n'],gates=len(doc['gates']),indices=doc['indices'],samples=samples,
                median_ms={k:statistics.median(x['ms'] for x in v) for k,v in samples.items()},
                median_process_ms={k:statistics.median(x['process_ms'] for x in v) for k,v in samples.items()})

if __name__=='__main__' and sys.argv[1:] and sys.argv[1]=='aer':
    d=json.loads(pathlib.Path(sys.argv[2]).read_text());print(json.dumps(baseline(d,d['indices'])))
elif __name__=='__main__':
    report=dict(corpus_commit=REV,engine_commit=os.environ.get('GITHUB_SHA'),cpu=platform.machine(),
                cpuinfo=next((l.strip() for l in pathlib.Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name')),'unknown'),
                node=subprocess.check_output(['node','-v'],text=True).strip(),python=sys.version,
                packages={p:importlib.metadata.version(p) for p in ('qiskit','qiskit-aer','numpy')},cases=[])
    for path in CASES:
        with tempfile.TemporaryDirectory() as td:
            try: row=compare(path,pathlib.Path(td))
            except Exception as e:row=dict(case=path,error=str(e))
        report['cases'].append(row)
        pathlib.Path('global-results.json').write_text(json.dumps(report,indent=2,allow_nan=False))
        print('RESULT',path,row.get('median_ms'),row.get('median_process_ms'),row.get('error'),flush=True)
    sys.exit(any('error' in r for r in report['cases']))
