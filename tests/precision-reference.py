"""Independent high-precision and exact-rational path-scatter oracles."""
import sys,json,mpmath as mp
from fractions import Fraction as F
mp.mp.dps=100

def high_case(case):
    n=case['n'];a=[mp.mpc(int(j==0)) for j in range(2**n)]
    for g in case['gates']:
        q=g['q'];cs=g['controls'];name=g['name'];t=mp.mpf(g.get('theta',0));c=mp.cos(t/2);s=mp.sin(t/2)
        if name in ('x','cx','mcx'): M=[0,1,1,0]
        elif name in ('z','cz'): M=[1,0,0,-1]
        elif name=='h': M=[1/mp.sqrt(2),1/mp.sqrt(2),1/mp.sqrt(2),-1/mp.sqrt(2)]
        elif name=='ry': M=[c,-s,s,c]
        elif name=='rx': M=[c,-mp.j*s,-mp.j*s,c]
        elif name=='rz': M=[mp.exp(-mp.j*t/2),0,0,mp.exp(mp.j*t/2)]
        elif name in ('p','cp'): M=[1,0,0,mp.exp(mp.j*t)]
        elif name=='t': M=[1,0,0,mp.exp(mp.j*mp.pi/4)]
        elif name=='tdg': M=[1,0,0,mp.exp(-mp.j*mp.pi/4)]
        elif name=='y': M=[0,-mp.j,mp.j,0]
        elif name=='s': M=[1,0,0,mp.j]
        elif name=='u':
            p=mp.mpf(g['phi']);l=mp.mpf(g['lambda']);M=[c,-s*mp.exp(mp.j*l),s*mp.exp(mp.j*p),c*mp.exp(mp.j*(p+l))]
        elif name=='swap': M=None
        else: raise ValueError(name)
        b=[mp.mpc(0) for _ in a]
        for j,z in enumerate(a):
            if name=='swap':
                x=j;u=(j>>q)&1;v=(j>>cs[0])&1
                if u!=v:x^=(1<<q)|(1<<cs[0])
                b[x]+=z
            elif all(j>>k&1 for k in cs):
                col=j>>q&1;base=j&~(1<<q)
                for row in range(2):b[base|(row<<q)]+=M[2*row+col]*z
            else:b[j]+=z
        a=b
    maxdelta=mp.mpf(0);maxfraction=mp.mpf(0)
    for j,r in enumerate(case['amps']):
        delta=abs(a[j]-mp.mpc(r['real'],r['imag']));bound=mp.mpf(r['absoluteErrorBound']);assert delta<=bound,(delta,bound);maxdelta=max(maxdelta,delta);maxfraction=max(maxfraction,delta/bound)
    for pauli,r in case['observables']:
        ev=mp.mpc(0)
        for x,z in enumerate(a):
            y=x;phase=mp.mpc(1)
            for q,p in enumerate(reversed(pauli)):
                if p in 'XY':y^=1<<q
                if p in 'YZ' and x>>q&1:phase=-phase
                if p=='Y':phase*=mp.j
            ev+=mp.conj(a[y])*phase*z
        delta=abs(ev-mp.mpf(r['real']));bound=mp.mpf(r['absoluteErrorBound']);assert delta<=bound,(pauli,delta,bound);maxdelta=max(maxdelta,delta);maxfraction=max(maxfraction,delta/bound)
    norm=mp.fsum(abs(z)**2 for z in a);assert abs(norm-1)<mp.mpf('1e-90')
    return {'amplitudes':len(a),'observables':len(case['observables']),'maxObservedError':float(maxdelta),'maxBoundFraction':float(maxfraction)}

def exact_case(case):
    n=case['n'];z=(F(0),F(0));a=[(F(int(j==0)),F(0)) for j in range(2**n)]
    def mul(x,y):return (x[0]*y[0]-x[1]*y[1],x[0]*y[1]+x[1]*y[0])
    def add(x,y):return (x[0]+y[0],x[1]+y[1])
    for g in case['gates']:
        q=g['q'];cs=g['controls'];b=[z for _ in a]
        if g['name']=='swap':
            for j,v in enumerate(a):b[j^(((1<<q)|(1<<cs[0])) if ((j>>q)^(j>>cs[0]))&1 else 0)]=v
        else:
            M=[tuple(F(x) for x in pair) for pair in g['M']]
            for j,v in enumerate(a):
                if all(j>>k&1 for k in cs):
                    col=j>>q&1;base=j&~(1<<q)
                    for row in range(2):b[base|(row<<q)]=add(b[base|(row<<q)],mul(M[2*row+col],v))
                else:b[j]=add(b[j],v)
        a=b
    for j,r in enumerate(case['amps']):
        scale=F(2)**r['binaryExponent'];assert a[j]==(F(int(r['realMantissa']))*scale,F(int(r['imagMantissa']))*scale),(j,a[j],r)
    return {'exactAmplitudes':len(a)}

x=json.load(sys.stdin);fn=high_case if x['kind']=='certificate' else exact_case
print(json.dumps([fn(c) for c in x['cases']]))
