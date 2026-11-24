"""Bounded forward-prefix diagnosis of original Diamond-70 fixture; no promotion."""
import hashlib,json,os,resource,runpy,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/'tests/mps-random-uncompute.py'))
gates=fixture['make'](100,8377)
def limit():
    resource.setrlimit(resource.RLIMIT_AS,(2**31,2**31))
def run(depth,mib,work,plan):
    req=dict(n=100,gates=gates[:150*depth],queries=['0'*100],max_bytes=mib*2**20,max_work=work,plan_only=plan)
    start=time.monotonic()
    row=dict(depth=depth,budget_mib=mib,work_budget=work,plan_only=plan)
    try:
        p=subprocess.run([sys.executable,str(ROOT/'native/mps_exact.py')],input=json.dumps(req),text=True,capture_output=True,timeout=30,preexec_fn=limit,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
        out=json.loads(p.stdout)
        row.update(exit_code=p.returncode,status='PLAN_ADMITTED' if p.returncode==0 and plan else 'QUERY_RETURNED' if p.returncode==0 else 'BOUNDARY' if p.returncode==2 and 'error' in out else 'ERROR',output=out)
    except subprocess.TimeoutExpired:row.update(status='TIMEOUT')
    except Exception as e:row.update(status='ERROR',error=repr(e))
    row['wall_seconds']=time.monotonic()-start
    return row
rows=[run(d,m,w,True) for d in (1,2,3,4,10,100) for m,w in ((16,2**28),(64,2**32),(256,2**36))]
rows += [run(d,64,2**32,False) for d in (1,2,3)]
report=dict(scope='MPS diagnostic only; original Diamond-70 criteria unchanged; returned midpoint queries not independently verified in this sweep',seed=8377,forward_gate_count=len(gates),forward_sha256=hashlib.sha256(json.dumps(gates,sort_keys=True).encode()).hexdigest(),rows=rows)
Path('diamond70-sweep.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps(report,indent=2,allow_nan=False))
sys.exit(any(r['status']=='ERROR' for r in rows))
