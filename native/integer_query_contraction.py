"""Precision-escalation contraction for feasible narrow separators.
Exact signed Python integer arithmetic on a 1280-bit dyadic grid. A complex
center plus an outward L1 radius; input gate enclosures are the same rigorous
192-bit gate intervals, not reference data. No BLAS or floating-point
arithmetic participates in the enclosure before final binary64 projection.
"""
import collections, json, math, pathlib, subprocess
import numpy as np
from query_contraction import Boundary, reduce_gates, fuse_parity_phases, cone, pauli_links, variable_plan
B=1280; S=1<<B; SHIFT=B-192; UNIT=768; ROOT=pathlib.Path(__file__).resolve().parent

def arr(a):return np.asarray(a,dtype=object)
def ceildiv(x):return (x+S-1)//S
class IntBall:
    def __init__(self,re,im=0,r=0):
        self.re=arr(re);self.im=np.broadcast_to(arr(im),self.re.shape).copy();self.r=np.broadcast_to(arr(r),self.re.shape).copy()
    @property
    def nbytes(self):return self.re.size*UNIT
    def zero(self):return (self.re==0)&(self.im==0)&(self.r==0)
    def get(self,key):return IntBall(self.re[key],self.im[key],self.r[key])
    def transpose(self,key):return IntBall(self.re.transpose(key),self.im.transpose(key),self.r.transpose(key))
    def reshape(self,shape):return IntBall(self.re.reshape(shape),self.im.reshape(shape),self.r.reshape(shape))
    def conj(self):return IntBall(self.re,-self.im,self.r)
    def flip(self,axis):return IntBall(np.flip(self.re,axis),np.flip(self.im,axis),np.flip(self.r,axis))
    def mul(self,b):
        a=self;rr=a.re*b.re-a.im*b.im;ii=a.re*b.im+a.im*b.re;re=rr//S;im=ii//S
        rad=ceildiv((abs(a.re)+abs(a.im))*b.r+(abs(b.re)+abs(b.im))*a.r+a.r*b.r)+(rr%S!=0).astype(object)+(ii%S!=0).astype(object) if isinstance(rr,np.ndarray) else ceildiv((abs(a.re)+abs(a.im))*b.r+(abs(b.re)+abs(b.im))*a.r+a.r*b.r)+int(rr%S!=0)+int(ii%S!=0)
        return IntBall(re,im,rad)
    def plus(self,b):return IntBall(self.re+b.re,self.im+b.im,self.r+b.r)
    def sum2(self):return self.get((...,0)).plus(self.get((...,1)))

def constant(a):
    a=np.asarray(a);re=np.vectorize(lambda x:int(x)*S,otypes=[object])(a.real);im=np.vectorize(lambda x:int(x)*S,otypes=[object])(a.imag);return IntBall(re,im)
def stack(a,b):return IntBall(np.stack([a.re,b.re]),np.stack([a.im,b.im]),np.stack([a.r,b.r]))
def gate_key(g):return json.dumps({k:v for k,v in g.items() if k not in ('q','controls')},sort_keys=True,separators=(',',':'))
def matrices(gs):
    keys=list(dict.fromkeys(gate_key(g) for g in gs if g['name']!='swap'));p=subprocess.run(['node',str(ROOT/'export-interval-matrices.mjs')],input=json.dumps([json.loads(k) for k in keys]),text=True,capture_output=True,timeout=30)
    if p.returncode:raise Boundary('Integer gate interval compilation failed')
    out={}
    for k,v in zip(keys,json.loads(p.stdout)):
        re=[];im=[];rad=[]
        for a,b in v:
            l,h=(int(x)<<SHIFT for x in a);u,w=(int(x)<<SHIFT for x in b);r=(l+h)//2;i=(u+w)//2;re.append(r);im.append(i);rad.append(max(r-l,h-r)+max(i-u,w-i))
        out[k]=IntBall(arr(re).reshape(2,2),arr(im).reshape(2,2),arr(rad).reshape(2,2))
    if len(out)!=len(keys):raise Boundary('Incomplete matrix compilation')
    return out

class Network:
    def __init__(self,n,ms):self.n=n;self.ms=ms;self.next=0;self.f=[];self.fixed={}
    def fresh(self):v=self.next;self.next+=1;return v
    def build(self,gs,conj=False):
        w=[self.fresh() for _ in range(self.n)];self.fixed.update({v:0 for v in w})
        for g in gs:
            q=g['q'];cs=g['controls'];a=w[q];name=g['name']
            if name=='swap':c=cs[0];w[q],w[c]=w[c],w[q];continue
            if name=='_parity_phase':
                d=self.ms[gate_key(g['diagonal'])];d=d.conj() if conj else d;v=d.get((np.arange(2),np.arange(2)));i=np.array([[0,1],[1,0]]);self.f.append(((w[cs[0]],a),v.get(i)));continue
            m=self.ms[gate_key(g)];m=m.conj() if conj else m;z=m.zero()
            if z[0,1] and z[1,0]:
                v=m.get((np.arange(2),np.arange(2)));self.f.append(((w[cs[0]],a),stack(constant([1,1]),v)) if cs else ((a,),v))
            else:
                b=self.fresh();w[q]=b;self.f.append(((w[cs[0]],b,a),stack(constant(np.eye(2)),m)) if cs else ((b,a),m))
        return w
    def simplify(self):
        fs=self.f;fixed=self.fixed
        while True:
            new=[];updates={}
            for s,a in fs:
                if any(v in fixed for v in s):a=a.get(tuple(fixed.get(v,slice(None)) for v in s));s=tuple(v for v in s if v not in fixed)
                zz=a.zero()
                if np.all(zz):return [((),constant(0))]
                if s and np.any(zz):
                    for i,v in enumerate(s):
                        allowed=np.any(~np.moveaxis(zz,i,0).reshape(2,-1),axis=1)
                        if allowed[0]!=allowed[1]:
                            b=int(allowed[1]);
                            if v in updates and updates[v]!=b:return [((),constant(0))]
                            updates[v]=b
                new.append((s,a))
            fs=new
            if not updates:break
            fixed.update(updates)
        merged={}
        for s,a in fs:
            k=tuple(sorted(s));a=a.transpose(tuple(s.index(v) for v in k)) if k!=s else a
            merged[k]=merged[k].mul(a) if k in merged else a
        return list(merged.items())

