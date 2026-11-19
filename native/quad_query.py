"""Bounded experimental binary128-center / outward FP64-radius contractions.
Gate centers originate in the existing integer enclosures. IEEE binary128
round-to-nearest and IEEE FP64 BLAS are assumptions, not externally attested.
Fail closed on unsupported dynamic range. No reference values in execution.
"""
import ctypes,os,math,collections,time
import numpy as np
from bond_contract import Boundary
import pairwise_query as p
import integer_query_contraction as high
D=np.dtype('V32');E=2.0**-112

def load():
    path=os.environ.get('DSIQ_QUAD_LIBRARY')
    if not path:raise Boundary('Optional binary128 library unavailable')
    lib=ctypes.CDLL(path);P=ctypes.c_void_p;N=ctypes.c_size_t
    for name,types in [('qparse',[P,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int]),('qmag',[N,P,P]),('qdot',[N,N,N,N,P,P,P]),('qproj',[P,P])]:
        f=getattr(lib,'dsiq_'+name);f.argtypes=types;f.restype=ctypes.c_int
    return lib
L=None
def lib():
    global L
    if L is None:L=load()
    return L

def upper(a):
    a=np.asarray(a,dtype=np.float64)
    if np.any(~np.isfinite(a)) or np.any(a<0):raise Boundary('Invalid radius')
    return np.nextafter(a,np.inf,out=a.copy(),where=a!=0)

def mag(a):
    a=np.ascontiguousarray(a);z=np.empty(a.shape,float)
    if lib().dsiq_qmag(a.size,a.ctypes.data,z.ctypes.data):raise Boundary('Quad center outside supported FP64 magnitude range')
    return z

class Ball:
    def __init__(self,c,r):self.c=np.asarray(c,dtype=D);self.r=np.broadcast_to(np.asarray(r,float),self.c.shape).copy()
    @property
    def nbytes(self):return self.c.nbytes+self.r.nbytes
    def transpose(self,o):return Ball(self.c.transpose(o),self.r.transpose(o))
    def reshape(self,s):return Ball(self.c.reshape(s),self.r.reshape(s))
    def mul(self,b):return dot(self,b,(),(),())

def convert(a):
    c=np.empty(a.re.shape,D);r=np.empty(a.re.shape,float)
    for j,(re,im,rad) in enumerate(zip(a.re.flat,a.im.flat,a.r.flat)):
        if lib().dsiq_qparse(c.ctypes.data+32*j,str(re).encode(),str(im).encode(),high.B):raise Boundary('Quad input conversion')
        v=int(rad)/high.S;r.flat[j]=math.nextafter(v,math.inf) if rad else 0.
    # strtoflt128 rounds the integer before power-of-two scaling. The
    # conversion radius covers both projected components conservatively.
    return Ball(c,upper(r+upper(8*E*mag(c).reshape(c.shape))))

def constant(z):return convert(high.constant(z))

def dot(a,b,left,right,out):
    ls=set(left);rs=set(right);oset=set(out)
    if (ls|rs)-oset!=(ls&rs)-oset:raise Boundary('Quad dot requires shared eliminated labels')
    shared=sorted(ls&rs&oset);inner=sorted((ls&rs)-oset);lo=sorted(ls-rs);ro=sorted(rs-ls)
    x=np.ascontiguousarray(a.c.transpose([left.index(v) for v in shared+lo+inner]));y=np.ascontiguousarray(b.c.transpose([right.index(v) for v in shared+inner+ro]));batch,m,k,n=(1<<len(v) for v in (shared,lo,inner,ro));z=np.empty((batch,m,n),D)
    if lib().dsiq_qdot(batch,m,k,n,x.ctypes.data,y.ctypes.data,z.ctypes.data):raise Boundary('Nonfinite quad dot')
    order=shared+lo+ro;z=z.reshape((2,)*len(out)).transpose([order.index(v) for v in out]);am=mag(a.c).reshape(a.c.shape);bm=mag(b.c).reshape(b.c.shape);g=16*E*(k+2)
    # Inflate each input radius to enclose accumulated rounded quad dot.
    ar=upper(a.r+upper(g*am));br=upper(b.r+upper(g*bm));bp=upper(bm+br)
    r=upper(p.upper_posdot(am,br,left,right,out)+p.upper_posdot(ar,bp,left,right,out))
    return Ball(z,r)

