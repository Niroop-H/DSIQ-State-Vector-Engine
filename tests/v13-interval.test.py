#!/usr/bin/env python3
"""Fresh source-scatter oracle comparisons; not Astra's fixtures or answers."""
import json, os, pathlib, random, subprocess, sys, importlib.util, hashlib
import mpmath as mp
ROOT=pathlib.Path(__file__).resolve().parents[1];mp.mp.dps=110
SEED=83491627;rng=random.Random(SEED)
def gate(name,q,controls=(),**kw):return dict(name=name,q=q,controls=list(controls),**kw)
def single(q):
    name=rng.choice(['rx','ry','rz','p','h','t','y','s','sdg','tdg','sx','sy','u'])
    return gate(name,q,**({'theta':rng.uniform(-5,5),'phi':rng.uniform(-5,5),'lambda':rng.uniform(-5,5)} if name=='u' else {'theta':rng.uniform(-5,5)} if name in ('rx','ry','rz','p') else {}))
def controlled(q,c):
    name=rng.choice(['cx','cy','cz','crx','cry','crz','cp','cu','csx'])
    return gate(name,q,[c],**({'theta':rng.uniform(-5,5),'phi':rng.uniform(-5,5),'lambda':rng.uniform(-5,5)} if name=='cu' else {'theta':rng.uniform(-5,5)} if name in ('crx','cry','crz','cp') else {}))
def mat(g):
    name=g['name'];t=mp.mpf(g.get('theta',0));c=mp.cos(t/2);s=mp.sin(t/2);i=mp.j
    if name in ('x','cx'):return [0,1,1,0]
    if name in ('y','cy'):return [0,-i,i,0]
    if name in ('z','cz'):return [1,0,0,-1]
    if name=='h':return [1/mp.sqrt(2)]*3+[-1/mp.sqrt(2)]
    if name in ('s','sdg','t','tdg'):return [1,0,0,{'s':i,'sdg':-i,'t':mp.exp(i*mp.pi/4),'tdg':mp.exp(-i*mp.pi/4)}[name]]
    if name in ('rx','crx'):return [c,-i*s,-i*s,c]
    if name in ('ry','cry'):return [c,-s,s,c]
    if name in ('rz','crz'):return [mp.exp(-i*t/2),0,0,mp.exp(i*t/2)]
    if name in ('p','cp'):return [1,0,0,mp.exp(i*t)]
    if name in ('sx','csx'):return [(1+i)/2,(1-i)/2,(1-i)/2,(1+i)/2]
    if name=='sy':return [(1+i)/2,-(1+i)/2,(1+i)/2,(1+i)/2]
    if name in ('u','cu'):
        p,l=mp.mpf(g['phi']),mp.mpf(g['lambda']);return [c,-s*mp.exp(i*l),s*mp.exp(i*p),c*mp.exp(i*(p+l))]
    raise ValueError(name)
def evolve(a,g):
    q=g['q'];cs=g['controls'];b=[mp.mpc(0) for _ in a];name=g['name']
    if name=='swap':
        c=cs[0]
        for x,v in enumerate(a):b[x^(((1<<q)|(1<<c)) if ((x>>q)^(x>>c))&1 else 0)]=v
    else:
        M=mat(g)
        for x,v in enumerate(a):
            if not all(x>>c&1 for c in cs):b[x]+=v;continue
            for row in range(2):b[(x&~(1<<q))|(row<<q)]+=M[2*row+(x>>q&1)]*v
    return b
def obs(a,p):
    total=mp.mpc(0)
    for x,v in enumerate(a):
        y=x;k=mp.mpc(1)
        for q,c in enumerate(reversed(p)):
            if c in 'XY':y^=1<<q
            if c in 'YZ' and x>>q&1:k=-k
            if c=='Y':k*=mp.j
        total+=mp.conj(a[y])*k*v
    return mp.re(total)
