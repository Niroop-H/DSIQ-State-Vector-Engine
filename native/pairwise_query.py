"""Bounded pairwise tensor contractions and local floating-point balls.
The plan uses only tensor scopes. Center uses long-double complex arithmetic
for certified contractions. Radius uses outward-bounded positive FP64 dot
products; inputs too small for that path fail closed. No answer lookup.
"""
import math, collections, functools, time
import numpy as np
from hypergraph_plan import greedy_ssa,schedule,refine
from bond_contract import Boundary


def dot(a,b,left,right,out,fast=False):
    """Canonical batched matrix product. Sum indices that appear on only one
    operand first, and retain hyperedges shared with unconsumed factors."""
    left=list(left);right=list(right);out=tuple(out);os=set(out)
    for v in list(left):
        if v not in right and v not in os:
            axis=left.index(v);a=a.sum(axis=axis,dtype=a.dtype);left.pop(axis)
    for v in list(right):
        if v not in left and v not in os:
            axis=right.index(v);b=b.sum(axis=axis,dtype=b.dtype);right.pop(axis)
    shared=sorted(set(left)&set(right)&os);inner=sorted((set(left)&set(right))-os)
    lonly=sorted(set(left)-set(right));ronly=sorted(set(right)-set(left))
    a=np.asarray(a).transpose([left.index(v) for v in shared+lonly+inner]);b=np.asarray(b).transpose([right.index(v) for v in shared+inner+ronly]);batch=1<<len(shared);m=1<<len(lonly);k=1<<len(inner);n=1<<len(ronly)
    aa=a.reshape(batch,m,k);bb=b.reshape(batch,k,n)
    if fast:
        import fast_matrix
        z=fast_matrix.matmul(aa,bb).reshape((2,)*len(out))
    else:z=(aa@bb).reshape((2,)*len(out))
    order=shared+lonly+ronly
    return z.transpose([order.index(v) for v in out])


def center_dot(a,b,left,right,out):
    """Same as dot; all disappeared variables are shared, so no hidden sums."""
    if (set(left)|set(right))-set(out) != ((set(left)&set(right))-set(out)):
        raise Boundary('Pairwise interval requires degree-two eliminated labels')
    return dot(a,b,left,right,out)


def upper64(a):
    a=np.asarray(a);b=np.asarray(a,dtype=np.float64)
    if np.any(~np.isfinite(b)) or np.any((a>0)&(b==0)):raise Boundary('Positive-radius projection outside FP64 range')
    return np.nextafter(b,np.inf,where=b!=0,out=b.copy())


def upper_posdot(a,b,left,right,out):
    """Positive dot upper enclosure, assuming IEEE-754 round-to-nearest and no
    reduced-precision BLAS. Use conservative gamma plus outward projection.
    Reject possible underflow instead of relying on a BLAS subnormal mode."""
    n=1<<len((set(left)&set(right))-set(out));eps=np.finfo(np.float64).eps
    aa=a[a>0];bb=b[b>0]
    if len(aa) and len(bb) and min(float(aa.min()),1.)*min(float(bb.min()),1.)<np.finfo(float).tiny*4:
        raise Boundary('Positive dot possible underflow')
    g=8*eps*(n+2)
    if g>=.125:raise Boundary('Positive dot rounding budget too large')
    c=center_dot(a,b,left,right,out)
    if np.any(~np.isfinite(c)) or np.any(c<0):raise Boundary('Nonfinite positive dot')
    c=np.asarray(c*(1+2*g));return np.nextafter(c,np.inf,out=c.copy(),where=c!=0)


