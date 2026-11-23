"""Two-excitation qubit benchmark using QuSpin sector basis and ladder operators."""
import itertools,json,math,os,resource,statistics,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'benchmarks/global'))
from excitation_check import fixture,particle_oracle

def quspin(d):
    from quspin.basis import spin_basis_general
    t=time.perf_counter();n=d['n'];basis=spin_basis_general(n,Nup=2,pauli=0)
    pairs=list(itertools.combinations(range(n),2))
    ids=np.array([basis.index(format((1<<i)|(1<<j),f'0{n}b')) for i,j in pairs])
    loc={pair:idx for pair,idx in zip(pairs,ids)}
    occ=[np.array([idx for pair,idx in zip(pairs,ids) if q in pair]) for q in range(n)]
    v=np.zeros(basis.Ns,complex);v[loc[0,n//2]]=1
    hopping={};phase=1+0j
    for g in d['gates'][2:]:
        q=g['q'];k=g['name'];a=g.get('theta',0)
        if k in ('rz','p'):
            if k=='rz':phase*=np.exp(-0.5j*a)
            v[occ[q]]*=np.exp(1j*a)
            continue
        c=g['controls'][0];both=loc[tuple(sorted((c,q)))]
        if k in ('cz','cp','fsim'):
            v[both]*=-1 if k=='cz' else np.exp(1j*(a if k=='cp' else -g['phi']))
        if k in ('swap','fsim'):
            if (c,q) not in hopping:
                me,row,col=basis.Op('+-',[n-1-c,n-1-q],1.,np.float64)
                keep=me!=0
                if not np.all(me[keep]==1):raise ValueError('unexpected spin ladder normalization')
                hopping[c,q]=row[keep],col[keep]
            i,j=hopping[c,q];x,y=v[i],v[j]
            if k=='swap':v[i],v[j]=y,x
            else:
                cs,mix=math.cos(a),-1j*math.sin(a)
                v[i],v[j]=cs*x+mix*y,mix*x+cs*y
    out=v[ids]*phase
    return dict(amplitudes=[[z.real,z.imag] for z in out],elapsed_seconds=time.perf_counter()-t,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)

def compare(n,seed):
    gates=fixture(n,seed);pairs=list(itertools.combinations(range(n),2))
    doc=dict(n=n,gates=gates,queries=[format((1<<i)|(1<<j),f'0{n}b') for i,j in pairs])
    table=particle_oracle(n,gates);ref=np.array([table[i,j] for i,j in pairs])
    reports={k:[] for k in ('dsiq','quspin')};payload=json.dumps(doc)
    for rep in range(3):
        for k in (('dsiq','quspin') if rep%2==0 else ('quspin','dsiq')):
            if isinstance(reports[k],dict):continue
            try:
                cmd=[sys.executable,str(ROOT/'native/excitation_statevector.py')] if k=='dsiq' else [sys.executable,__file__,'worker']
                t=time.perf_counter();p=subprocess.run(cmd,input=payload,text=True,capture_output=True,timeout=120)
                wall=time.perf_counter()-t
                if p.returncode:raise RuntimeError((p.stderr or p.stdout)[-900:])
                r=json.loads(p.stdout);v=np.array(r['amplitudes']);delta=abs(v[:,0]+1j*v[:,1]-ref)
                mask=abs(ref)>1e-14
                reports[k].append(dict(ms=1000*r['elapsed_seconds'],process_ms=1000*wall,rss_kib=r['peak_rss_kib'],abs_error=float(max(delta)),relative_error=float(max(delta[mask]/abs(ref[mask])))))
            except Exception as exc:reports[k]=dict(error=str(exc))
    for k,v in reports.items():
        if isinstance(v,list):reports[k]=dict(samples=v,ms=statistics.median(x['ms'] for x in v),process_ms=statistics.median(x['process_ms'] for x in v),passed=all(x['abs_error']<1e-13 and x['relative_error']<1e-9 for x in v))
    return dict(n=n,seed=seed,coefficients=len(pairs),engines=reports)

if __name__=='__main__':
    if sys.argv[1]=='worker':print(json.dumps(quspin(json.load(sys.stdin))));sys.exit()
    n=int(sys.argv[1]);r=compare(n,int(sys.argv[2]))
    import importlib.metadata
    r['versions']={p:importlib.metadata.version(p) for p in ('quspin','numpy')}
    r['cpu']=next(s.strip() for s in Path('/proc/cpuinfo').read_text().splitlines() if s.startswith('model name'))
    Path('result.json').write_text(json.dumps(r,indent=2));print(r)
