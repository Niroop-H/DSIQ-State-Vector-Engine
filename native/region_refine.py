"""Optional native DP optimizer; scopes only, no fixture-specific paths."""
import ctypes,os,random,math,time, numpy as np
import hypergraph_plan as h
import fast_matrix as fm
class FastTree(h.Tree):
    def __init__(self,i=None,a=None,b=None,mask=0):
        super().__init__(i,a,b,mask)
        if i is None:self.cost=fm.maskcost(a.mask,b.mask,mask);self.total=self.cost+a.total+b.total

def library():
    path=os.environ.get('DSIQ_REGION_DP_LIBRARY')
    if not path:return None
    f=ctypes.CDLL(path).dsiq_region_dp;f.argtypes=[ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];f.restype=ctypes.c_int;return f
DP=library()
def fast_library():
    path=os.environ.get("DSIQ_REGION_DP_LIBRARY")
    if not path:return None
    f=ctypes.CDLL(path).dsiq_fast_dp;f.argtypes=[ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint];f.restype=ctypes.c_int;return f
FAST=fast_library();TABLE=None
def table():
    global TABLE
    if TABLE is None:
        n=32;TABLE=np.empty((n,n,n),float)
        for m in range(n):
            for k in range(n):
                for j in range(n):TABLE[m,k,j]=fm.choose(1<<m,1<<k,1<<j)[0]
    return TABLE

def optimize(root,k,rng,fast=False):
    if root.i is not None:return root
    if DP is None:return root if fast else h.optimize_region(root,min(k,10),rng)
    leaves=[root.a,root.b]
    while len(leaves)<k:
        eligible=[i for i,x in enumerate(leaves) if x.i is None]
        if not eligible:break
        j=max(eligible,key=lambda i:math.log2(max(1,leaves[i].cost))+rng.uniform(-5,5));x=leaves.pop(j);leaves.extend([x.a,x.b])
    k=len(leaves);N=1<<k;full=N-1;us=[0]*N;bs=[0]*N
    mask=0
    for t in leaves:mask|=t.mask
    labels=[]
    while mask:
        b=mask&-mask;mask^=b;labels.append(b)
    remap=lambda m:sum(1<<i for i,b in enumerate(labels) if m&b)
    lm=[remap(t.mask) for t in leaves];rm=remap(root.mask)
    for s in range(1,N):
        b=s&-s;us[s]=us[s^b]|lm[b.bit_length()-1]
    words=(len(labels)+63)//64 or 1;arr=np.zeros((N,words),np.uint64)
    for s in range(1,N):
        m=us[s]&(us[full^s]|rm);bs[s]=m
        for j in range(words):arr[s,j]=(m>>(j*64))&((1<<64)-1)
    cost=np.zeros(N,np.float64);split=np.zeros(N,np.uint32)
    if fast:
        if FAST is None:raise RuntimeError('Fast DP unavailable')
        tab=table();rc=FAST(k,words,arr.ctypes.data,cost.ctypes.data,split.ctypes.data,tab.ctypes.data,tab.shape[0])
    else:rc=DP(k,words,arr.ctypes.data,cost.ctypes.data,split.ctypes.data)
    if rc:raise RuntimeError('Region DP failed')
    if cost[full]+sum(t.total for t in leaves)>=root.total:return root
    def build(s):
        if s&(s-1)==0:return leaves[s.bit_length()-1]
        t=int(split[s]);m=bs[s];return (FastTree if fast else h.Tree)(a=build(t),b=build(s^t),mask=sum(b for i,b in enumerate(labels) if m>>i&1))
    return build(full)

def refine(scopes,steps,iterations=40,k=14,seed=0,deadline=None,target=None,fast=False):
    root=h.make_tree(scopes,[(a,b) for a,b,*_ in steps]);rng=random.Random(seed)
    if fast:
        def cv(t):return FastTree(i=t.i,mask=t.mask) if t.i is not None else FastTree(a=cv(t.a),b=cv(t.b),mask=t.mask)
        root=cv(root)
    for i in range(iterations):
        if deadline is not None and time.monotonic()>=deadline:break
        nodes=[]
        def visit(t,path):
            if t.i is None:
                nodes.append((t,path));visit(t.a,path+(0,));visit(t.b,path+(1,))
        visit(root,());nodes.sort(key=lambda x:x[0].cost,reverse=True)
        t,path=nodes[rng.randrange(min(8,len(nodes)))];path=path[:max(0,len(path)-rng.randrange(4))]
        def change(t,p):
            if not p:return optimize(t,k,rng,fast)
            a,b=(change(t.a,p[1:]),t.b) if p[0]==0 else (t.a,change(t.b,p[1:]));return (FastTree if fast else h.Tree)(a=a,b=b,mask=t.mask)
        root=change(root,path)
        if target is not None and root.total<=target:break
    return h.schedule(scopes,h.tree_ssa(root,len(scopes)))
