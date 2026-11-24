"""Paired end-to-end CPU full-output benchmark. No retrospective engine selection."""
import hashlib,json,math,os,random,statistics,subprocess,sys,tempfile,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
def fixture(n,kind,seed):
    rng=random.Random(seed);g=[]
    def add(name,q,controls=(),**kw):g.append(dict(name=name,q=q,controls=list(controls),**kw))
    if kind=='qft':
        for q in range(n):add('ry',q,theta=rng.uniform(-2,2))
        for q in reversed(range(n)):
            add('h',q)
            for c in reversed(range(q)):add('cp',q,[c],theta=math.pi/2**(q-c))
        for q in range(n//2):add('swap',n-1-q,[q])
    else:
        for layer in range(10):
            for q in range(n):
                add('ry',q,theta=rng.uniform(-math.pi,math.pi));add('rz',q,theta=rng.uniform(-math.pi,math.pi))
            wires=list(range(n));rng.shuffle(wires)
            for c,q in zip(wires[::2],wires[1::2]):add('cx',q,[c])
    return dict(n=n,gates=g,indices=list(range(1<<n)))
def execute(engine,inp):
    cmd=[sys.executable,str(HERE/'run.py'),'aer',str(inp)] if engine=='aer' else ['node',str(HERE/'dsiq.mjs'),str(inp)]
    start=time.monotonic()
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
        wall=1000*(time.monotonic()-start)
        if p.returncode:return dict(status='ERROR',wall_ms=wall,exit=p.returncode,error=p.stderr[-500:]),None
        out=json.loads(p.stdout);a=np.asarray(out['values'],float)
        if a.ndim!=2 or a.shape[1]!=2 or not np.isfinite(a).all():raise ValueError('invalid values')
        return dict(status='RETURNED',wall_ms=wall,adapter_ms=out['ms']),a[:,0]+1j*a[:,1]
    except subprocess.TimeoutExpired:return dict(status='TIMEOUT',wall_ms=1000*(time.monotonic()-start)),None
    except Exception as e:return dict(status='ERROR',error=repr(e)),None
def main():
    report=dict(scope='project-run FP64 full output, end-to-end wall time; no best-of selection',absolute_tolerance=1e-13,relative_tolerance=1e-9,repetitions=30,cases=[])
    for n,kind in ((8,'random'),(10,'random'),(12,'random'),(10,'qft')):
        req=fixture(n,kind,261124);rows=[]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'input.json';p.write_text(json.dumps(req,sort_keys=True))
            for rep in range(30):
                stats={};values={}
                for eng in (('aer','dsiq_js') if rep%2==0 else ('dsiq_js','aer')):
                    stats[eng],values[eng]=execute(eng,p)
                a,b=values['aer'],values['dsiq_js']
                if a is not None and b is not None and len(a)==len(b)==1<<n:
                    delta=abs(a-b);nz=abs(a)>0
                    ae=float(max(delta));re=float(max(delta[nz]/abs(a[nz]))) if nz.any() else 0.
                    passed=bool(ae<=1e-13 and re<=1e-9)
                    rows.append(dict(rep=rep,engines=stats,passed=passed,max_abs=ae,max_relative=re))
                else:rows.append(dict(rep=rep,engines=stats,passed=False))
            med={}
            for eng in ('aer','dsiq_js'):
                vals=[r['engines'][eng]['wall_ms'] for r in rows if r['passed']]
                med[eng]=dict(completed_accuracy_pairs=len(vals),median_ms=statistics.median(vals) if vals else None,iqr_ms=statistics.quantiles(vals,n=4)[2]-statistics.quantiles(vals,n=4)[0] if len(vals)>1 else None)
            report['cases'].append(dict(width=n,family=kind,seed=261124,input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),summary=med,rows=rows))
            Path('paired-full-output.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return int(any(not r['passed'] for c in report['cases'] for r in c['rows']))
if __name__=='__main__':sys.exit(main())