def ball_dot(a,b,left,right,out):
    import certified_query_contraction as c
    # Input centers/radii already enclose exact coefficients. Account for all
    # center-product and summation errors with a conservative gamma bound.
    k=1<<len((set(left)&set(right))-set(out));eps=c.R(np.finfo(c.R).eps);g=c.R(16)*eps*(k+2)
    if g>=.125:raise Boundary('Center dot rounding budget too large')
    am=upper64(c.mag(a.c));bm=upper64(c.mag(b.c));ar=upper64(c.radadd(a.r,c.radmul(g,c.mag(a.c))));br=upper64(c.radadd(b.r,c.radmul(g,c.mag(b.c))))
    zz=center_dot(a.c,b.c,left,right,out)
    # e <= |a|*rb + ra*(|b|+rb), with inflation above covering dot rounding.
    rbplus=np.nextafter(bm+br,np.inf,where=(bm+br)!=0,out=(bm+br).copy())
    r1=upper_posdot(am,br,left,right,out);r2=upper_posdot(ar,rbplus,left,right,out)
    rad=np.asarray(np.asarray(r1,dtype=c.R)+np.asarray(r2,dtype=c.R));rad=c.up(rad)
    return c.Ball(zz,rad)


def singleton_reduce(raw,budget,cert=False):
    # Unary labels can be summed independently before binary contractions.
    counts=collections.Counter(v for s,a in raw for v in s);fs=[]
    for s,a in raw:
        s=list(s)
        for v in list(s):
            if counts[v]==1:
                i=s.index(v);budget.charge(1<<len(s),max(1,a.nbytes)*3,len(s));
                if cert:
                    order=[j for j in range(len(s)) if j!=i]+[i];a=a.transpose(order).sum2()
                else:a=a.sum(axis=i)
                s.pop(i)
        fs.append((tuple(s),a))
    return fs


def plan_estimate(scopes,steps,cert=False,fast=False):
    """Revalidate every schedule and track conservative live buffers. Work is
    logical pair scalar products; a ball uses one complex and two real dots.
    Distinct from the previous element-by-element interval work counter."""
    item=48 if cert else 16;active={i:set(s) for i,s in enumerate(scopes)};counts=collections.Counter(v for s in scopes for v in s);live=sum(item*(1<<len(s)) for s in scopes);peak=live;work=0;rank=0
    for t,(i,j,oo) in enumerate(steps):
        if i==j or i not in active or j not in active:raise Boundary('Invalid pair IDs')
        a,b=active.pop(i),active.pop(j);u=a|b;o=set()
        for v in u:
            counts[v]-=(v in a)+(v in b)
            if counts[v]:o.add(v);counts[v]+=1
        if o!=set(oo):raise Boundary('Invalid pair output labels')
        na,nb,no=1<<len(a),1<<len(b),1<<len(o);
        if fast and not cert:
            import fast_matrix
            inter=len(a&b);batch=len(a&b&o);k=inter-batch;m=len(a-b);n=len(b-a)
            c,depth=fast_matrix.choose(1<<m,1<<k,1<<n);work+=(1<<batch)*c
            # Conservative scratch allowance including recursive output and
            # two operand sums, temporary old/new products and layout copies.
            extra=64*(na+nb+no) if depth else 32*(na+nb+no)
        else:work+=(1<<len(u))*(3 if cert else 1);extra=(96*(na+nb)+128*no) if cert else (32*(na+nb)+32*no)
        rank=max(rank,len(o));peak=max(peak,live+extra);live+=item*(no-na-nb);active[len(scopes)+t]=o
    if len(active)!=1 or next(iter(active.values())):raise Boundary('Incomplete pair plan')
    return work,peak,rank


def admissible(est,budget):return est[0]+budget.work<=budget.mw and est[1]<=budget.mb and 2**est[2]<=budget.mn*64

