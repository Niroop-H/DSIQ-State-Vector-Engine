#!/usr/bin/env python3
"""Full fail-closed DSIQ scientific campaign; no indefinite retry or fake pass.
Run from any directory; immutable timestamped evidence directory. External
references are optional dependencies and never replaced by internal oracles.
The original Diamond result counts remain authoritative until qualifying
reference evidence is integrated into the acceptance harness.
"""
import argparse, datetime, hashlib, importlib.util, json, os, pathlib, subprocess, sys, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
def save(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='validation-runs');p.add_argument('--seed',type=int,default=2738912009);p.add_argument('--timeout',type=int,default=1200,help='maximum seconds per job');p.add_argument('--external',action='store_true',help='run named reference tests if installed; never install packages');args=p.parse_args()
    if not 0<=args.seed<=0xffffffff or not 1<=args.timeout<=86400:p.error('invalid seed or timeout')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');out=(pathlib.Path(args.out).resolve()/stamp);out.mkdir(parents=True,exist_ok=False)
    env={**os.environ,'DSIQ_AUDIT_SEED':str(args.seed),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'};jobs=[]
    original=json.loads((ROOT/'docs/diamond-105.json').read_text());assert len(original)==105 and [int(r['id']) for r in original]==list(range(1,106))
    files=[p for d in ['apps/web/public/dsiq','tests','native'] for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts];manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)};manifest['docs/diamond-105.json']=sha(ROOT/'docs/diamond-105.json');save(out/'source-manifest.json',manifest)
    def run(name,cmd,expect=(0,),json_output=False):
        start=time.monotonic();log=out/(name+'.stdout');err=out/(name+'.stderr');status=None;reason=None
        print(f'RUN {name}',flush=True)
        with log.open('wb') as a,err.open('wb') as b:
            try:status=subprocess.run(cmd,cwd=ROOT,env=env,stdout=a,stderr=b,timeout=args.timeout,check=False).returncode
            except (subprocess.TimeoutExpired,OSError) as e:reason=str(e)
        item=dict(name=name,command=[str(x) for x in cmd],exitCode=status,completed=status in expect,elapsedSeconds=time.monotonic()-start,stdoutSHA256=sha(log),stderrSHA256=sha(err),reason=reason)
        if item['completed'] and json_output:
            try:item['result']=json.loads(log.read_text())
            except (ValueError,UnicodeError) as e:item['completed']=False;item['reason']='Invalid JSON: '+str(e)
        jobs.append(item);save(out/'campaign-progress.json',jobs);print(f"{'DONE' if item['completed'] else 'FAIL'} {name}",flush=True);return item
    run('regression',['node','tests/dsiq.test.mjs'])
    run('worker',['node','tests/worker.test.mjs'])
    raw=out/'diamond-results.json';h=run('diamond',['node','--max-old-space-size=3072','tests/diamond.test.mjs',str(raw)],(0,1));report=None
    if h['completed'] and raw.is_file():
        try:
            report=json.loads(raw.read_text());rows=report['results'];assert len(rows)==105 and all(str(a['id'])==str(b['id']) and a['title']==b['title'] and a['requirement']==b['requirement'] for a,b in zip(rows,original))
            counts={s:sum(r['status']==s for r in rows) for s in ('PASS','PARTIAL','FAIL','BLOCKED','NOT_RUN')};assert sum(counts.values())==105 and counts==report['counts'];assert bool(report['releaseEligible'])==(counts['PASS']==105);assert h['exitCode']==(0 if counts['PASS']==105 else 1)
        except (AssertionError,ValueError,KeyError,TypeError) as e:print('Invalid Diamond result:',e,file=sys.stderr);report=None
    for file in ('mps-audit.py','mps-deep-audit.py','mps-random-uncompute.py','sliced-bond-audit.py','v12-audit.test.py'):run(file.removesuffix('.py'),[sys.executable,'-B','tests/'+file],json_output=True)
    for name,dep,cmd in [('Aer','qiskit_aer',[sys.executable,'-B','tests/connected-frame-audit.py','25','aer']),('Stim','stim',[sys.executable,'-B','tests/external-oracle.py','stim']),('quimb','quimb',[sys.executable,'-B','tests/external-oracle.py','quimb'])]:
        if args.external and importlib.util.find_spec(dep):run('reference-'+name,cmd,json_output=True)
        else:jobs.append(dict(name='reference-'+name,status='NOT_RUN',reason='optional external check not enabled or dependency missing'))
    unchanged=all((ROOT/f).is_file() and sha(ROOT/f)==v for f,v in manifest.items());eligible=bool(report and report['releaseEligible'] and unchanged and all(j.get('completed',False) for j in jobs));summary=dict(originalRequirementSHA256=manifest['docs/diamond-105.json'],sourceUnchanged=unchanged,counts=report['counts'] if report else None,releaseEligible=eligible,baselineReportSHA256=sha(raw) if raw.is_file() else None,jobs=jobs,scope='Supplemental results do not override original acceptance statuses; missing external hardware and independent evaluators remain blockers.')
    save(out/'campaign-summary.json',summary);print(json.dumps(dict(evidence=str(out),counts=summary['counts'],releaseEligible=eligible)),flush=True);return 0 if eligible else 1
if __name__=='__main__':sys.exit(main())
