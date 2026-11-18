"""DSIQ native-host bond contraction. NumPy supplies numeric BLAS, not a simulator.
All bond assignments contracted, no SVD or deliberate pruning. Amplitude queries.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import numpy as np
import heapq,random,math,json,sys,time
class Boundary(RuntimeError): pass

def gate_matrix(g):
    t=g.get('theta',0) or 0; name=g['name']; c=math.cos(t/2); s=math.sin(t/2)
    if name=='i': return np.eye(2)
    if name=='h': return np.array([[1.,1.],[1.,-1.]])/math.sqrt(2)
    if name in ('x','cx'): return np.array([[0.,1.],[1.,0.]])
    if name in ('y','cy'): return np.array([[0,-1j],[1j,0]])
    if name in ('z','cz'): return np.diag([1.,-1.])
    if name in ('ry','cry'): return np.array([[c,-s],[s,c]])
    if name in ('rx','crx'): return np.array([[c,-1j*s],[-1j*s,c]])
    if name in ('rz','crz'): return np.diag([complex(c,-s),complex(c,s)])
    if name in ('p','cp','t','tdg','s','sdg'):
        if name in ('s','sdg'):return np.diag([1,1j if name=='s' else -1j])
        t={'t':math.pi/4,'tdg':-math.pi/4}.get(name,t)
        return np.diag([1,complex(math.cos(t),math.sin(t))])
    if name in ('u','cu'):
        p,l=g['phi'],g['lambda']; a=complex(math.cos(p),math.sin(p)); b=complex(math.cos(l),math.sin(l)); return np.array([[c,-s*b],[s*a,c*a*b]])
    raise Boundary('Unsupported bond gate: '+name)

def compile_network(n,gates,bits):
    if not isinstance(n,int) or not 1<=n<=4096 or len(bits)!=n or set(bits)-set('01'):raise ValueError('Invalid register or query')
    if len(gates)>100000:raise Boundary('Gate count limit')
    nodes=[]; edges=[None]*n; pending=[np.eye(2) for _ in range(n)]; nxt=0
    def fresh():
        nonlocal nxt
        a=nxt;nxt+=1;return a
    def attach(q,parts,bond):
        a=edges[q];b=fresh(); p=pending[q]
        T=np.stack([m@p for m in parts],axis=-1)
        if a is None:T=T[:,0,:];scope=[b,bond]
        else:scope=[b,a,bond]
        nodes.append((tuple(scope),T));edges[q]=b;pending[q]=np.eye(2)
    for g in gates:
        q=g['q']; controls=g['controls']; name=g['name']
        if not isinstance(q,int) or q<0 or q>=n or any(not isinstance(c,int) or c<0 or c>=n or c==q for c in controls) or len(set(controls))!=len(controls):raise ValueError('Invalid gate operands')
        if name=='swap':
            if len(controls)!=1:raise ValueError('Invalid SWAP')
            c=controls[0]; edges[q],edges[c]=edges[c],edges[q];pending[q],pending[c]=pending[c],pending[q];continue
        controlled={'cx','cy','cz','crx','cry','crz','cp','cu'}
        if len(controls)!=int(name in controlled):raise Boundary('Only one-wire and singly controlled gates admitted')
        if name in {'ry','rx','rz','p','cry','crx','crz','cp','u','cu'} and not (isinstance(g.get('theta'),(float,int)) and math.isfinite(g['theta'])):raise ValueError('Invalid angle')
        m=gate_matrix(g)
        if not np.all(np.isfinite(m)):raise ValueError('Nonfinite matrix')
        if not controls:pending[q]=m@pending[q];continue
        c=controls[0]; bond=fresh();attach(c,[np.diag([1.,0.]),np.diag([0.,1.])],bond);attach(q,[np.eye(2),m],bond)
    for q in range(n):
        a=edges[q];v=pending[q][int(bits[n-1-q]),:]
        nodes.append((() if a is None else (a,),np.asarray(v[0] if a is None else v)))
    dtype=np.complex128 if any(np.iscomplexobj(a) for _,a in nodes) else np.float64
    return [(s,np.asarray(a,dtype=dtype).reshape((2,)*len(s))) for s,a in nodes],np.dtype(dtype).itemsize

def compile_compact(n,gates,bits):
    # Validation and exact matrices as above; control wire retains its index.
    if not isinstance(n,int) or not 1<=n<=4096 or len(bits)!=n or set(bits)-set('01') or len(gates)>100000:raise ValueError('Invalid input')
    wires=list(range(n));fixed={q:0 for q in wires};nxt=n;raw=[]
    controlled={'cx','cy','cz','crx','cry','crz','cp','cu'}
    for g in gates:
        q=g['q'];cs=g['controls'];name=g['name']
        if not isinstance(q,int) or q<0 or q>=n or any(not isinstance(c,int) or not 0<=c<n or c==q for c in cs) or len(set(cs))!=len(cs):raise ValueError('Invalid operands')
        if name=='swap':
            if len(cs)!=1:raise ValueError('Invalid SWAP')
            c=cs[0];wires[q],wires[c]=wires[c],wires[q];continue
        if len(cs)!=int(name in controlled):raise Boundary('Unsupported controlled gate')
        if name in {'ry','rx','rz','p','cry','crx','crz','cp','u','cu'} and not (isinstance(g.get('theta'),(float,int)) and math.isfinite(g['theta'])):raise ValueError('Invalid angle')
        m=gate_matrix(g); a=wires[q]
        if not np.all(np.isfinite(m)):raise ValueError('Nonfinite matrix')
        diag=m[0,1]==0 and m[1,0]==0
        if diag:
            v=np.diag(m);raw.append(((wires[cs[0]],a),np.stack([np.ones(2),v])) if cs else ((a,),v))
        else:
            b=nxt;nxt+=1;wires[q]=b
            raw.append(((wires[cs[0]],b,a),np.stack([np.eye(2),m])) if cs else ((b,a),m))
    for q,v in enumerate(wires):
        b=int(bits[n-1-q])
        if v in fixed and fixed[v]!=b:return [((),np.asarray(0.))],8
        fixed[v]=b
    dtype=np.complex128 if any(np.iscomplexobj(a) for _,a in raw) else np.float64
    # Propagate only exact zeros in constraints. If a variable has just one
    # possible value in any factor, conditioning it is an algebraic identity.
    while True:
        fs=[];updates={}
        for scope,a in raw:
            sel=tuple(fixed.get(v,slice(None)) for v in scope);t=np.asarray(a[sel],dtype=dtype);s=tuple(v for v in scope if v not in fixed)
            if not np.any(t):return [((),np.asarray(0.,dtype=dtype))],np.dtype(dtype).itemsize
            for i,v in enumerate(s):
                allowed=[np.any(np.take(t,k,axis=i)) for k in (0,1)]
                if allowed[0]!=allowed[1]:
                    b=int(allowed[1]);
                    if v in updates and updates[v]!=b:return [((),np.asarray(0.,dtype=dtype))],np.dtype(dtype).itemsize
                    updates[v]=b
            fs.append((s,t))
        raw=fs
        if not updates:break
        fixed.update(updates)
    # Singleton wires represent exact summation, not an implicit projection.
    return raw,np.dtype(dtype).itemsize

def eliminate_affine(raw,max_arity=8):
    """Eliminate exact 0/1 XOR constraints locally, choosing sparse pivots.
    No numerical value threshold. Dense factor tables remain explicit; if
    substitution would exceed arity budget, retain the constraint as a tensor.
    """
    allvars={v for scope,_ in raw for v in scope};eqs=[];fs=[];pivots=set();largest=0
    for scope,a in raw:
        flat=a.reshape(-1)
        if scope and len(scope)<=max_arity and np.all((flat==0)|(flat==1)):
            rhs=int(flat[0]==0)
            if all(int(flat[j].real)==int((j.bit_count()&1)==rhs) for j in range(len(flat))):eqs.append((set(scope),rhs));continue
        fs.append((scope,a))
    original=len(eqs)
    while eqs:
        chosen=None;score=None
        for j,(eq,rhs) in enumerate(eqs):
            if not eq:
                if rhs:return [((),np.asarray(0.))],dict(affineConstraints=original,affinePivots=len(pivots),affineConflict=True)
                continue
            for v in eq:
                rest=eq-{v};affected=[s for s,_ in fs if v in s];widths=[len((set(s)-{v})|rest) for s in affected];other=[len(e^eq) for k,(e,_) in enumerate(eqs) if k!=j and v in e];maxw=max(widths+other+[0]);
                if maxw>max_arity:continue
                w=(maxw,sum(2**t for t in widths)+sum(2**t for t in other)-sum(2**len(s) for s in affected),len(affected)+len(other),len(eq),v)
                if score is None or w<score:chosen=(j,v);score=w
        if chosen is None:break
        j,v=chosen;eq,rhs=eqs.pop(j);rest=eq-{v};pivots.add(v);new=[]
        for scope,a in fs:
            if v not in scope:new.append((scope,a));continue
            out=tuple(sorted((set(scope)-{v})|rest));largest=max(largest,len(out));ids={w:i for i,w in enumerate(out)};xs=np.arange(1<<len(out),dtype=np.uint32);b={w:(xs>>(len(out)-1-i))&1 for w,i in ids.items()};p=np.full(xs.shape,rhs,dtype=np.uint32)
            for w in rest:p^=b[w]
            a=a[tuple(p if w==v else b[w] for w in scope)].reshape((2,)*len(out));new.append((out,a))
        fs=new;eqs=[(e^eq,r^rhs) if v in e else (e,r) for e,r in eqs]
    for e,rhs in eqs:
        if not e:
            if rhs:return [((),np.asarray(0.))],dict(affineConstraints=original,affinePivots=len(pivots),affineConflict=True)
            continue
        s=tuple(sorted(e));a=np.array([int((j.bit_count()&1)==rhs) for j in range(1<<len(s))],dtype=np.float64).reshape((2,)*len(s));fs.append((s,a))
    absent=allvars-pivots-{v for s,a in fs for v in s}
    for _ in absent:fs.append(((),np.asarray(2.)))
    return fs,dict(affineConstraints=original,affinePivots=len(pivots),affineMaxArity=largest,freeUnweightedVariables=len(absent))

def hyperplan(scopes,itemsize,trials=128,seed=873,planner_seconds=20):
    best=None;start=time.monotonic();completed=0
    for k in range(trials):
        if k and time.monotonic()-start>planner_seconds:break
        rng=random.Random(seed+k*1777);active={i:set(s) for i,s in enumerate(scopes) if s};links={};heap=[];uid=len(scopes);steps=[];live=sum(itemsize*2**len(s) for s in active.values());peak=live;products=0;rank=0
        for i,s in active.items():
            for v in s:links.setdefault(v,set()).add(i)
        def option(a,b):
            x=active[a];y=set() if b is None else active[b];u=x|y;drop={v for v in u if links[v]<={a,b}};out=u-drop;return x,y,u,out
        def offer(a,b):
            if a==b:return
            if b is not None and b<a:a,b=b,a
            x,y,u,out=option(a,b);w=len(out);s=len(u)
            if b is None and w==s:return
            coeff=[.05,.15,.3,.6,1.0,.0,.45,.08][k%8];noise=0 if not k else rng.random()*(.25+(k%7)*.35)
            heapq.heappush(heap,(w+coeff*s-.07*max(len(x),len(y))+noise,a,-1 if b is None else b))
        def neighbors(a):
            offer(a,None)
            for b in set.union(*(links[v] for v in active[a]))-{a}:offer(a,b)
        for a in active:neighbors(a)
        while active:
            while heap:
                _,a,b=heapq.heappop(heap);b=None if b==-1 else b
                if a not in active or b is not None and (b not in active or not active[a]&active[b]):continue
                x,y,u,out=option(a,b)
                if b is None and out==u:continue
                break
            else:raise RuntimeError('No contraction option')
            A=itemsize*2**len(x);B=itemsize*2**len(y) if b is not None else 0;C=itemsize*2**len(out);peak=max(peak,live+A+B+3*C);products+=2**len(u);rank=max(rank,len(out));steps.append((a,b,uid,tuple(sorted(out))))
            affected=set()
            for v in u:
                e=links[v];e.discard(a);e.discard(b)
                if v not in out:del links[v]
                else:e.add(uid);affected.update(e)
            del active[a]
            if b is not None:del active[b]
            live-=A+B
            if out:active[uid]=out;live+=C
            # Any pair sharing an affected variable can have a changed retirement set.
            for i in affected:
                if i in active:neighbors(i)
            uid+=1
            if best and peak>best['predictedArrayBytes'] and products>best['products']:break
        if not active:
            completed+=1;p=dict(steps=steps,predictedArrayBytes=peak,products=products,maxOutputRank=rank,trial=k)
            if best is None or (peak,products)<(best['predictedArrayBytes'],best['products']):best=p
    if best is None:raise Boundary('No compact plan')
    return dict(best,completeTrials=completed,planningSeconds=time.monotonic()-start)

def plan(scopes,itemsize,trials=64,seed=873,planner_seconds=15):
    if not 1<=trials<=1024:raise ValueError('Invalid trials')
    best=None; start=time.monotonic(); completed=0
    for k in range(trials):
        if k and time.monotonic()-start>planner_seconds:break
        rand=random.Random(seed+k*1777); active={i:set(s) for i,s in enumerate(scopes) if s}; edges={}; heap=[]; steps=[]; uid=len(scopes); live=sum(itemsize*2**len(s) for s in active.values()); peak=live; flops=0; maxwidth=0
        for i,s in active.items():
            for v in s:edges.setdefault(v,set()).add(i)
        if any(len(a)!=2 for a in edges.values()):raise ValueError('Bond network must have degree-two indices')
        def offer(a,b):
            if a==b:return
            x,y=active[a],active[b]; w=len(x^y); u=len(x|y)
            coeff=[.10,.30,.60,1.0,.15,.05,.4,.2][k%8]; jitter=0 if k==0 else rand.random()*(.7+(k%5)*.3)
            score=w+coeff*u-.08*max(len(x),len(y))+jitter
            heapq.heappush(heap,(score,min(a,b),max(a,b)))
        for a,b in edges.values():offer(a,b)
        while active:
            while heap:
                _,a,b=heapq.heappop(heap)
                if a in active and b in active and active[a]&active[b]:break
            else:raise ValueError('Disconnected unfinished component')
            x,y=active[a],active[b]; out=x^y; shared=x&y; A=itemsize*2**len(x);B=itemsize*2**len(y);C=itemsize*2**len(out)
            # Copies, output and normalization scratch; BLAS/OS overhead separate.
            peak=max(peak,live+A+B+3*C); flops+=2**len(x|y);maxwidth=max(maxwidth,len(out));steps.append((a,b,uid))
            for v in x|y:
                e=edges[v];e.discard(a);e.discard(b)
                if v in shared:del edges[v]
                else:e.add(uid)
            del active[a],active[b];live-=A+B
            if out:
                active[uid]=out;live+=C
                for j in set.union(*(edges[v] for v in out))-{uid}:offer(uid,j)
            uid+=1
            if best and peak>best['predictedArrayBytes'] and flops>best['products']:break
        if not active:
            completed+=1; p=dict(steps=steps,predictedArrayBytes=peak,products=flops,maxOutputRank=maxwidth,trial=k)
            if best is None or (peak,flops)<(best['predictedArrayBytes'],best['products']):best=p
    if best is None:raise Boundary('No complete planning order')
    return dict(best,completeTrials=completed,planningSeconds=time.monotonic()-start)

def execute(n,gates,bits,max_bytes=512*1024**2,max_products=2**36,trials=64,seed=873,plan_only=False,representation="compact"):
    if not isinstance(max_bytes,int) or max_bytes<1024 or max_bytes>2*1024**3 or not isinstance(max_products,int) or not 1<=max_products<=2**42:raise ValueError('Invalid limits')
    if representation not in ("compact","bond","affine"):raise ValueError("Invalid representation")
    start=time.monotonic();raw,itemsize=(compile_compact if representation!="bond" else compile_network)(n,gates,bits);algebra={}
    if representation=="affine":raw,algebra=eliminate_affine(raw)
    p=(hyperplan if representation!="bond" else plan)([s for s,a in raw],itemsize,trials,seed);stats={k:v for k,v in p.items() if k!='steps'};stats.update(gates=len(gates),qubits=n,factors=len(raw),coefficientType='real64' if itemsize==8 else 'complex128',mode='bond-contraction',representation=representation,**algebra)
    if plan_only:return stats
    if p['predictedArrayBytes']>max_bytes or p['products']>max_products:raise Boundary('Predicted budget exceeded: '+json.dumps(stats))
    fs={}; scale=0; scalar=1.
    def normalized(a):
        m=float(np.max(np.abs(a)))
        if not math.isfinite(m):raise Boundary('Nonfinite tensor')
        if not m:return a,0
        _,exp=math.frexp(m); exp-=1
        b=a/math.ldexp(1.,exp)
        if np.any((a!=0)&(b==0)):raise Boundary('Tensor scaling underflow')
        return b,exp
    def insert(i,s,a,e=0):
        nonlocal scalar,scale
        a,k=normalized(a);e+=k
        if s:fs[i]=(s,a,e)
        else:
            z=scalar*a.item()
            if scalar!=0 and a.item()!=0 and z==0:raise Boundary('Scalar underflow')
            b,k=normalized(np.asarray(z));scalar=b.item();scale+=e+k
    for i,(s,a) in enumerate(raw):insert(i,s,a)
    del raw
    for step in p['steps']:
        i,j,k=step[:3];sa,a,ea=fs.pop(i)
        if j is None:sb=();b=None;eb=0
        else:sb,b,eb=fs.pop(j)
        if representation!="bond":
            scope=step[3];u=sorted(set(sa)|set(sb));ids={v:i for i,v in enumerate(u)}
            if len(u)>52:raise Boundary('Einsum label limit')
            args=[a,[ids[v] for v in sa]]
            if b is not None:args.extend([b,[ids[v] for v in sb]])
            c=np.einsum(*args,[ids[v] for v in scope],optimize=True)
        else:
            shared=sorted(set(sa)&set(sb));scope=tuple(x for x in sa if x not in shared)+tuple(x for x in sb if x not in shared);c=np.tensordot(a,b,axes=([sa.index(x) for x in shared],[sb.index(x) for x in shared]))
        del a,b;insert(k,scope,c,ea+eb);del c
    if fs:raise RuntimeError('Incomplete plan')
    value=complex(scalar);mag=abs(value);re=math.ldexp(value.real,scale) if value.real else 0.;im=math.ldexp(value.imag,scale) if value.imag else 0.
    if not math.isfinite(re) or not math.isfinite(im):raise Boundary('Nonfinite output')
    return dict(stats,real=re,imag=im,log2Magnitude=math.log2(mag)+scale if mag else None,phase=math.atan2(value.imag,value.real) if mag else 0.,binaryExponent=scale,scaledMantissa=[value.real,value.imag],elapsedSeconds=time.monotonic()-start,componentUnderflow=bool(value.real and not re or value.imag and not im),precision='Float64 BLAS; all bond indices contracted; no deliberate truncation; numerical rounding and underflow possible')
if __name__=='__main__':
    try:print(json.dumps(execute(**json.load(sys.stdin)),allow_nan=False))
    except (Boundary,ValueError,OverflowError) as e:print(json.dumps({'error':str(e)}));sys.exit(2)