def result(a):
    c=np.ascontiguousarray(a.c);v=np.empty(3,float)
    if lib().dsiq_qproj(c.ctypes.data,v.ctypes.data):raise Boundary('Projection boundary')
    re,im,d=map(float,v);r=math.nextafter(float(a.r)+d,math.inf);lo=max(0.,math.nextafter(max(abs(re),abs(im))-r,-math.inf));rel=math.nextafter(r/lo,math.inf) if lo else None
    return dict(real=re,imag=im,absoluteErrorBound=r,certifiedMagnitudeLowerBound=lo,relativeErrorUpperBound=rel,componentUnderflow=False,definition='experimental IEEE binary128 center with outward FP64 radius')

def execute(raw,budget,steps=None):
    # Sum dangling labels exactly on the input dyadic grid before conversion.
    counts=collections.Counter(v for s,a in raw for v in s);fs=[];scalar=high.constant(1)
    for s,a in raw:
        s=list(s)
        for v in list(s):
            if counts[v]==1:
                i=s.index(v);budget.charge(1<<len(s),a.nbytes*3,len(s));a=a.transpose([j for j in range(len(s)) if j!=i]+[i]).sum2();s.pop(i)
        if not s:scalar=scalar.mul(a)
        else:fs.append((tuple(s),convert(a)))
    if not fs:return convert(scalar)
    sc=tuple(s for s,a in fs)
    if steps is None:steps=plan(sc,budget)
    est=p.plan_estimate(sc,steps,True);budget.charge(*est);active=dict(enumerate(fs));n=len(fs)
    for t,(i,j,o) in enumerate(steps):
        s,a=active.pop(i);r,b=active.pop(j);o=tuple(o);z=dot(a,b,s,r,o);active[n+t]=(o,z);budget.steps+=1
    _,z=next(iter(active.values()));return dot(convert(scalar),z,(),(),())


import functools
@functools.lru_cache(maxsize=8)
def planned(sc):
    import region_refine as rr
    seeds=p.candidates(sc);steps=min(seeds,key=lambda t:p.plan_estimate(sc,t,True)[0])
    if rr.DP is not None:
        candidate=rr.refine(sc,steps,iterations=40,k=14,seed=1)[3]
        if p.plan_estimate(sc,candidate,True)[0]<p.plan_estimate(sc,steps,True)[0]:steps=candidate
    return (steps,*seeds)

def plan(sc,budget):
    choices=[(p.plan_estimate(sc,t,True),t) for t in planned(sc)]
    chosen=min((x for x in choices if p.admissible(x[0],budget)),default=None,key=lambda x:x[0][0])
    if chosen is None:raise Boundary('No feasible binary128 pairwise path')
    return chosen[1]

def evaluate(n,gs,q,budget,ms):
    from query_contraction import reduce_gates,fuse_parity_phases
    if q['kind']!='amplitude':raise Boundary('Binary128 fallback currently admits amplitudes only')
    gs=fuse_parity_phases(n,reduce_gates(n,gs));net=high.Network(n,ms);w=net.build(gs)
    for v,b in zip(w,q['bits'][::-1]):
        b=int(b)
        if v in net.fixed and net.fixed[v]!=b:return result(constant(0)),dict(reducedGates=len(gs),**budget.stats())
        net.fixed[v]=b
    z=execute(net.simplify(),budget);return result(z),dict(reducedGates=len(gs),precisionEscalation='native-binary128-pairwise',**budget.stats())
