#!/usr/bin/env python3
"""Fresh source-scatter oracle comparisons; not Astra's fixtures or answers."""
import json, os, pathlib, random, subprocess, sys, importlib.util, hashlib
import mpmath as mp
ROOT=pathlib.Path(__file__).resolve().parents[1];mp.mp.dps=110
SEED=718316554;rng=random.Random(SEED)
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
for t in range(20):
    n=5+t%3;gs=[];w=list(range(n));rng.shuffle(w)
    for layer in range(5):
        gs.extend(single(q) for q in w)
        for j in range(n):
            a,b=rng.sample(w,2);gs.append(controlled(a,b))
        gs.append(gate('swap',w[0],[w[-1]]))
    queries=[]
    for prefix in [1,len(gs)//2,len(gs)]:
        queries.append(dict(id=f'n-{prefix}',kind='norm',prefix=prefix))
        for x in range(2**n):queries.append(dict(id=f'a-{prefix}-{x}',kind='amplitude',prefix=prefix,bits=format(x,f'0{n}b')))
        for j in range(8):queries.append(dict(id=f'p-{prefix}-{j}',kind='pauli',prefix=prefix,pauli=''.join(rng.choices('IXYZ',k=n))))
    CASES.append(dict(n=n,gates=gs,queries=queries))
runner="""import fs from 'node:fs';import {IntervalSparse,SparseBoundary} from './apps/web/public/dsiq/interval-sparse.mjs';const cases=JSON.parse(fs.readFileSync(0,'utf8'));const all=[];for(const c of cases){const d=new IntervalSparse(c.n,c.gates,{maxBytes:67108864,maxWork:50000000,maxNodes:32768});const out=[];for(let i=0;i<c.gates.length;i++){d.apply(c.gates[i]);for(const q of c.queries.filter(q=>q.prefix===i+1)){out.push({id:q.id,value:q.kind==='norm'?d.norm():q.kind==='amplitude'?d.amplitude(q.bits):d.expectation(q.pauli)})}}all.push({out,stats:d.stats()})}let boundary=false;try{new IntervalSparse(30,Array.from({length:30},(_,q)=>({name:'h',q,controls:[]})),{maxBytes:67108864,maxWork:50000000,maxNodes:32768})}catch(e){boundary=e instanceof SparseBoundary}if(!boundary)throw Error('Missing support refusal');console.log(JSON.stringify(all));"""
p=subprocess.run(['node','--input-type=module','-e',runner],input=json.dumps(CASES),text=True,capture_output=True,cwd=ROOT,timeout=120);assert p.returncode==0,p.stderr
out=json.loads(p.stdout);counts={'amplitude':0,'pauli':0,'norm':0};maxerr=mp.mpf(0);maxbound=0;maxrelative=0;relcount=0
for c,r in zip(CASES,out):
    got={q['id']:q['value'] for q in r['out']};assert len(got)==len(c['queries']);a=[mp.mpc(int(x==0)) for x in range(2**c['n'])]
    for i,g in enumerate(c['gates'],1):
        a=evolve(a,g)
        for q in c['queries']:
            if q['prefix']!=i:continue
            kind=q['kind'];expected=a[int(q['bits'],2)] if kind=='amplitude' else obs(a,q['pauli']) if kind=='pauli' else mp.fsum(abs(z)**2 for z in a)
            v=got[q['id']];err=abs(mp.mpc(v['real'],v['imag'])-expected);bound=mp.mpf(v['absoluteErrorBound']);assert err<=bound+mp.mpf('1e-102'),(q,err,bound);assert err<mp.mpf('1e-13');maxerr=max(maxerr,err);maxbound=max(maxbound,float(bound));counts[kind]+=1
            if kind=='amplitude' and abs(expected)>mp.mpf('1e-45'):
                relative=err/abs(expected);assert relative<mp.mpf('1e-9');assert v['relativeErrorUpperBound'] is not None and relative<=mp.mpf(v['relativeErrorUpperBound'])+mp.mpf('1e-90') and v['relativeErrorUpperBound']<=1e-9;maxrelative=max(maxrelative,float(relative));relcount+=1
print(json.dumps(dict(seed=SEED,freshCircuits=len(CASES),denseOracleDecimalDigits=110,amplitudeComparisons=counts['amplitude'],pauliComparisons=counts['pauli'],normComparisons=counts['norm'],relativeCertificates=relcount,maxAbsoluteError=float(maxerr),maxRelativeAmplitudeError=maxrelative,maxAbsoluteBound=maxbound,supportBoundaryTest='PASS'),indent=2))
