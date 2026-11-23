"""Exact-assignment slicing of an affine/compact tensor network.
All binary assignments are evaluated. Float64 tensor arithmetic with scaled
outputs; summation of represented slice contributions uses exact rationals.
The projected array model excludes allocator, Python, and BLAS workspaces.
"""
import math, time, json, sys, itertools
try:
    import resource
except ImportError:
    resource = None
from fractions import Fraction
import numpy as np
from bond_contract import compile_compact, eliminate_affine, hyperplan, Boundary

def projected(scopes,steps,cut,itemsize):
    active={i:set(s)-cut for i,s in enumerate(scopes) if s};live=sum(itemsize*(1<<len(s)) for s in active.values());peak=live;products=0;heavy=set();rank=0
    for i,j,k,out0 in steps:
        a=active.pop(i);b=active.pop(j) if j is not None else set();u=a|b;out=set(out0)-cut
        A=itemsize*(1<<len(a));B=itemsize*(1<<len(b)) if j is not None else 0;C=itemsize*(1<<len(out));p=live+A+B+3*C
        if p>peak:peak=p;heavy=u
        products+=1<<len(u);rank=max(rank,len(out));live-=A+B
        if out0:active[k]=out;live+=C
    if active:raise RuntimeError('Incomplete projection')
    return dict(predictedArrayBytes=peak,productsPerSlice=products,maxOutputRank=rank,heavy=heavy)

def choose_slices(scopes,steps,itemsize,max_bytes,max_slices,max_products):
    cut=set();stats=projected(scopes,steps,cut,itemsize)
    while stats['predictedArrayBytes']>max_bytes:
        if 2**(len(cut)+1)>max_slices:raise Boundary('Slice budget exceeded')
        candidates=[]
        for v in sorted(stats['heavy']-cut):
            a=projected(scopes,steps,cut|{v},itemsize);candidates.append((a['predictedArrayBytes'],a['productsPerSlice'],v,a))
        if not candidates:raise Boundary('No slice candidate reduces peak')
        _,_,v,stats=min(candidates,key=lambda a:a[:3]);cut.add(v)
    count=1<<len(cut);total=stats['productsPerSlice']*count
    if total>max_products:raise Boundary(f'Sliced total work {total} exceeds {max_products}')
    return sorted(cut),{k:v for k,v in stats.items() if k!='heavy'}|dict(slices=count,totalProducts=total)

def multiply_tensors(a, sa, b, sb, out):
    """Group binary axes for a batched matrix product; preserve shared output axes."""
    common = set(sa) & set(sb)
    batch = sorted(common.intersection(out))
    summed = sorted(common.difference(out))
    left = [v for v in sa if v not in common]
    right = [v for v in sb if v not in common]
    # A one-sided reduction needs the general contraction rule.
    if set(left + right + batch) != set(out):
        return None
    def reshape(array, axes, groups):
        order = [axes.index(v) for group in groups for v in group]
        return array.transpose(order).reshape(tuple(1 << len(group) for group in groups))
    x = reshape(a, sa, [batch, left, summed])
    y = reshape(b, sb, [batch, summed, right])
    result = (x @ y).reshape((2,) * len(out))
    order = batch + left + right
    return result.transpose([order.index(v) for v in out])

