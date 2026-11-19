"""Deterministic bounded hypergraph contraction planner. No circuit identities or references.
Each merge removes an index only when its final incident factor is consumed.
"""
import heapq,random,math,collections,functools

def greedy_ssa(scopes,seed,weight=0.8,jitter=0.15):
    rng=random.Random(seed);active={i:set(s) for i,s in enumerate(scopes)};adj=collections.defaultdict(set)
    for i,s in active.items():
        for v in s:adj[v].add(i)
    h=[];uid=len(scopes);path=[];work=0;peak=0
    def offer(i,j):
        if i==j or i not in active or j not in active:return
        if i>j:i,j=j,i
        a,b=active[i],active[j];both=a&b
        if not both:return
        gone={v for v in both if len(adj[v])==2};out=(a|b)-gone
        # Penalize open separator size and union FLOPs, reward removed memory.
        cost=weight*len(out)+(1-weight)*len(a|b)-0.33*max(len(a),len(b))
        if jitter:cost+=jitter*rng.uniform(-1,1)
        heapq.heappush(h,(cost,i,j))
    seen=set()
    for ids in adj.values():
        for i in ids:
            for j in ids:
                if i<j and (i,j) not in seen:seen.add((i,j));offer(i,j)
    while len(active)>1:
        while h:
            _,i,j=heapq.heappop(h)
            if i in active and j in active:break
        else:i,j=sorted(active,key=lambda i:len(active[i]))[:2]
        a,b=active.pop(i),active.pop(j);union=a|b;out=set();changed=set()
        for v in union:
            bucket=adj[v];bucket.discard(i);bucket.discard(j)
            if bucket:out.add(v);bucket.add(uid);changed.update(bucket)
            else:del adj[v]
        path.append((i,j));work+=1<<len(union);peak=max(peak,len(out));active[uid]=out
        if work>2**51: return None
        for k in sorted(changed):offer(k,uid)
        # A merge can turn a hyperedge into an ordinary edge. Refresh the
        # affected surviving pair including any newly removable label.
        for v in a&b:
            bucket=adj.get(v,())
            if len(bucket)==2:
                k,l=sorted(bucket);offer(k,l)
        uid+=1
    return work,peak,tuple(path)

def schedule(scopes,ssa,item=16):
    active={i:set(s) for i,s in enumerate(scopes)};adj=collections.Counter(v for s in scopes for v in s)
    uid=len(scopes);live=sum(item*(1<<len(s)) for s in scopes);peak=live;work=0;rank=0;steps=[]
    for i,j in ssa:
        a,b=active.pop(i),active.pop(j);u=a|b;out=set()
        for v in u:
            adj[v]-=(v in a)+(v in b)
            if adj[v]:out.add(v);adj[v]+=1
        size=1<<len(out);ins=(1<<len(a))+(1<<len(b));work+=1<<len(u);peak=max(peak,live+item*(2*ins+2*size));rank=max(rank,len(out));live+=item*(size-ins);active[uid]=out
        steps.append((i,j,tuple(sorted(out))));uid+=1
    if len(active)!=1 or next(iter(active.values())):raise ValueError('Invalid contraction schedule')
    return work,peak,rank,tuple(steps)

