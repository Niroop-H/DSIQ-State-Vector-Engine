"""Fresh project-run dense oracle and operational checks; not third-party validation."""
import hashlib, json, math, os, random, subprocess, sys, time, resource
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
ENGINE=ROOT/'native/mps_exact.py'
def limit():
    resource.setrlimit(resource.RLIMIT_AS,(2**31,2**31))
def run(req):
    start=time.monotonic()
    p=subprocess.run([sys.executable,str(ENGINE)],input=json.dumps(req),text=True,capture_output=True,timeout=60,preexec_fn=limit,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
    return p.returncode,json.loads(p.stdout),time.monotonic()-start
def oracle(n,gates):
    v=np.zeros(1<<n,complex);v[0]=1
    idx=np.arange(len(v))
    for g in gates:
        q=g['q']; mask=1<<q; name=g['name']
        if name=='cz':
            v[((idx&mask)!=0)&((idx&(1<<g['controls'][0]))!=0)]*=-1
        elif name=='p':
            v[(idx&mask)!=0]*=np.exp(1j*g['theta'])
        else:
            lo=idx[(idx&mask)==0];hi=lo|mask
            a,b=v[lo].copy(),v[hi].copy()
            c,s=math.cos(g['theta']/2),math.sin(g['theta']/2)
            v[lo]=c*a-s*b;v[hi]=s*a+c*b
    return v
def fixture(n,seed):
    rng=random.Random(seed);g=[]
    for layer in range(4):
        for q in range(n):
            for name in ('ry','p'):
                g.append(dict(name=name,q=q,controls=[],theta=rng.uniform(-2,2)))
        for q in range(layer%2,n-1,2):
            g.append(dict(name='cz',q=q+1,controls=[q]))
    return g
def main():
    rows=[]
    def check(label,fn):
        try: rows.append(dict(case=label,**fn()))
        except Exception as e: rows.append(dict(case=label,passed=False,error=repr(e)))
    def numerical(n,seed):
        gates=fixture(n,seed);req=dict(n=n,gates=gates,queries=[format(i,f'0{n}b') for i in range(1<<n)])
        code,out,elapsed=run(req)
        if code: raise RuntimeError(out)
        expected=oracle(n,gates)
        actual=np.array([complex(a['real'],a['imag']) for a in out['amplitudes']])
        delta=abs(actual-expected);nz=abs(expected)>0
        relative=float(max(delta[nz]/abs(expected[nz])))
        return dict(passed=bool(max(delta)<=1e-13 and relative<=1e-9 and abs(out['norm']-1)<=1e-12),width=n,seed=seed,amplitudes=len(actual),max_abs=float(max(delta)),max_relative=relative,norm=out['norm'],seconds=elapsed,peak_rss_kib=out['processPeakRSSKiB'],input_sha256=hashlib.sha256(json.dumps(req,sort_keys=True).encode()).hexdigest())
    for n in (4,6,8,10):
        for seed in (261124,261125,261126):check(f'dense-{n}-{seed}',lambda n=n,seed=seed:numerical(n,seed))
    def repeat():
        req=dict(n=8,gates=fixture(8,261127),queries=['00000000','11111111'],shots=128,seed=42)
        runs=[run(req) for _ in range(3)]
        fields=['amplitudes','observables','norm','samples']
        values=[{k:o[k] for k in fields} for c,o,t in runs if c==0]
        return dict(passed=len(values)==3 and values[0]==values[1]==values[2],runs=len(values))
    check('cold-process-repeat',repeat)
    for name,req in [('invalid-wire',dict(n=8,gates=[dict(name='x',q=8,controls=[])])),('unsupported',dict(n=8,gates=[dict(name='unsupported',q=0,controls=[])])),('budget',dict(n=8,gates=fixture(8,1),max_work=1))]:
        def rejection(req=req):
            c,o,t=run(req);return dict(passed=c==2 and 'error' in o and 'amplitudes' not in o,exit_code=c,response=o,seconds=t)
        check(name,rejection)
    report=dict(scope='project-run fresh tests; no independent evaluator',numpy=np.__version__,python=sys.version,cases=rows)
    Path('supplemental-validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2,allow_nan=False))
    return int(not all(r['passed'] for r in rows))
if __name__=='__main__':sys.exit(main())