def contract(raw,budget):
    # Strict bounded escalation: conservative work and array forecasts. Avoid
    # allocating high-rank large object arrays just to seek a tighter radius.
    fs={i:(s,a) for i,(s,a) in enumerate(raw)};uid=len(fs);links=collections.defaultdict(set);live=0;scalar=constant(1)
    for i,(s,a) in list(fs.items()):
        if not s:scalar=scalar.mul(a);del fs[i];continue
        live+=a.nbytes
        for v in s:links[v].add(i)
    if scalar.zero():return scalar
    scopes=tuple(s for s,a in raw if s);plans=[variable_plan(scopes,k) for k in range(4)];fit=[p for p in plans if p[2]<=13 and p[0]*64+budget.work<=budget.mw and p[1]*UNIT*5<=budget.mb and 2**p[2]<=budget.mn*64]
    if not fit:raise Boundary('No feasible high-precision integer contraction plan')
    for v in min(fit,key=lambda p:p[:3])[3]:
        ids=sorted(links[v]);t=[fs[i] for i in ids];scope=tuple(sorted(set().union(*(s for s,a in t))-{v}));rank=len(scope)+1
        budget.charge((1<<rank)*max(1,len(ids))*64,live+UNIT*((1<<rank)*15+(1<<len(scope))*4),rank)
        full=scope+(v,);a=None
        for s,x in t:
            order=tuple(sorted(range(len(s)),key=lambda i:full.index(s[i])));ss=[s[i] for i in order];x=x.transpose(order).reshape(tuple(2 if w in ss else 1 for w in full));a=x if a is None else a.mul(x)
        z=a.sum2();budget.steps+=1
        for i,(s,x) in zip(ids,t):
            del fs[i];live-=x.nbytes
            for w in s:links[w].discard(i)
        del links[v]
        if scope:
            fs[uid]=(scope,z);live+=z.nbytes
            for w in scope:links[w].add(uid)
            uid+=1
        else:scalar=scalar.mul(z)
    if links:raise RuntimeError('Incomplete high-precision contraction')
    return scalar

def evaluate(n,gs,q,budget,ms):
    gs=fuse_parity_phases(n,reduce_gates(n,gs));kind=q['kind'];net=Network(n,ms)
    if kind=='amplitude':
        w=net.build(gs)
        for v,b in zip(w,q['bits'][::-1]):
            b=int(b)
            if v in net.fixed and net.fixed[v]!=b:return constant(0),dict(reducedGates=len(gs))
            net.fixed[v]=b
    else:
        p=q.get('pauli','I'*n)
        if kind=='pauli':gs=cone(n,gs,p)
        ket=net.build(gs);bra=net.build(gs,True);pm=pauli_links(net,ket,bra,p)
        if pm is None:return constant(0),dict(reducedGates=len(gs))
        mapping,net.fixed=pm;fs=[]
        for s,a in net.f:
            for i,v in enumerate(s):
                if v in mapping and mapping[v][1]:a=a.flip(i)
            fs.append((tuple(mapping.get(v,(v,0))[0] for v in s),a))
        net.f=fs
        for k,o in zip(ket,p[::-1]):
            if o in 'YZ':net.f.append(((k,),constant([1j,-1j] if o=='Y' else [1,-1])))
    z=contract(net.simplify(),budget);return z,dict(reducedGates=len(gs),**budget.stats())

def result(a):
    R=int(a.re);I=int(a.im);re=R/S;im=I/S
    if not all(map(math.isfinite,(re,im))):raise Boundary('Nonfinite integer output')
    def units(x):n,d=x.as_integer_ratio();return n*(S//d)
    r=int(a.r)+abs(R-units(re))+abs(I-units(im));bound=math.nextafter(r/S,math.inf) if r else 0.;lo=max(0.,math.nextafter(max(abs(re),abs(im))-bound,-math.inf));rel=math.nextafter(bound/lo,math.inf) if lo and bound else (0. if lo else None)
    return dict(real=re,imag=im,absoluteErrorBound=bound,certifiedMagnitudeLowerBound=lo,relativeErrorUpperBound=rel if rel is None or math.isfinite(rel) else None,componentUnderflow=bool((R and not re) or (I and not im)),definition='1280-bit integer complex center and outward L1 radius; rigorous 192-bit gate intervals; binary64 projection included')