@functools.lru_cache(maxsize=32)
def portfolio(scopes,repeats=96):
    best=[]
    for seed in range(repeats):
        p=greedy_ssa(scopes,seed,weight=(0.3,0.6,0.85,1.0)[seed%4],jitter=(0.0,0.2,0.5,0.9)[(seed//4)%4]);
        if p is None:continue
        best.append(p)
    # Pareto-ish portfolio, sorted by logical products and separator.
    return tuple(schedule(scopes,p[2]) for p in sorted(best,key=lambda p:(p[0],p[1]))[:8])

class Tree:
    __slots__=('i','a','b','mask','cost','total')
    def __init__(self,i=None,a=None,b=None,mask=0):
        self.i=i;self.a=a;self.b=b;self.mask=mask;self.cost=0 if i is not None else 1<<(a.mask|b.mask).bit_count();self.total=0 if i is not None else self.cost+a.total+b.total

def from_ssa(scopes,ssa):
    # Remap labels densely so Python integer masks are small.
    labels={v:i for i,v in enumerate(sorted({v for s in scopes for v in s}))}
    active={i:Tree(i=i,mask=sum(1<<labels[v] for v in s)) for i,s in enumerate(scopes)};counts=collections.Counter(v for s in scopes for v in s);uid=len(scopes)
    for i,j in ssa:
        a,b=active.pop(i),active.pop(j);u=a.mask|b.mask;shared=a.mask&b.mask
        while shared:
            x=shared&-shared;shared^=x;idx=x.bit_length()-1
            # label counts indexed by dense id below
            counts_dense=None
        # Rebuild count representation by bit, once outside loop below.
        active[uid]=Tree(a=a,b=b,mask=u);uid+=1
    return next(iter(active.values()))

def make_tree(scopes,ssa):
    active={i:Tree(i=i,mask=sum(1<<v for v in s)) for i,s in enumerate(scopes)};counts=collections.Counter(v for s in scopes for v in s);uid=len(scopes)
    for i,j in ssa:
        a,b=active.pop(i),active.pop(j);u=a.mask|b.mask;x=a.mask&b.mask
        while x:
            bit=x&-x;x^=bit;v=bit.bit_length()-1;counts[v]-=1
            if counts[v]==1:u^=bit;del counts[v]
        active[uid]=Tree(a=a,b=b,mask=u);uid+=1
    return next(iter(active.values()))

def tree_ssa(root,n):
    path=[]
    def visit(t):
        if t.i is not None:return t.i
        a,b=visit(t.a),visit(t.b);i=n+len(path);path.append((a,b));return i
    visit(root);return tuple(path)

def optimize_region(root,k=8,rng=None):
    if root.i is not None:return root
    leaves=[root.a,root.b]
    while len(leaves)<k:
        eligible=[i for i,x in enumerate(leaves) if x.i is None]
        if not eligible:break
        j=max(eligible,key=lambda i:leaves[i].cost*(rng.uniform(.5,1.5) if rng else 1));x=leaves.pop(j);leaves.extend([x.a,x.b])
    k=len(leaves);N=1<<k;full=N-1;us=[0]*N;bs=[0]*N;best=[math.inf]*N;split=[0]*N
    for s in range(1,N):
        bit=s&-s;us[s]=us[s^bit]|leaves[bit.bit_length()-1].mask
    for s in range(1,N):bs[s]=us[s]&(us[full^s]|root.mask)
    for i in range(k):best[1<<i]=0
    for s in range(1,N):
        if s&(s-1)==0:continue
        # enumerate unique unordered partitions anchored by least bit
        bit=s&-s;t=(s-1)&s;val=math.inf;pick=0
        while t:
            if t&bit:
                b=s^t;c=best[t]+best[b]+(1<<(bs[t]|bs[b]).bit_count())
                if c<val:val=c;pick=t
            t=(t-1)&s
        best[s]=val;split[s]=pick
    if best[full]+sum(t.total for t in leaves)>=root.total:return root
    def build(s):
        if s&(s-1)==0:return leaves[s.bit_length()-1]
        t=split[s];return Tree(a=build(t),b=build(s^t),mask=bs[s])
    return build(full)

def refine(scopes,ssa,passes=6,k=8,seed=0):
    root=make_tree(scopes,ssa);rng=random.Random(seed)
    for _ in range(passes):
        def visit(t):
            if t.i is not None:return t
            a,b=visit(t.a),visit(t.b)
            t=Tree(a=a,b=b,mask=t.mask)
            if t.cost>=2048 or (t.total>=8192 and rng.random()<.2):t=optimize_region(t,k,rng)
            return t
        root=visit(root)
    return schedule(scopes,tree_ssa(root,len(scopes)))

# Experimental recursive partitioner: deterministic graph spectral cuts,
# then boundary-aware local swaps. The true schedule is always re-estimated.
def partition_plan(scopes,seed=0,balance=.5):
    import numpy as np
    import scipy.sparse as sp
    from scipy.sparse.linalg import eigsh
    from scipy.sparse.csgraph import connected_components
    rng=random.Random(seed);masks=[sum(1<<v for v in s) for s in scopes];inc=collections.defaultdict(set)
    for i,s in enumerate(scopes):
        for v in s:inc[v].add(i)
    def build(ids,root_mask):
        if len(ids)==1:return Tree(i=ids[0],mask=masks[ids[0]])
        if len(ids)<=10:
            ts=[Tree(i=i,mask=masks[i]) for i in ids];a=ts[0]
            # Produce a valid initial tree inside this cluster; optimize its
            # binary contraction tree with exhaustive subset DP.
            for j,b in enumerate(ts[1:]):
                outside=root_mask
                for t in ts[j+2:]:outside|=t.mask
                a=Tree(a=a,b=b,mask=(a.mask|b.mask)&outside)
            return optimize_region(a,len(ts))
        loc={v:i for i,v in enumerate(ids)};n=len(ids);edge={v:[loc[i] for i in inc[v] if i in loc] for v in set().union(*(set(scopes[i]) for i in ids))};rows=[];cols=[];data=[]
        for v,js in edge.items():
            if len(js)>1:
                w=1/(len(js)-1)
                for i in js:
                    for j in js:
                        if i!=j:rows.append(i);cols.append(j);data.append(w)
        g=sp.csr_matrix((data,(rows,cols)),shape=(n,n));nc,lab=connected_components(g)
        if nc>1:
            order=sorted(range(n),key=lambda i:(lab[i],i))
        else:
            d=np.asarray(g.sum(axis=1)).ravel();lap=sp.diags(d)-g
            try:
                ev,vec=eigsh(lap,k=2,which='SM',tol=.005,v0=np.array([rng.uniform(-1,1) for _ in ids]));order=np.argsort(vec[:,np.argsort(ev)[1]],kind='stable').tolist()
            except Exception:order=list(range(n))
        ext={v for v in edge if root_mask>>v&1};by=[[] for _ in ids]
        for v,js in edge.items():
            for j in js:by[j].append(v)
        best=None
        for frac in (balance,.5,1-balance):
            if not .2<=frac<=.8:continue
            side=[0]*n
            for i in order[:max(1,min(n-1,round(n*frac)))]:side[i]=1
            counts={v:sum(side[i] for i in js) for v,js in edge.items()};size=sum(side)
            def cost(v,k):
                z=len(edge[v]);return (int(k>0)+int(k<z)) if v in ext else 2*int(0<k<z)
            def gain(i):
                s=1-2*side[i];return sum(cost(v,counts[v])-cost(v,counts[v]+s) for v in by[i])
            # Fixed imbalance band, greedy single-vertex FM sweeps.
            low=max(1,round(n*(frac-.08)));high=min(n-1,round(n*(frac+.08)))
            for _ in range(12):
                changed=False
                for i in sorted(range(n),key=lambda i:(-gain(i),rng.random())):
                    new=size+1-2*side[i]
                    if not low<=new<=high or gain(i)<=0:continue
                    delta=1-2*side[i]
                    for v in by[i]:counts[v]+=delta
                    side[i]^=1;size=new;changed=True
                if not changed:break
            left=[ids[i] for i in range(n) if side[i]];right=[ids[i] for i in range(n) if not side[i]]
            lm=0;rm=0
            for v,k in counts.items():
                z=len(edge[v]);bit=1<<v
                if k and (k<z or v in ext):lm|=bit
                if k<z and (k or v in ext):rm|=bit
            score=(lm|rm).bit_count()+.15*max(lm.bit_count(),rm.bit_count())+.02*abs(size-n/2)
            if best is None or score<best[0]:best=(score,left,right,lm,rm)
        _,left,right,lm,rm=best;return Tree(a=build(left,lm),b=build(right,rm),mask=root_mask)
    return tree_ssa(build(list(range(len(scopes))),0),len(scopes))