CASES=[]
for t in range(24):
    n=6+(t%2);w=list(range(n));rng.shuffle(w);gs=[]
    if t<12:
        groups=[w[:2],w[2:4],w[4:]]
        # Interleaved local noncommuting gates with exactly-once bridges,
        # reversed physical ordering and local SWAPs; no circuit template match.
        for layer in range(3):
            for group in groups:
                gs += [single(q) for q in group]
                for j in range(len(group)-1):gs.append(controlled(group[j+1],group[j]))
                if layer==1:gs.append(gate('swap',group[-1],[group[0]]))
            if layer<2:
                a,b=groups[layer],groups[layer+1];gs.append(controlled(rng.choice(b),rng.choice(a)))
        mode='bridge'
    else:
        for layer in range(3):
            gs += [single(q) for q in w]
            a,b=rng.sample(w,2);gs.append(controlled(a,b));a,b=rng.sample(w,2);gs.append(gate('swap',a,[b]))
        mode='product'
    # All basis coefficients and randomly chosen Pauli strings at two prefixes.
    checkpoints=[len(gs)//2,len(gs)];queries=[]
    for prefix in checkpoints:
        queries.append(dict(id=f'n-{prefix}',kind='norm',prefix=prefix))
        for x in range(2**n):queries.append(dict(id=f'a-{prefix}-{x}',kind='amplitude',prefix=prefix,bits=format(x,f'0{n}b')))
        for j in range(8):queries.append(dict(id=f'p-{prefix}-{j}',kind='pauli',prefix=prefix,pauli=''.join(rng.choices('IXYZ',k=n))))
    CASES.append(dict(n=n,gates=gs,queries=queries,mode=mode))
runner='''import fs from 'node:fs';import {BridgeFactor} from './apps/web/public/dsiq/bridge-factor.mjs';import {IntervalProduct} from './apps/web/public/dsiq/interval-product.mjs';const cs=JSON.parse(fs.readFileSync(0,'utf8'));const all=[];for(const c of cs){const d=c.mode==='bridge'?new BridgeFactor(c.n,c.gates):new IntervalProduct(c.n);const out=[];for(let i=0;i<c.gates.length;i++){d.apply(c.gates[i]);for(const q of c.queries.filter(q=>q.prefix===i+1)){out.push({id:q.id,value:q.kind==='norm'?d.norm():q.kind==='amplitude'?d.amplitude(q.bits):d.expectation(q.pauli)})}}all.push({out,stats:d.stats()})}console.log(JSON.stringify(all));'''
p=subprocess.run(['node','--input-type=module','-e',runner],input=json.dumps(CASES),text=True,capture_output=True,cwd=ROOT,timeout=120);assert p.returncode==0,p.stderr
out=json.loads(p.stdout);assert len(out)==len(CASES);counts={'amplitude':0,'pauli':0,'norm':0};maxerr=mp.mpf(0);maxbound=0;maxrelative=0;maxblock=0;maxterms=0
for c,r in zip(CASES,out):
    got={q['id']:q['value'] for q in r['out']};assert len(got)==len(c['queries']);a=[mp.mpc(int(x==0)) for x in range(2**c['n'])]
    for i,g in enumerate(c['gates'],1):
        a=evolve(a,g)
        for q in c['queries']:
            if q['prefix']!=i:continue
            kind=q['kind'];expected=a[int(q['bits'],2)] if kind=='amplitude' else obs(a,q['pauli']) if kind=='pauli' else mp.fsum(abs(z)**2 for z in a)
            v=got[q['id']];err=abs(mp.mpc(v['real'],v['imag'])-expected);bound=mp.mpf(v['absoluteErrorBound']);assert err<=bound+mp.mpf('1e-102'),(c['mode'],q,err,bound);assert err<mp.mpf('1e-13');maxerr=max(maxerr,err);maxbound=max(maxbound,float(bound));counts[kind]+=1
            if kind=='amplitude' and abs(expected)>mp.mpf('1e-95'):
                rel=err/abs(expected);assert rel<mp.mpf('1e-9');maxrelative=max(maxrelative,float(rel))
    maxblock=max(maxblock,r['stats'].get('maxBlockWidth',0));maxterms=max(maxterms,r['stats'].get('peakTerms',0))
# Actual abrupt termination: read the flushed prefix-zero query from a real
# worker and kill it; recover journal in the parent, never mark it completed.
spec=importlib.util.spec_from_file_location('audit',ROOT/'native/scientific-audit.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
n=50;gs=[gate('h',q) for q in range(n)]+[gate('cp',q,[c],theta=.321) for q in range(n) for c in range(q)];req=dict(n=n,gates=gs,queries=[dict(id='early',kind='amplitude',bits='0'*n,prefix=0),dict(id='late',kind='norm',prefix=len(gs))],method='certified-contraction',requireCertificate=True,checkpointEvery=100000,maxBytes=268435456,maxWork=250000000);raw=json.dumps(req).encode();proc=subprocess.Popen(['node',str(ROOT/'native/scientific-run.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'DSIQ_STREAM_AUDIT':'1'});lines=[]
try:
    proc.stdin.write(raw);proc.stdin.close()
    while True:
        line=proc.stderr.readline()
        if not line:raise AssertionError('worker exited before journal output')
        lines.append(line)
        if line.startswith(b'DSIQ-AUDIT ') and json.loads(line[len(b'DSIQ-AUDIT '):]).get('kind')=='output':break
    proc.kill();proc.wait(timeout=10);lines.append(proc.stderr.read());report,_,journal=audit.recover_journal(raw,b''.join(lines),None,'Deliberate test SIGKILL');assert proc.returncode<0 and report['status']=='FAILED' and report['recoveredFromJournal'] and report['completedPrefix']==0 and report['outputs'][0]['id']=='early'
finally:
    if proc.poll() is None:proc.kill();proc.wait()
print(json.dumps(dict(seed=SEED,freshCircuits=len(CASES),denseOracleDecimalDigits=110,amplitudeComparisons=counts['amplitude'],pauliComparisons=counts['pauli'],normComparisons=counts['norm'],maxAbsoluteError=float(maxerr),maxRelativeAmplitudeError=maxrelative,maxAbsoluteBound=maxbound,maxBlockWidth=maxblock,maxProductTerms=maxterms,forcedKillExit=proc.returncode,journalRecordsRecovered=len(journal),freshFixtureSHA256=hashlib.sha256(json.dumps(CASES,sort_keys=True).encode()).hexdigest()),indent=2))
