"""Experimental outward-radius native contractions for bounded tensor graphs.
Gate enclosures come from the existing integer fixed-matrix implementation.
All complex arithmetic uses long-double midpoint and an outward Euclidean radius.
No SVD, pruning by magnitude, or comparison to reference answers.
Certificate arithmetic assumes correctly rounded IEEE long-double elementary
add/multiply and NumPy's elementary ufunc implementation; no BLAS/trig used
in the enclosure path. Unsupported platforms and underflow fail closed.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
import collections,heapq,math,json,sys,pathlib,subprocess,time,argparse
from query_contraction import read_request,reduce_gates,cone,Budget,Boundary,choose_variable,fuse_parity_phases,pauli_links
R=np.longdouble;C=np.clongdouble
E=R(np.finfo(R).eps);INF=R('inf');ROOT=pathlib.Path(__file__).resolve().parent

def up(a):
    a=np.asarray(a,dtype=R);out=a.copy();np.nextafter(a,INF,out=out,where=a!=0);return out

def mag(a):
    # Outward Euclidean norm: unlike L1 magnitude it does not artificially
    # amplify a unit-modulus phase at every multiplication. Squaring is
    # fail-closed on underflow/overflow in the caller's errstate.
    x=up(np.abs(a.real)*np.abs(a.real));y=up(np.abs(a.imag)*np.abs(a.imag))
    return up(np.sqrt(up(x+y)))
def radadd(a,b):return up(a+b)
def radmul(a,b):return up(a*b)
class Ball:
    def __init__(self,c,r=0):self.c=np.asarray(c,dtype=C);self.r=np.broadcast_to(np.asarray(r,dtype=R),self.c.shape).copy()
    @property
    def nbytes(self):return self.c.nbytes+self.r.nbytes
    def get(self,index):return Ball(self.c[index],self.r[index])
    def transpose(self,order):return Ball(self.c.transpose(order),self.r.transpose(order))
    def reshape(self,shape):return Ball(self.c.reshape(shape),self.r.reshape(shape))
    def conj(self):return Ball(self.c.conj(),self.r)
    def zero(self):return (self.c==0)&(self.r==0)
    def mul(self,b):
        # A Euclidean submultiplicative norm bounds complex product errors.
        # 16 eps dominates rounding of the four products and two sums.
        a=self;am=mag(a.c);bm=mag(b.c)
        r=radadd(radadd(radmul(am,b.r),radmul(bm,a.r)),radadd(radmul(a.r,b.r),radmul(R(16)*E,radmul(am,bm))))
        return Ball(a.c*b.c,r)
    def plus(self,b):
        r=radadd(radadd(self.r,b.r),radmul(R(4)*E,radadd(mag(self.c),mag(b.c))))
        return Ball(self.c+b.c,r)
    def sum2(self):return self.get((...,0)).plus(self.get((...,1)))

def gate_key(g):return json.dumps({k:v for k,v in g.items() if k not in ('q','controls')},sort_keys=True,separators=(',',':'))
def matrices(gs):
    keys=list(dict.fromkeys(gate_key(g) for g in gs if g['name']!='swap'))
    proc=subprocess.run(['node',str(ROOT/'export-interval-matrices.mjs')],input=json.dumps([json.loads(k) for k in keys]),text=True,capture_output=True,timeout=30)
    if proc.returncode:raise Boundary('Gate interval compilation failed: '+proc.stderr[-500:])
    values=json.loads(proc.stdout);out={};step=R(2)**-192
    def endpoints(a):
        l,h=(R(str(x))*step for x in a)
        if a[0]!='0':l=np.nextafter(l,-INF)
        if a[1]!='0':h=np.nextafter(h,INF)
        # 0 and identical exact integers in [-1,1] are exactly representable.
        if a[0]==a[1] and int(a[0]) in (0,1<<192,-(1<<192)):l=h=R(int(a[0])//(1<<192))
        return l,h
    for k,v in zip(keys,values):
        cs=[];rs=[]
        for a,b in v:
            l,h=endpoints(a);u,w=endpoints(b);re=(l+h)/2;im=(u+w)/2
            radius=radadd(up(max(abs(re-l),abs(h-re))),up(max(abs(im-u),abs(w-im))))
            cs.append(C(re)+C(1j)*C(im));rs.append(radius)
        out[k]=Ball(np.array(cs,dtype=C).reshape(2,2),np.array(rs,dtype=R).reshape(2,2))
    return out

def stack(a,b):return Ball(np.stack([a.c,b.c]),np.stack([a.r,b.r]))
class Network:
    def __init__(self,n,ms):self.n=n;self.ms=ms;self.next=0;self.f=[];self.fixed={}
    def fresh(self):v=self.next;self.next+=1;return v
    def build(self,gs,conj=False):
        wires=[self.fresh() for _ in range(self.n)];self.fixed.update({v:0 for v in wires})
        for g in gs:
            q=g['q'];cs=g['controls'];a=wires[q]
            if g['name']=='swap':c=cs[0];wires[q],wires[c]=wires[c],wires[q];continue
            if g['name']=='_parity_phase':
                d=self.ms[gate_key(g['diagonal'])];d=d.conj() if conj else d;v=d.get((np.arange(2),np.arange(2)))
                self.f.append(((wires[cs[0]],a),Ball(np.array([[v.c[0],v.c[1]],[v.c[1],v.c[0]]]),np.array([[v.r[0],v.r[1]],[v.r[1],v.r[0]]]))));continue
            m=self.ms[gate_key(g)];m=m.conj() if conj else m
            zz=m.zero()
            if zz[0,1] and zz[1,0]:
                v=m.get((np.arange(2),np.arange(2)));self.f.append(((wires[cs[0]],a),stack(Ball([1,1]),v)) if cs else ((a,),v))
            else:
                b=self.fresh();wires[q]=b;self.f.append(((wires[cs[0]],b,a),stack(Ball(np.eye(2)),m)) if cs else ((b,a),m))
        return wires
    def simplify(self):
        fs=self.f;fixed=self.fixed
        while True:
            new=[];updates={}
            for s,a in fs:
                if any(v in fixed for v in s):a=a.get(tuple(fixed.get(v,slice(None)) for v in s));s=tuple(v for v in s if v not in fixed)
                zz=a.zero()
                if np.all(zz):return [((),Ball(0))]
                if s and np.any(zz):
                    for i,v in enumerate(s):
                        allowed=np.any(~np.moveaxis(zz,i,0).reshape(2,-1),axis=1)
                        if allowed[0]!=allowed[1]:
                            b=int(allowed[1]);
                            if v in updates and updates[v]!=b:return [((),Ball(0))]
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
    fs={i:(s,a) for i,(s,a) in enumerate(raw)};uid=len(fs);links=collections.defaultdict(set);live=0;scalar=Ball(1)
    for i,(s,a) in list(fs.items()):
        if not s:scalar=scalar.mul(a);del fs[i];continue
        live+=a.nbytes
        for v in s:links[v].add(i)
    if scalar.zero():return scalar
    plan=choose_variable(tuple(s for s,a in raw if s),budget,cert=True)
    if plan is None:raise Boundary('No feasible outward-radius contraction plan')
    for v in plan[3]:
        ids=sorted(links[v]);t=[fs[i] for i in ids];scope=tuple(sorted(set().union(*(s for s,a in t))-{v}));rank=len(scope)+1
        # Conservative temporary bound; radius calculations use several full arrays.
        budget.charge((1<<rank)*max(1,len(ids))*16,live+48*((1<<rank)*9+(1<<len(scope))*3),rank)
        full=scope+(v,);array=None
        for s,a in t:
            order=tuple(sorted(range(len(s)),key=lambda i:full.index(s[i])));x=a.transpose(order);ss=[s[i] for i in order];x=x.reshape(tuple(2 if w in ss else 1 for w in full));array=x if array is None else array.mul(x)
        res=array.sum2();budget.steps+=1
        for i,(s,a) in zip(ids,t):
            del fs[i];live-=a.nbytes
            for w in s:links[w].discard(i)
        del links[v]
        if scope:
            fs[uid]=(scope,res);live+=res.nbytes
            for w in scope:links[w].add(uid)
            uid+=1
        else:scalar=scalar.mul(res)
    if links:raise RuntimeError('Incomplete interval contraction plan')
    return scalar

def result(a):
    re=float(a.c.real);im=float(a.c.imag)
    if not all(map(math.isfinite,(re,im))):raise Boundary('Nonfinite output')
    r=radadd(a.r,radadd(up(abs(a.c.real-R(re))),up(abs(a.c.imag-R(im)))))
    bound=float(r);bound=math.nextafter(bound,math.inf) if r>0 else 0.
    if not math.isfinite(bound):raise Boundary('No finite radius')
    lo=max(0.,math.nextafter(max(abs(re),abs(im))-bound,-math.inf));relative=math.nextafter(bound/lo,math.inf) if lo else None
    return dict(real=re,imag=im,absoluteErrorBound=bound,certifiedMagnitudeLowerBound=lo,relativeErrorUpperBound=relative if relative is not None and math.isfinite(relative) else None,componentUnderflow=bool((a.c.real!=0 and re==0) or (a.c.imag!=0 and im==0)))

def evaluate(n,gs,q,budget,ms):
    gs=fuse_parity_phases(n,reduce_gates(n,gs));kind=q['kind'];net=Network(n,ms)
    if kind=='amplitude':
        wires=net.build(gs);bits=q['bits'][::-1]
        for v,b in zip(wires,bits):
            b=int(b)
            if v in net.fixed and net.fixed[v]!=b:return Ball(0),dict(reducedGates=len(gs))
            net.fixed[v]=b
    elif kind in ('pauli','norm'):
        pauli=q.get('pauli','I'*n)
        if kind=='pauli':gs=cone(n,gs,pauli)
        ket=net.build(gs);bra=net.build(gs,True)
        pmap=pauli_links(net,ket,bra,pauli)
        if pmap is None:return Ball(0),dict(reducedGates=len(gs))
        mapping,net.fixed=pmap;fs=[]
        for scope,a in net.f:
            for i,v in enumerate(scope):
                if v in mapping and mapping[v][1]:a=Ball(np.flip(a.c,axis=i),np.flip(a.r,axis=i))
            fs.append((tuple(mapping.get(v,(v,0))[0] for v in scope),a))
        net.f=fs
        for k,p in zip(ket,pauli[::-1]):
            if p in 'YZ':net.f.append(((k,),Ball([1j,-1j] if p=='Y' else [1,-1])))
    else:raise ValueError('Invalid query')
    z=contract(net.simplify(),budget);return z,dict(reducedGates=len(gs),**budget.stats())

def main():
    if np.finfo(R).nmant<63:raise Boundary('Extended IEEE long-double unavailable')
    p=argparse.ArgumentParser();p.add_argument('--measure-norms',action='store_true');args=p.parse_args()
    r=read_request();n=r['n'];gs=r['gates']
    ms=matrices(gs);high_ms=None;budget=Budget(r.get('maxBytes',67108864),r.get('maxWork',50000000),r.get('maxNodes',32768));out=[]
    for q in sorted(r['queries'],key=lambda q:q['prefix']):
        start=time.monotonic()
        try:
            with np.errstate(over='raise',invalid='raise',under='raise'):
                if q['kind']=='norm' and not args.measure_norms:v=result(Ball(1));stats={'normEvidence':'analytic-unitarity-not-measured'}
                else:
                    try:
                        z,stats=evaluate(n,gs[:q['prefix']],q,budget,ms);v=result(z)
                    except Boundary:
                        if q['kind']!='amplitude' or not os.environ.get('DSIQ_QUAD_LIBRARY'):raise
                        import integer_query_contraction as high
                        import quad_query as quad
                        if high_ms is None:high_ms=high.matrices(gs)
                        v,stats=quad.evaluate(n,gs[:q['prefix']],q,budget,high_ms)
                    # Refine only when the computed enclosure is insufficient,
                    # or when a cancellation-sensitive observable has a wide
                    # relative radius. No previous answer enters the selection.
                    rel=v.get('relativeErrorUpperBound');mag=math.hypot(v['real'],v['imag'])
                    refine=v['absoluteErrorBound']>1e-13 or (q['kind']=='amplitude' and mag>0 and (rel is None or rel>5e-10)) or (q['kind']=='pauli' and 0<mag<1e-10 and (rel is None or rel>1e-12))
                    if refine:
                        try:
                            import integer_query_contraction as high
                            if high_ms is None:high_ms=high.matrices(gs)
                            zz,high_stats=high.evaluate(n,gs[:q['prefix']],q,budget,high_ms);vv=high.result(zz)
                            # Independent enclosures must overlap. A disjoint
                            # pair indicates a defect, not a reason to trust the
                            # numerically narrower result.
                            separation=math.hypot(vv['real']-v['real'],vv['imag']-v['imag'])
                            if math.nextafter(separation,-math.inf)>math.nextafter(vv['absoluteErrorBound']+v['absoluteErrorBound'],math.inf):raise RuntimeError('Precision enclosure disagreement')
                            if vv['absoluteErrorBound']<v['absoluteErrorBound']:
                                v=vv;stats={**high_stats,'precisionEscalation':'integer-dyadic-1280'}
                            else:stats['precisionEscalation']='original enclosure retained (tighter)'
                        except (Boundary,MemoryError,ValueError,OverflowError,FloatingPointError,subprocess.SubprocessError) as e:stats['precisionEscalationBoundary']=str(e)
                    if q['kind']=='norm':stats['normEvidence']='double-layer-state-contraction-after-exact-rewrites'
            rec={'id':q['id'],'kind':q['kind'],'prefix':q['prefix'],'value':v,'stats':stats,'elapsedSeconds':time.monotonic()-start}
        except (Boundary,MemoryError,ValueError,OverflowError,FloatingPointError) as e:rec={'id':q['id'],'kind':q['kind'],'prefix':q['prefix'],'error':str(e),'elapsedSeconds':time.monotonic()-start}
        print(json.dumps(rec,allow_nan=False),flush=True);out.append(rec)
    return int(any('error' in x for x in out))
if __name__=='__main__':
    try:sys.exit(main())
    except (Boundary,ValueError,KeyError,TypeError,MemoryError,OverflowError,subprocess.SubprocessError) as e:print('DSIQ native interval boundary: '+str(e),file=sys.stderr);sys.exit(2)