@functools.lru_cache(maxsize=16)
def candidates(scopes):
    import opt_einsum as oe
    # Deterministic multistart followed by subset-DP tree optimization. No
    # persisted fixture-specific paths. Search bounded by fixed seed count.
    n=len(scopes);p=oe.paths.greedy([frozenset(s) for s in scopes],frozenset(),{v:2 for s in scopes for v in s});ids=list(range(n));ssa=[]
    for ix in p:
        if len(ix)!=2:raise Boundary('Pair planner requires binary steps')
        i,j=sorted(ix);ssa.append((ids[i],ids[j]));ids=[v for k,v in enumerate(ids) if k not in ix]+[n+len(ssa)-1]
    seeds=[schedule(scopes,ssa)]
    for i in range(32):
        x=greedy_ssa(scopes,i,weight=(.3,.6,.85,1.)[i%4],jitter=(0,.2,.5,.9)[i//4%4]);
        if x is not None:seeds.append(schedule(scopes,x[2]))
    top=sorted(seeds,key=lambda x:(x[0],x[1]))[:8];outs=list(top)
    for i,p in enumerate(top):
        x=refine(scopes,[(a,b) for a,b,o in p[3]],passes=4,k=8,seed=i);outs.append(x)
    top=sorted(outs,key=lambda x:(x[0],x[1]))[:3]
    for i,p in enumerate(top):
        x=refine(scopes,[(a,b) for a,b,o in p[3]],passes=3,k=10,seed=20+i);outs.append(x)
    return tuple(x[3] for x in sorted(outs,key=lambda x:(x[0],x[1]))[:12])


def execute(raw,budget,cert=False,steps=None,fast=False):
    if cert:
        import certified_query_contraction as c
        scalar=c.Ball(1)
    else:scalar=np.asarray(1+0j)
    raw=singleton_reduce(raw,budget,cert);fs=[]
    for s,a in raw:
        if not s:scalar=scalar.mul(a) if cert else scalar*a
        else:fs.append((s,a))
    if not fs:return scalar
    if len(fs)==1:raise Boundary('Unexpected uncontracted singleton tensor')
    scopes=tuple(s for s,a in fs)
    if steps is None:
        options=[(plan_estimate(scopes,p,cert,fast),p) for p in candidates(scopes)];chosen=min((x for x in options if admissible(x[0],budget)),default=None,key=lambda x:x[0][0]);
        if chosen is None:raise Boundary('Bounded pairwise planner found no feasible schedule: '+str([x[0] for x in options[:4]]))
        est,steps=chosen
    else:est=plan_estimate(scopes,steps,cert,fast)
    budget.charge(*est);active=dict(enumerate(fs));n=len(fs)
    with np.errstate(over='raise',invalid='raise',under='raise'):
        for t,(i,j,o) in enumerate(steps):
            s,a=active.pop(i);r,b=active.pop(j);o=tuple(o);z=ball_dot(a,b,s,r,o) if cert else dot(a,b,s,r,o,fast=fast);active[n+t]=(o,z);budget.steps+=1
    _,z=next(iter(active.values()));return scalar.mul(z) if cert else complex(scalar*z)


@functools.lru_cache(maxsize=8)
def optimized_paths(scopes):
    """Generate native fallback plans from tensor scopes only. Search happens
    inside the audited worker and shares its wall/CPU limits. The fixed seed
    sequence does not depend on the circuit identity or reference values."""
    import region_refine as rr
    import tree_anneal as anneal
    seeds=candidates(scopes)
    best=min(seeds,key=lambda t:plan_estimate(scopes,t,False,True)[0]);options=[best,*seeds]
    if rr.DP is not None and rr.FAST is not None:
        for i in range(3):
            # Deterministic stage count; time cap bounds expensive searches.
            p,cost=anneal.run(scopes,best,seed=i+10,rounds=30,seconds=15,fast=True)
            cur=p[3];a=plan_estimate(scopes,cur,False,True);b=plan_estimate(scopes,best,False,True)
            options.append(cur)
            if a[0]<b[0]:best=cur
            if a[0]<=200000000:break
    return tuple(options)

def optimized_execute(raw,budget):
    raw=singleton_reduce(raw,budget,False);scalar=1+0j;fs=[]
    for s,a in raw:
        if not s:scalar*=complex(a)
        else:fs.append((s,a))
    if not fs:return scalar
    if scalar==0:return 0j
    scopes=tuple(s for s,a in fs);paths=optimized_paths(scopes)
    options=[(plan_estimate(scopes,t,False,True),t) for t in paths]
    chosen=min((x for x in options if admissible(x[0],budget)),default=None,key=lambda x:x[0][0])
    if chosen is None:raise Boundary('No feasible optimized pair contraction; best estimates '+str(sorted(x[0] for x in options)[:4]))
    # The dangling labels were already removed. The scalar multiplier is
    # kept separate so the planner's input shape exactly matches execution.
    return scalar*execute(fs,budget,False,chosen[1],fast=True)
