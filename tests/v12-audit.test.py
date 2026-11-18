#!/usr/bin/env python3
"""Targeted #102/#103 tests: real certified queries + fail-closed reporting."""
import json, pathlib, subprocess, sys, math, random
import mpmath as mp
ROOT=pathlib.Path(__file__).resolve().parents[1];mp.mp.dps=100

def run(req,expected=True):
    p=subprocess.run([sys.executable,'-B',str(ROOT/'native/scientific-audit.py'),'--timeout','120'],input=json.dumps(req),text=True,capture_output=True,timeout=135);r=json.loads(p.stdout);assert (p.returncode==0)==expected,(r.get('error'),p.stderr);return r

def check_report(r,req):
    w=r['workerReport'];assert w['status']=='COMPLETED' and w['completedPrefix']==len(req['gates']);e=w['events'];assert [x['sequence'] for x in e]==list(range(len(e)));cp=[x for x in e if x['kind']=='checkpoint'];assert [x['prefix'] for x in cp]==list(range(len(req['gates'])+1));assert all(x['rssBytes']>0 and x['peakRssKiB']>0 and x['cpuMicros']['user']>=0 and x['stats']['gates']==x['prefix'] for x in cp)
    for x in cp:
        a=x['norm'];assert mp.fabs(mp.mpf(a['real'])-1)<=mp.mpf(a['absoluteErrorBound'])
    assert len(w['outputs'])==len(req['queries']);assert all(math.isfinite(q['value']['absoluteErrorBound']) and q['value']['absoluteErrorBound']>=0 for q in w['outputs']);assert r['childPeakRssKiB']>0
    ctr=r['cpuCycles'];assert ctr['value'] is not None or ctr['unavailableReason'];assert not r['gpu']['used'] and r['gpu']['cycles'] is None
    return w,cp

def gate(name,q,c=(),**kwargs):return dict(name=name,q=q,controls=list(c),**kwargs)
n=100;gs=[gate('h',0)]+[gate('cx',i,[i-1]) for i in range(1,n)]+[gate('rz',i,theta=(i-40)/137) for i in range(n)]
qs=[dict(id='zero',kind='amplitude',bits='0'*n,prefix=len(gs)),dict(id='one',kind='amplitude',bits='1'*n,prefix=len(gs)),dict(id='XX',kind='pauli',pauli='X'*n,prefix=len(gs)),dict(id='YY',kind='pauli',pauli='Y'*n,prefix=len(gs)),dict(id='middle',kind='amplitude',bits='0'*n,prefix=n),dict(id='before',kind='norm',prefix=0),dict(id='end',kind='norm',prefix=len(gs))]
req=dict(n=n,gates=gs,queries=qs,method='certified-auto',requireCertificate=True,checkpointEvery=1,maxBytes=67108864,maxWork=100000000);out=run(req);w,cp=check_report(out,req);assert cp[-1]['stats']['mode']=='certified-contraction';phase=sum(mp.mpf(g['theta']) for g in gs[n:]);expected={'zero':mp.exp(-mp.j*phase/2)/mp.sqrt(2),'one':mp.exp(mp.j*phase/2)/mp.sqrt(2),'XX':mp.cos(phase),'YY':mp.cos(phase),'middle':1/mp.sqrt(2),'before':1,'end':1};maxerr=0;maxratio=0
for q in w['outputs']:
    a=q['value'];err=abs(mp.mpc(a['real'],a.get('imag',0))-expected[q['id']]);b=mp.mpf(a['absoluteErrorBound']);assert err<=b,(q['id'],err,b);maxerr=max(maxerr,float(err));maxratio=max(maxratio,float(err/b))
rng=random.Random(126193);cases=[];checkpoints=len(cp);modes={cp[-1]['stats']['mode']};bounded_queries=len(qs);bounds=[q['value']['absoluteErrorBound'] for q in w['outputs']]
for case in range(8):
    n=4;g=[]
    for j in range(18):
        q=rng.randrange(n);t=rng.uniform(-4,4);g.append(gate(rng.choice(['rx','ry','rz']),q,theta=t))
        if j%3==0:g.append(gate('cx',(q+1)%n,[q]))
    g += [gate('u',1,theta=.723,phi=-.33,**{'lambda':.23}),gate('t',3),gate('y',2),gate('swap',0,[3])]
    qs=[dict(id=f'a{x}',kind='amplitude',bits=format(x,'04b'),prefix=len(g)) for x in range(16)]+[dict(id=f'p{i}',kind='pauli',pauli=''.join(rng.choice('IXYZ') for _ in range(n)),prefix=len(g)) for i in range(5)]
    req=dict(n=n,gates=g,queries=qs,method='certified-factor' if case%2==0 else 'certified-contraction',requireCertificate=True,checkpointEvery=1);r=run(req);w,cp=check_report(r,req);checkpoints+=len(cp);modes.add(cp[-1]['stats']['mode']);by={x['id']:x['value'] for x in w['outputs']};cases.append(dict(n=n,gates=g,amps=[by[f'a{x}'] for x in range(16)],observables=[[q['pauli'],by[q['id']]] for q in qs if q['kind']=='pauli']));bounded_queries+=len(qs);bounds.extend(q['value']['absoluteErrorBound'] for q in w['outputs'])
p=subprocess.run([sys.executable,'-B',str(ROOT/'tests/precision-reference.py')],input=json.dumps(dict(kind='certificate',cases=cases)),capture_output=True,text=True,timeout=120);assert p.returncode==0,p.stderr;refs=json.loads(p.stdout);amp=sum(r['amplitudes'] for r in refs);obs=sum(r['observables'] for r in refs);maxerr=max(maxerr,*[r['maxObservedError'] for r in refs]);maxratio=max(maxratio,*[r['maxBoundFraction'] for r in refs]);
base=dict(n=2,gates=[gate('h',0)],queries=[dict(id='q',kind='amplitude',bits='00',prefix=1)],method='certified-auto',requireCertificate=True)
for bad in [dict(base,method='adaptive'),dict(base,gates=[gate('rx',0,theta=1e7)]),dict(base,queries=base['queries']*2),dict(base,queries=[dict(base['queries'][0],bits='zz')]),dict(base,gates=[gate('bogus',0)]),dict(base,n=100,gates=[gate('h',0)]+[gate('cx',i,[i-1]) for i in range(1,100)],queries=[dict(id='q',kind='amplitude',bits='0'*100,prefix=100)],maxBytes=256,method='certified-contraction')]:
    failure=run(bad,False);assert not (failure.get('workerReport') or {}).get('outputs')
print(json.dumps({'scope':'strict headless CPU unitary query API; certified gate domain only; not general browser or hardware certification','connected100':{'gates':len(gs),'checkpoints':len(gs)+1,'queries':len(expected),'peakRssKiB':out['workerReport']['metrics']['peakRssKiB'],'cpuCycles':out['cpuCycles'],'gpu':out['gpu']},'denseReferenceAmplitudeComparisons':amp,'denseReferenceObservableComparisons':obs,'allCertifiedQueries':bounded_queries,'normCheckpoints':checkpoints,'maxObservedError':maxerr,'maxBoundFraction':maxratio,'maxReportedBound':max(bounds),'rejectedInvalidOrUnaffordableRequests':6,'testedModes':sorted(modes)},indent=2))
