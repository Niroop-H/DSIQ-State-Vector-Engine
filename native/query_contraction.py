"""Experimental query-directed contraction. Exact structural rewrites; FP64
arithmetic, no truncation threshold. Does NOT assert numerical certificates.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np
import json,sys,math,time,collections,heapq,functools,argparse
import opt_einsum as oe
from opt_einsum.path_random import RandomGreedy
from bond_contract import Boundary,gate_matrix
CONTROL={'cx','cy','cz','crx','cry','crz','cp','cu'}
SINGLE={'i','h','x','y','z','s','sdg','t','tdg','rx','ry','rz','p','u'}
PARAM={'rx':('theta',),'ry':('theta',),'rz':('theta',),'p':('theta',),'u':('theta','phi','lambda'),'crx':('theta',),'cry':('theta',),'crz':('theta',),'cp':('theta',),'cu':('theta','phi','lambda')}

def validate(n,g):
    name=g['name'];q=g['q'];cs=g['controls']
    if name not in SINGLE|CONTROL|{'swap'} or type(q)!=int or not 0<=q<n or not isinstance(cs,list) or len(cs)!=int(name in CONTROL|{'swap'}) or any(type(c)!=int or c==q or not 0<=c<n for c in cs):raise ValueError('Invalid gate')
    keys={'name','q','controls'}|set(PARAM.get(name,()))
    for k in PARAM.get(name,()):
        if type(g.get(k)) not in (int,float) or not math.isfinite(g[k]) or abs(g[k])>1e6:raise ValueError('Invalid angle')
        p='pi'+k.title()
        if p in g:
            a,b=g[p];a,b=int(a),int(b)
            if b<=0 or not math.isclose(g[k],math.pi*(a/b),rel_tol=2e-15,abs_tol=0):raise ValueError('Invalid rational-pi')
            keys.add(p)
    if set(g)!=keys:raise ValueError('Unexpected fields')

def inverse(a,b):
    if a['q']!=b['q'] or a['controls']!=b['controls']:return False
    x,y=a['name'],b['name']
    if x in ('h','x','y','z','cx','cy','cz','swap'):return x==y
    if x in ('s','sdg','t','tdg'):return {'s':'sdg','sdg':'s','t':'tdg','tdg':'t'}[x]==y
    if x!=y or x not in PARAM:return False
    for k in PARAM[x]:
        kk={'phi':'lambda','lambda':'phi'}.get(k,k) if x in ('u','cu') else k
        pa,pb='pi'+k.title(),'pi'+kk.title()
        if pa in a or pb in b:
            if pa not in a or pb not in b:return False
            u,v=map(int,a[pa]);w,z=map(int,b[pb]);
            if u*z!=-w*v:return False
        elif a[k]!=-b[kk]:return False
    return True

def reduce_gates(n,gs):
    stack=[[] for _ in range(n)];live=[True]*len(gs)
    for i,g in enumerate(gs):
        if g['name']=='i':live[i]=False;continue
        wires=[g['q'],*g['controls']];old=stack[wires[0]][-1] if stack[wires[0]] else -1
        if old>=0 and all(stack[q] and stack[q][-1]==old for q in wires) and inverse(gs[old],g):
            for q in wires:stack[q].pop()
            live[old]=live[i]=False
        else:
            for q in wires:stack[q].append(i)
    return [g for g,keep in zip(gs,live) if keep]

def fuse_parity_phases(n,gs):
    """Exact CX-D-CX conjugation for any admitted diagonal target gate.
    Only adjacent operations on both involved wires may be fused. Other
    intervening operations are disjoint and commute. Global phase kept.
    """
    diagonal={'z','s','sdg','t','tdg','rz','p'};gs=list(gs);live=[True]*len(gs);stack=[[] for _ in range(n)]
    for i,g in enumerate(gs):
        q=g['q'];cs=g['controls']
        if g['name']=='cx' and len(stack[q])>=2:
            c=cs[0];j,k=stack[q][-2:];a,d=gs[j],gs[k]
            if a['name']=='cx' and a['q']==q and a['controls']==cs and d['name'] in diagonal and d['q']==q and not d['controls'] and not any(k.startswith('pi') for k in d) and stack[c] and stack[c][-1]==j:
                live[j]=live[k]=False;stack[q].pop();stack[q].pop();stack[c].pop();gs[i]=g={'name':'_parity_phase','q':q,'controls':[c],'diagonal':d}
        for v in [q,*cs]:stack[v].append(i)
    return [g for g,x in zip(gs,live) if x]

def pauli_links(net,ket,bra,pauli):
    """Identify final bra and ket variables exactly, including X/Y flips.
    Return False for impossible initial/final assignments. Values are only
    substituted on the bra indices; the mapping is injective.
    """
    mapping={b:(k,int(p in 'XY')) for k,b,p in zip(ket,bra,pauli[::-1])}
    fixed=dict(net.fixed)
    for b,(k,flip) in mapping.items():
        if b in fixed:
            v=fixed.pop(b)^flip
            if k in fixed and fixed[k]!=v:return None
            fixed[k]=v
    return mapping,fixed

class Network:
    def __init__(self,n):self.n=n;self.next=0;self.f=[];self.fixed={}
    def fresh(self):x=self.next;self.next+=1;return x
    def build(self,gs,conj=False):
        wires=[self.fresh() for _ in range(self.n)];self.fixed.update({v:0 for v in wires})
        for g in gs:
            name=g['name'];q=g['q'];cs=g['controls'];a=wires[q]
            if name=='swap':c=cs[0];wires[q],wires[c]=wires[c],wires[q];continue
            if name=='_parity_phase':
                d=g['diagonal']
                if any(k.startswith('pi') for k in d):raise Boundary('Symbolic diagonal parity phase outside path')
                v=np.diag(gate_matrix(d));v=v.conj() if conj else v
                self.f.append(((wires[cs[0]],a),np.array([[v[0],v[1]],[v[1],v[0]]])));continue
            # Never substitute a rounded binary64 angle for symbolic rational pi.
            if any(k.startswith('pi') for k in g):
                import mpmath as mp
                with mp.workdps(60):
                    t=g.get('piTheta');
                    if name=='cp' and t and not ('piPhi' in g or 'piLambda' in g):m=np.diag([1,complex(mp.exp(1j*mp.pi*int(t[0])/int(t[1])))])
                    else:raise Boundary('Symbolic angle outside experimental path')
            else:m=np.array(gate_matrix(g),complex)
            m=m.conj() if conj else m
            if m[0,1]==m[1,0]==0:
                v=np.diag(m);self.f.append(((wires[cs[0]],a),np.stack([np.ones(2),v])) if cs else ((a,),v))
            else:
                b=self.fresh();wires[q]=b
                self.f.append(((wires[cs[0]],b,a),np.stack([np.eye(2),m])) if cs else ((b,a),m))
        return wires
    def simplify(self):
        fs=self.f;fixed=self.fixed
        while True:
            new=[];updates={}
            for s,a in fs:
                if any(v in fixed for v in s):a=a[tuple(fixed.get(v,slice(None)) for v in s)];s=tuple(v for v in s if v not in fixed)
                a=np.asarray(a,dtype=complex)
                if not np.any(a):return [((),np.asarray(0j))]
                if s and np.any(a==0):
                    for i,v in enumerate(s):
                        aa=np.moveaxis(a,i,0).reshape(2,-1);allowed=np.any(aa!=0,axis=1)
                        if allowed[0]!=allowed[1]:
                            b=int(allowed[1]);
                            if v in updates and updates[v]!=b:return [((),np.asarray(0j))]
                            updates[v]=b
                new.append((s,a))
            fs=new
            if not updates:break
            fixed.update(updates)
        merged={}
        for s,a in fs:
            k=tuple(sorted(s));a=a.transpose(tuple(s.index(v) for v in k)) if k!=s else a
            if k in merged:
                with np.errstate(under='raise',over='raise',invalid='raise'):merged[k]=merged[k]*a
            else:merged[k]=a.copy()
        return list(merged.items())

def cone(n,gs,pauli):
    # Track a conservative algebra class per wire: identity, diagonal, or
    # general. This is stronger than an undifferentiated connectivity cone.
    # A diagonal two-wire gate commutes with any operator diagonal on both
    # wires, including correlated diagonal operators. When it touches a
    # general operator on one wire, the other wire remains diagonal.
    I,D,G=0,1,2
    kinds=[I if p=='I' else D if p=='Z' else G for p in pauli[::-1]];keep=[]
    diagonal={'z','s','sdg','t','tdg','rz','p','cz','cp','crz','_parity_phase'}
    for g in reversed(gs):
        q=g['q'];cs=g['controls'];name=g['name'];t=kinds[q]
        if not cs:
            if t==I or name=='i' or (t==D and name in diagonal):continue
            keep.append(g)
            if t==D and name not in ('x','y'):kinds[q]=G
            continue
        c=cs[0];u=kinds[c]
        if t==I and u==I:continue
        if name=='swap':keep.append(g);kinds[q],kinds[c]=u,t;continue
        if name in diagonal:
            if max(t,u)<G:continue
            keep.append(g);kinds[q]=max(t,D);kinds[c]=max(u,D);continue
        # Controlled non-diagonal gate commutes with a control-diagonal
        # operator that is identity on the target. Otherwise its block
        # structure preserves control diagonality unless already general.
        if u<G and t==I:continue
        keep.append(g)
        if u<G:kinds[c]=D;kinds[q]=D if t==D and name in ('cx','cy') else G
        else:kinds[c]=G;kinds[q]=G
    return list(reversed(keep))

class Budget:
    def __init__(self,mb,mw,mn):self.mb=mb;self.mw=mw;self.mn=mn;self.work=0;self.peak=0;self.rank=0;self.steps=0
    def charge(self,w,b,rank):
        if self.work+int(w)>self.mw:raise Boundary(f'Contraction work budget: {self.work+int(w)}>{self.mw}')
        if b>self.mb:raise Boundary(f'Contraction array budget: {b}>{self.mb}')
        if 2**rank>self.mn*64:raise Boundary(f'Contraction separator budget: rank {rank}')
        self.work+=int(w);self.peak=max(self.peak,int(b));self.rank=max(self.rank,rank)
    def stats(self):return dict(workUnits=self.work,peakExplicitBytes=self.peak,maxSeparator=self.rank,contractions=self.steps)

@functools.lru_cache(maxsize=64)
def variable_plan(scopes,variant=0):
    """Forecast complete separator sequence before allocating any large tensor."""
    fs={i:set(q) for i,q in enumerate(scopes) if q};uid=len(scopes);links=collections.defaultdict(set);live=sum(2**len(q) for q in fs.values());peak=live;work=0;rank=0;order=[]
    for i,q in fs.items():
        for v in q:links[v].add(i)
    def key(v):
        ids=links[v];u=set().union(*(fs[i] for i in ids));w=len(u)
        # Min-fill is used only for moderate neighbor sets, avoiding unbounded
        # planner work on dense hypergraphs.
        fill=0
        if variant in (1,3) and w<=32:
            ns=u-{v};fill=sum(1 for a in ns for b in ns if a<b and not (links[a]&links[b]))
        elif variant in (1,3):fill=w*w
        tie=v if variant<2 else ((v*2654435761+1013904223)&0xffffffff)
        return ((fill,w,len(ids),tie,v) if variant in (1,3) else (w,len(ids),tie,v))
    heap=[key(v) for v in links];heapq.heapify(heap)
    while links:
        while heap:
            k=heapq.heappop(heap);v=k[-1]
            if v in links and key(v)==k:break
        else:raise RuntimeError('Planner inconsistency')
        ids=sorted(links[v]);ss=[fs[i] for i in ids];scope=set().union(*ss)-{v};r=len(scope)+1
        # No useful plan at the permitted memory size can have such a rank.
        if r>40:return (math.inf,math.inf,r,())
        work+=(1<<r)*max(1,len(ids));peak=max(peak,live+3*(1<<r)+(1<<len(scope)));rank=max(rank,r);order.append(v)
        affected=set(scope)
        if variant in (1,3):
            for w in scope:affected.update(set().union(*(fs[i] for i in links[w])))
        for i,a in zip(ids,ss):
            del fs[i];live-=2**len(a)
            for w in a:links[w].discard(i)
        del links[v]
        if scope:
            fs[uid]=scope;live+=2**len(scope)
            for w in scope:links[w].add(uid)
            uid+=1
        for w in affected:
            if w in links:heapq.heappush(heap,key(w))
    return work,peak,rank,tuple(order)

def choose_variable(scopes,budget,cert=False):
    mult=16 if cert else 1;item=48 if cert else 16;factor=4 if cert else 1
    plans=[]
    for variant in range(4):
        p=variable_plan(scopes,variant);plans.append(p)
        if p[0]*mult+budget.work<=budget.mw and p[1]*item*factor<=budget.mb and 2**p[2]<=budget.mn*64:
            if variant==0:return p
    return min((p for p in plans if p[0]*mult+budget.work<=budget.mw and p[1]*item*factor<=budget.mb and 2**p[2]<=budget.mn*64),key=lambda p:p[0],default=None)

def variable_contract(raw,budget,order_plan=None):
    fs={i:(tuple(s),np.asarray(a)) for i,(s,a) in enumerate(raw)};uid=len(fs);links=collections.defaultdict(set);live=0;scalar=1+0j;exp=0
    def normalize(a):
        m=float(np.max(np.abs(a)))
        if not math.isfinite(m):raise Boundary('Nonfinite tensor')
        if not m:return a,0
        _,e=math.frexp(m);e-=1
        # ldexp separately avoids an overflowing reciprocal on subnormals.
        b=np.ldexp(a.real,-e)+1j*np.ldexp(a.imag,-e)
        if np.any((a!=0)&(b==0)):raise Boundary('Tensor scaling underflow')
        return b,e
    for i,(s,a) in list(fs.items()):
        a,e=normalize(a);exp+=e
        if not s:
            scalar*=complex(a);scalar,k=normalize(np.asarray(scalar));scalar=complex(scalar);exp+=k;del fs[i];continue
        fs[i]=(s,a);live+=a.nbytes
        for v in s:links[v].add(i)
    if scalar==0:return scalar
    if order_plan is None:
        plan=choose_variable(tuple(s for s,a in raw if s),budget)
        if plan is None:raise Boundary('No feasible variable elimination plan')
        order_plan=plan[3]
    for v in order_plan:
        ids=sorted(links[v]);t=[fs[i] for i in ids];scope=tuple(sorted(set().union(*(s for s,a in t))-{v}));rank=len(scope)+1
        budget.charge((1<<rank)*max(1,len(ids)),live+16*((1<<rank)*3+(1<<len(scope))),rank)
        full=scope+(v,);array=None
        for s,a in t:
            order=tuple(sorted(range(len(s)),key=lambda i:full.index(s[i])));x=a.transpose(order);ss=[s[i] for i in order];x=x.reshape(tuple(2 if w in ss else 1 for w in full));array=x if array is None else array*x
        res,e=normalize(array.sum(axis=-1));exp+=e;budget.steps+=1
        for i,(s,a) in zip(ids,t):
            del fs[i];live-=a.nbytes
            for w in s:links[w].discard(i)
        del links[v]
        if scope:
            fs[uid]=(scope,res);live+=res.nbytes
            for w in scope:links[w].add(uid)
            uid+=1
        else:
            scalar*=complex(res);scalar,e=normalize(np.asarray(scalar));scalar=complex(scalar);exp+=e
    if links:raise RuntimeError('Incomplete variable contraction plan')
    return complex(math.ldexp(scalar.real,exp),math.ldexp(scalar.imag,exp))

@functools.lru_cache(maxsize=64)
def pair_plan(scopes):
    inputs=[frozenset(s) for s in scopes];sizes={v:2 for s in scopes for v in s}
    # Bounded portfolio, seeded by opt_einsum repeat number. No reference access.
    opts=[oe.paths.greedy(inputs,frozenset(),sizes)]
    for criterion in ('size','flops'):
        opts.append(RandomGreedy(max_repeats=40,max_time=1.5,minimize=criterion)(inputs,frozenset(),sizes))
    def estimate(path):
        ss=[set(s) for s in scopes];live=sum(16*2**len(s) for s in ss);peak=live;work=0;rank=0;steps=[]
        for ix in path:
            ix=tuple(sorted(ix));a=[ss[i] for i in ix];remain=[s for i,s in enumerate(ss) if i not in ix];union=set().union(*a);out=union&set().union(*remain);size=2**len(out);ins=sum(2**len(s) for s in a)
            peak=max(peak,live+16*(2*ins+2*size));work+=2**len(union)*max(1,len(ix)-1);rank=max(rank,len(out));steps.append((ix,tuple(sorted(out)),work,peak,rank));ss=remain+[out];live+=16*(size-ins)
        return work,peak,rank,steps
    return sorted((estimate(p) for p in opts),key=lambda p:(p[1]>2**29,p[0],p[1]))

def pair_contract(raw,budget):
    arrays=[];scopes=[];scale=0;scalar=1+0j
    def norm(a):
        nonlocal scale
        m=float(np.max(np.abs(a)))
        if not math.isfinite(m):raise Boundary('Nonfinite tensor')
        if m==0:return a
        _,e=math.frexp(m);e-=1;scale+=e
        b=np.ldexp(a.real,-e)+1j*np.ldexp(a.imag,-e)
        if np.any((a!=0)&(b==0)):raise Boundary('Tensor scaling underflow')
        return b
    for s,a in raw:
        a=norm(a)
        if not s:
            scalar=complex(norm(np.asarray(scalar*complex(a))))
            if scalar==0:return 0j
        else:scopes.append(s);arrays.append(a)
    if not scopes:return complex(math.ldexp(scalar.real,scale),math.ldexp(scalar.imag,scale))
    # Reduce to scalar even for a single tensor.
    if len(scopes)==1:
        budget.charge(arrays[0].size,arrays[0].nbytes*2,len(scopes[0]));z=scalar*complex(arrays[0].sum());return complex(math.ldexp(z.real,scale),math.ldexp(z.imag,scale))
    plans=pair_plan(tuple(scopes));chosen=next((p for p in plans if p[0]+budget.work<=budget.mw and p[1]<=budget.mb and 2**p[2]<=budget.mn*64),None)
    if chosen is None:raise Boundary('No feasible pair contraction plan: '+str([(p[0],p[1],p[2]) for p in plans]))
    work,peak,rank,steps=chosen;budget.charge(work,peak,rank)
    for ix,out,_,_,_ in steps:
        operands=[];labels=sorted(set().union(*(set(scopes[i]) for i in ix)));mapping={v:j for j,v in enumerate(labels)}
        for i in ix:operands.extend((arrays[i],[mapping[v] for v in scopes[i]]))
        operands.append([mapping[v] for v in out]);z=norm(oe.contract(*operands,optimize='greedy'))
        arrays=[a for i,a in enumerate(arrays) if i not in ix]+[z];scopes=[s for i,s in enumerate(scopes) if i not in ix]+[out];budget.steps+=1
    if len(arrays)!=1 or scopes[0]:raise RuntimeError('Incomplete contraction plan')
    z=scalar*complex(arrays[0]);return complex(math.ldexp(z.real,scale),math.ldexp(z.imag,scale))

def contract(raw,budget):
    plan=choose_variable(tuple(s for s,a in raw if s),budget)
    if plan is not None:return variable_contract(raw,budget,plan[3])
    before=budget.work
    try:return pair_contract(raw,budget)
    except Boundary:
        # Never refund computation already spent. The stronger path may be
        # entered only when the earlier path rejected before charging work.
        if budget.work!=before or not os.environ.get('DSIQ_REGION_DP_LIBRARY'):raise
        import pairwise_query as pair
        return pair.optimized_execute(raw,budget)

def evaluate(n,gs,q,budget):
    gs=fuse_parity_phases(n,reduce_gates(n,gs));kind=q['kind'];net=Network(n)
    if kind=='amplitude':
        wires=net.build(gs);bits=q['bits'][::-1]
        for v,b in zip(wires,bits):
            b=int(b)
            if v in net.fixed and net.fixed[v]!=b:return 0j,dict(reducedGates=len(gs))
            net.fixed[v]=b
    elif kind in ('pauli','norm'):
        pauli=q.get('pauli','I'*n)
        if kind=='pauli':gs=cone(n,gs,pauli)
        ket=net.build(gs);bra=net.build(gs,True)
        pmap=pauli_links(net,ket,bra,pauli)
        if pmap is None:return 0j,dict(reducedGates=len(gs))
        mapping,net.fixed=pmap;fs=[]
        for scope,a in net.f:
            for i,v in enumerate(scope):
                if v in mapping and mapping[v][1]:a=np.flip(a,axis=i)
            fs.append((tuple(mapping.get(v,(v,0))[0] for v in scope),a))
        net.f=fs
        for k,p in zip(ket,pauli[::-1]):
            if p in 'YZ':net.f.append(((k,),np.asarray([1j,-1j] if p=='Y' else [1,-1],dtype=complex)))
    else:raise ValueError('Unsupported query')
    z=contract(net.simplify(),budget)
    return z,dict(reducedGates=len(gs),**budget.stats())

def read_request():
    raw=sys.stdin.buffer.read(32*2**20+1)
    if len(raw)>32*2**20:raise ValueError('Request too large')
    r=json.loads(raw,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    if set(r)-{'n','gates','queries','method','requireCertificate','checkpointEvery','maxBytes','maxWork','maxNodes'}:raise ValueError('Unexpected request fields')
    n=r['n'];gs=r['gates'];qs=r['queries']
    if type(n)!=int or not 1<=n<=4096 or not isinstance(gs,list) or len(gs)>100000 or not isinstance(qs,list) or not 1<=len(qs)<=10000:raise ValueError('Invalid request sizes')
    for k,lo,hi,default in [('maxBytes',256,536870912,67108864),('maxWork',1,1000000000,50000000),('maxNodes',n+1,1000000,32768),('checkpointEvery',1,100000,1)]:
        v=r.get(k,default)
        if type(v)!=int or not lo<=v<=hi:raise ValueError('Invalid budget '+k)
    method=r.get('method','certified-auto');cert=r.get('requireCertificate',True)
    if method not in ('adaptive','contracted','certified-auto','certified-factor','certified-contraction') or type(cert)!=bool or cert and not method.startswith('certified-'):raise ValueError('Invalid method or certificate flag')
    for g in gs:validate(n,g)
    ids=set()
    for q in qs:
        kind=q.get('kind');i=q.get('id');p=q.get('prefix');field={'amplitude':'bits','pauli':'pauli'}.get(kind)
        if kind not in ('amplitude','pauli','norm') or not isinstance(i,str) or not 1<=len(i)<=128 or i in ids or type(p)!=int or not 0<=p<=len(gs) or set(q)!={'kind','id','prefix'}|({field} if field else set()):raise ValueError('Invalid query')
        ids.add(i)
        if field and (not isinstance(q[field],str) or len(q[field])!=n or set(q[field])-set('01' if kind=='amplitude' else 'IXYZ')):raise ValueError('Invalid query operands')
    return r

def main():
    p=argparse.ArgumentParser();p.add_argument('--diagnostic-uncertified',action='store_true');p.add_argument('--measure-norms',action='store_true');args=p.parse_args()
    r=read_request();n=r['n'];gs=r['gates']
    if r.get('requireCertificate',True) and not args.diagnostic_uncertified:raise Boundary('Strict request rejected by uncertified numerical path')
    budget=Budget(r.get('maxBytes',67108864),r.get('maxWork',50000000),r.get('maxNodes',32768));out=[]
    for q in sorted(r['queries'],key=lambda q:q['prefix']):
        start=time.monotonic()
        try:
            if q['kind']=='norm' and not args.measure_norms:z=1.;stats={'normEvidence':'analytic-unitarity-not-measured'}
            else:
                z,stats=evaluate(n,gs[:q['prefix']],q,budget)
                if q['kind']=='norm':stats['normEvidence']='double-layer-state-contraction-after-exact-rewrites'
            v={'real':float(np.real(z)),'imag':float(np.imag(z))}
            if not all(math.isfinite(x) for x in v.values()):raise Boundary('Nonfinite output')
            rec={'id':q['id'],'kind':q['kind'],'prefix':q['prefix'],'value':v,'stats':stats,'elapsedSeconds':time.monotonic()-start,'certified':False}
        except (Boundary,MemoryError,ValueError,OverflowError,FloatingPointError) as e:rec={'id':q['id'],'kind':q['kind'],'prefix':q['prefix'],'error':str(e),'elapsedSeconds':time.monotonic()-start}
        print(json.dumps(rec,allow_nan=False),flush=True);out.append(rec)
    return int(any('error' in x for x in out))
if __name__=='__main__':
    try:sys.exit(main())
    except (Boundary,ValueError,KeyError,TypeError,MemoryError,OverflowError) as e:print('DSIQ native boundary: '+str(e),file=sys.stderr);sys.exit(2)