def scaled_contract(raw,steps,assignment):
    fs={};scale=0;scalar=complex(1.)
    def normalize(a):
        a=np.asarray(a);m=float(np.max(np.abs(a)))
        if not math.isfinite(m):raise Boundary('Nonfinite tensor')
        if m==0:return a,0
        e=math.frexp(m)[1]-1;b=a/math.ldexp(1.,e)
        if np.any((a!=0)&(b==0)):raise Boundary('Tensor scaling underflow')
        return b,e
    def accumulate(a,e):
        nonlocal scale,scalar
        z=complex(a)*scalar
        if a!=0 and scalar!=0 and z==0:raise Boundary('Scalar underflow')
        b,k=normalize(np.asarray(z));scalar=complex(b.item());scale+=e+k
    cut=set(assignment)
    for i,(s,a) in enumerate(raw):
        v=a[tuple(assignment.get(x,slice(None)) for x in s)] if s else a
        b,e=normalize(v)
        if s:fs[i]=(tuple(x for x in s if x not in cut),b,e)
        else:accumulate(b.item(),e)
    for i,j,k,out0 in steps:
        sa,a,ea=fs.pop(i)
        if j is None:sb=();b=None;eb=0
        else:sb,b,eb=fs.pop(j)
        out=tuple(x for x in out0 if x not in cut);u=sorted(set(sa)|set(sb));ids={v:i for i,v in enumerate(u)}
        if len(u)>52:raise Boundary('Einsum label limit')
        args=[a,[ids[v] for v in sa]]
        if b is not None:args.extend([b,[ids[v] for v in sb]])
        c=multiply_tensors(a,sa,b,sb,out) if b is not None else None
        if c is None:c=np.einsum(*args,[ids[v] for v in out],optimize=True)
        del args,a,b
        c,e=normalize(c);e+=ea+eb
        if out0:fs[k]=(out,c,e)
        else:accumulate(c.item(),e)
        del c
    if fs:raise RuntimeError('Incomplete sliced plan')
    return scalar,scale

def dyadic(v,e):
    if abs(e)>131072:raise Boundary('Slice accumulation exponent limit')
    a,b=float(v).as_integer_ratio()
    return Fraction(a*(1<<e),b) if e>=0 else Fraction(a,b*(1<<(-e)))

def execute(n,gates,bits,*,max_bytes=512*2**20,max_slices=64,max_products=2**42,trials=128,seed=873,representation='affine',plan_only=False):
    if type(max_bytes)!=int or not 1024<=max_bytes<=2**31 or type(max_slices)!=int or not 1<=max_slices<=1024 or type(max_products)!=int or not 1<=max_products<=2**46 or type(trials)!=int or not 1<=trials<=1024:raise ValueError('Invalid slice budgets')
    if representation not in ('affine','compact'):raise ValueError('Invalid representation')
    start=time.monotonic();raw,itemsize=compile_compact(n,gates,bits);algebra={}
    if representation=='affine':raw,algebra=eliminate_affine(raw)
    scopes=[s for s,a in raw];p=hyperplan(scopes,itemsize,trials,seed);steps=p['steps'];cut,stats=choose_slices(scopes,steps,itemsize,max_bytes,max_slices,max_products)
    info=dict(mode='sliced-native-contraction',qubits=n,gates=len(gates),representation=representation,unslicedArrayBytes=p['predictedArrayBytes'],unslicedProducts=p['products'],slicedVariables=cut,**stats,**algebra,scope='all slices; FP64 tensor arithmetic; exact represented-mantissa sum; total RSS separate')
    if plan_only:return info
    re=Fraction(0);im=Fraction(0);completed=0
    for vals in itertools.product((0,1),repeat=len(cut)):
        z,e=scaled_contract(raw,steps,dict(zip(cut,vals)));re+=dyadic(z.real,e);im+=dyadic(z.imag,e);completed+=1
    mag=max(abs(re),abs(im))
    if mag:
        e=mag.numerator.bit_length()-mag.denominator.bit_length();two=Fraction(2)**e;z=complex(float(re/two),float(im/two));log=math.log2(abs(z))+e;phase=math.atan2(z.imag,z.real)
    else:log=None;phase=0.
    a=float(re);b=float(im)
    if not math.isfinite(a) or not math.isfinite(b):raise Boundary('Nonfinite output')
    return dict(info,completedSlices=completed,real=a,imag=b,log2Magnitude=log,phase=phase,componentUnderflow=bool(re and a==0 or im and b==0),elapsedSeconds=time.monotonic()-start,peakRSSKiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None)

if __name__=='__main__':
    try:print(json.dumps(execute(**json.load(sys.stdin)),allow_nan=False))
    except (Boundary,ValueError,OverflowError,MemoryError) as e:print(json.dumps({'error':str(e)}));sys.exit(2)
