#!/usr/bin/env python3
"""Fresh source-scatter oracle comparisons; not Astra's fixtures or answers."""
import json, os, pathlib, random, subprocess, sys, importlib.util, hashlib
import mpmath as mp
ROOT=pathlib.Path(__file__).resolve().parents[1];mp.mp.dps=110
SEED=145926307;rng=random.Random(SEED)
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


import numpy as np
sys.path.insert(0,str(ROOT/'native'))
import integer_query_contraction as hi
from query_contraction import Budget
queries=0;maxabs=mp.mpf(0);maxrel=mp.mpf(0)
for run in range(10):
 n=4+run%2;gs=[]
 for layer in range(3):
  for q in range(n):
   g=single(q)
   while g['name'] in ('sx','sy'):g=single(q)
   gs.append(g)
  for j in range(n):
   q,c=rng.sample(range(n),2);g=controlled(q,c)
   while g['name']=='csx':g=controlled(q,c)
   gs.append(g)
  q,c=rng.sample(range(n),2);gs.append(gate('swap',q,[c]))
 ms=hi.matrices(gs);budget=Budget(67108864,1000000000,32768);a=[mp.mpc(int(x==0)) for x in range(2**n)]
 for g in gs:a=evolve(a,g)
 tests=[({'kind':'amplitude','bits':format(x,f'0{n}b')},v) for x,v in enumerate(a)]
 for _ in range(8):
  p=''.join(rng.choices('IXYZ',k=n));tests.append(({'kind':'pauli','pauli':p},obs(a,p)))
 tests.append(({'kind':'norm'},mp.fsum(abs(v)**2 for v in a)))
 for q,v in tests:
  z,_=hi.evaluate(n,gs,q,budget,ms);r=hi.result(z);error=abs(mp.mpc(r['real'],r['imag'])-v);assert error<=mp.mpf(r['absoluteErrorBound'])+mp.mpf('1e-102'),(q,error,r);assert error<=mp.mpf('1e-13');maxabs=max(maxabs,error);queries+=1
  if q['kind']=='amplitude' and abs(v)>mp.mpf('1e-95'):
   relative=error/abs(v);assert relative<=mp.mpf('1e-9') and r['relativeErrorUpperBound'] is not None and relative<=mp.mpf(r['relativeErrorUpperBound'])+mp.mpf('1e-90');maxrel=max(maxrel,relative)
print(json.dumps({'seed':SEED,'circuits':10,'comparisons':queries,'denseReferenceDigits':110,'maxAbsoluteError':float(maxabs),'maxRelativeAmplitudeError':float(maxrel)},indent=2))
