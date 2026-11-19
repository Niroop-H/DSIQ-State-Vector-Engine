#!/usr/bin/env python3
"""Independent dense-oracle checks for the new pair/quad execution paths."""
import json,math,random,pathlib,sys
import mpmath as mp
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'native'))
import query_contraction as m,integer_query_contraction as high,quad_query as quad,pairwise_query as pair,fast_matrix as fm,hypergraph_plan as hp,region_refine as rr,tree_anneal as anneal
mp.mp.dps=100;seed=16393923;rng=random.Random(seed)
def gate(name,q,cs=(),**kw):return dict(name=name,q=q,controls=list(cs),**kw)
def mat(g):
    name=g['name'];t=mp.mpf(g.get('theta',0));c=mp.cos(t/2);s=mp.sin(t/2);i=mp.j
    if name in ('x','cx'):return [0,1,1,0]
    if name in ('z','cz'):return [1,0,0,-1]
    if name=='h':return [1/mp.sqrt(2)]*3+[-1/mp.sqrt(2)]
    if name in ('rx','crx'):return [c,-i*s,-i*s,c]
    if name in ('ry','cry'):return [c,-s,s,c]
    if name in ('rz','crz'):return [mp.exp(-i*t/2),0,0,mp.exp(i*t/2)]
    if name in ('p','cp'):return [1,0,0,mp.exp(i*t)]
    if name in ('u','cu'):
        p,l=mp.mpf(g['phi']),mp.mpf(g['lambda']);return [c,-s*mp.exp(i*l),s*mp.exp(i*p),c*mp.exp(i*(p+l))]
    raise ValueError(name)
def evolve(a,g):
    q=g['q'];cs=g['controls'];b=[mp.mpc(0) for _ in a];M=mat(g)
    for x,v in enumerate(a):
        if not all(x>>c&1 for c in cs):b[x]+=v;continue
        for row in range(2):b[(x&~(1<<q))|(row<<q)]+=M[2*row+(x>>q&1)]*v
    return b
def netraw(n,gs,bits,ms=None):
    gs=m.fuse_parity_phases(n,m.reduce_gates(n,gs));net=high.Network(n,ms) if ms is not None else m.Network(n);w=net.build(gs)
    for v,b in zip(w,bits[::-1]):
        b=int(b)
        if v in net.fixed and net.fixed[v]!=b:return [((),high.constant(0))] if ms is not None else [((),np.asarray(0j))]
        net.fixed[v]=b
    return net.simplify()
max_quad=mp.mpf(0);max_fast=mp.mpf(0);max_rel=mp.mpf(0);nq=nr=0
for case in range(14):
    n=4+case%3;gs=[]
    for layer in range(4):
        for q in range(n):
            name=rng.choice(['rx','ry','rz','u','h']);gs.append(gate(name,q,**({k:rng.uniform(-3,3) for k in m.PARAM.get(name,())})))
        for _ in range(n):
            a,b=rng.sample(range(n),2);name=rng.choice(['cx','cz','cp','crx','cry','cu']);gs.append(gate(name,a,[b],**{k:rng.uniform(-3,3) for k in m.PARAM.get(name,())}))
    st=[mp.mpc(int(x==0)) for x in range(1<<n)]
    for g in gs:st=evolve(st,g)
    ms=high.matrices(gs)
    for x,target in enumerate(st):
        bits=format(x,f'0{n}b');b=m.Budget(2**28,10**9,1000000);raw=netraw(n,gs,bits,ms)
        v=quad.result(quad.execute(raw,b));err=abs(mp.mpc(v['real'],v['imag'])-target);assert err<=mp.mpf(v['absoluteErrorBound'])+mp.mpf('1e-92'),(case,x,err,v);max_quad=max(max_quad,err)
        if abs(target)>mp.mpf('1e-90'):
            rel=err/abs(target);assert v['relativeErrorUpperBound'] is not None and rel<=mp.mpf(v['relativeErrorUpperBound'])+mp.mpf('1e-88') and v['relativeErrorUpperBound']<=1e-9;max_rel=max(max_rel,rel);nr+=1
        b=m.Budget(2**28,10**9,1000000);raw=netraw(n,gs,bits);raw=pair.singleton_reduce(raw,b);sc=tuple(s for s,a in raw if s)
        if len(sc)>1:
            path=hp.portfolio(sc,repeats=4)[0][3];z=pair.execute(raw,b,steps=path,fast=True)
        else:z=pair.optimized_execute(raw,b)
        e=abs(mp.mpc(z.real,z.imag)-target);assert e<=mp.mpf('1e-13') and (abs(target)<mp.mpf('1e-90') or e/abs(target)<=mp.mpf('1e-9'));max_fast=max(max_fast,e);nq+=1
# Exact small integer complex matrices exercise the seven-product recursion.
ng=np.random.default_rng(seed);matcases=[]
for M,K,N in [(128,128,128),(256,128,64),(128,64,256),(256,256,128)]:
    a=ng.integers(-2,3,(2,M,K))+1j*ng.integers(-2,3,(2,M,K));b=ng.integers(-2,3,(2,K,N))+1j*ng.integers(-2,3,(2,K,N));z=fm.matmul(a,b);assert np.array_equal(z,a@b);c,d=fm.choose(M,K,N);assert c<=M*K*N;matcases.append(dict(shape=[M,K,N],selectedDepth=d,workUnits=c))
assert any(x['selectedDepth'] for x in matcases)
# Tampered schedule must be rejected before execution.
try:pair.plan_estimate(((0,),(0,)),[(0,1,(0,))]);raise AssertionError('tamper admitted')
except m.Boundary:pass
print(json.dumps(dict(seed=seed,freshCircuits=14,comparisonsPerBackend=nq,relativeCertChecks=nr,maxQuadAbsError=float(max_quad),maxQuadRelativeError=float(max_rel),maxFastAbsError=float(max_fast),matrixChecks=matcases,tamperedPlanRejected=True),indent=2))
