"""Contraction-tree rotations with bounded simulated annealing. Planning only;
all returned paths must undergo exact scope/work/peak revalidation."""
import math,random,time
import hypergraph_plan as h
import region_refine as rr

def run(scopes,steps,seed=0,rounds=10,seconds=15,fast=False):
    T=rr.FastTree if fast else h.Tree;start=time.monotonic();rng=random.Random(seed)
    def cv(t):return T(i=t.i,mask=t.mask) if t.i is not None else T(a=cv(t.a),b=cv(t.b),mask=t.mask)
    root=cv(h.make_tree(scopes,[(a,b) for a,b,*_ in steps]));best=root
    def rotate(t,temp):
        if t.i is not None:return t
        if t.a.i is None and (t.b.i is not None or rng.random()<.5):a,b,c=t.a.a,t.a.b,t.b
        elif t.b.i is None:a,b,c=t.b.a,t.b.b,t.a
        else:return t
        def opt(a,b,c):
            ab=T(a=a,b=b,mask=(a.mask|b.mask)&(c.mask|t.mask));return T(a=ab,b=c,mask=t.mask)
        x=opt(a,c,b) if rng.random()<.5 else opt(b,c,a)
        if x.total<=t.total:return x
        # bounded uphill movement relative to affected local contraction work
        denom=max(1,t.cost+(t.a.cost if t.a.i is None else 0)+(t.b.cost if t.b.i is None else 0))
        return x if rng.random()<math.exp(-min(700,(x.total-t.total)/(denom*temp))) else t
    def sweep(t,temp):
        if t.i is not None:return t
        a,b=sweep(t.a,temp),sweep(t.b,temp);t=T(a=a,b=b,mask=t.mask)
        # More frequent rotations at high-cost internal boundaries.
        return rotate(t,temp) if rng.random()<(.75 if t.cost>65536 else .25) else t
    for j in range(rounds):
        if time.monotonic()-start>seconds:break
        root=best
        for k in range(14):
            root=sweep(root,0.4*0.78**k+0.015)
            if root.total<best.total:best=root
        try:
            p=h.schedule(scopes,h.tree_ssa(root,len(scopes)))
            p=rr.refine(scopes,p[3],iterations=24,k=14,seed=seed+j,fast=fast,deadline=start+seconds)
            root=cv(h.make_tree(scopes,[(a,b) for a,b,o in p[3]]))
            if root.total<best.total:best=root
        except (ValueError,RuntimeError):pass
    return h.schedule(scopes,h.tree_ssa(best,len(scopes))),best.total
