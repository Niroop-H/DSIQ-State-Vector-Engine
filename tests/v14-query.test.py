#!/usr/bin/env python3
"""Independent high-precision dense oracle; no prior challenge/reference files."""
import json,math,random,pathlib,sys,subprocess,importlib.util
import mpmath as mp
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'native'))
import query_contraction as fast
import certified_query_contraction as cert
mp.mp.dps=110;rng=random.Random(70110386)
def g(name,q,cs=(),**extra):return dict(name=name,q=q,controls=list(cs),**extra)
def one(q):
    name=rng.choice(['h','x','y','z','s','sdg','t','tdg','rx','ry','rz','p','u'])
    return g(name,q,**{k:rng.uniform(-4,4) for k in fast.PARAM.get(name,())})
def two(q,c):
    name=rng.choice(['cx','cy','cz','cp','crx','cry','crz','cu','swap'])
    return g(name,q,[c],**{k:rng.uniform(-4,4) for k in fast.PARAM.get(name,())})
def mat(g):
    name=g['name'];t=mp.mpf(g.get('theta',0));c=mp.cos(t/2);s=mp.sin(t/2);i=mp.j
    if name=='i':return [1,0,0,1]
    if name in ('x','cx'):return [0,1,1,0]
    if name in ('y','cy'):return [0,-i,i,0]
    if name in ('z','cz'):return [1,0,0,-1]
    if name=='h':return [1/mp.sqrt(2)]*3+[-1/mp.sqrt(2)]
    if name in ('s','sdg','t','tdg'):return [1,0,0,{'s':i,'sdg':-i,'t':mp.exp(i*mp.pi/4),'tdg':mp.exp(-i*mp.pi/4)}[name]]
    if name in ('rx','crx'):return [c,-i*s,-i*s,c]
    if name in ('ry','cry'):return [c,-s,s,c]
    if name in ('rz','crz'):return [mp.exp(-i*t/2),0,0,mp.exp(i*t/2)]
    if name in ('p','cp'):return [1,0,0,mp.exp(i*t)]
    if name in ('u','cu'):
        p,l=mp.mpf(g['phi']),mp.mpf(g['lambda']);return [c,-s*mp.exp(i*l),s*mp.exp(i*p),c*mp.exp(i*(p+l))]
    raise ValueError(name)
def evolve(a,g):
    q=g['q'];cs=g['controls'];b=[mp.mpc(0) for _ in a];name=g['name']
    if name=='swap':
        c=cs[0]
        for x,v in enumerate(a):b[x^(((1<<q)|(1<<c)) if ((x>>q)^(x>>c))&1 else 0)]=v
    else:
        M=mat(g)
        for x,v in enumerate(a):
            if not all(x>>c&1 for c in cs):b[x]+=v;continue
            for row in range(2):b[(x&~(1<<q))|(row<<q)]+=M[2*row+(x>>q&1)]*v
    return b
def obs(a,p):
    total=mp.mpc(0)
    for x,v in enumerate(a):
        y=x;k=mp.mpc(1)
        for q,c in enumerate(reversed(p)):
            if c in 'XY':y^=1<<q
            if c in 'YZ' and x>>q&1:k=-k
            if c=='Y':k*=mp.j
        total+=mp.conj(a[y])*k*v
    return mp.re(total)
def inv(a):
    b={**a};name=a['name'];b['name']={'t':'tdg','tdg':'t','s':'sdg','sdg':'s'}.get(name,name)
    for k in fast.PARAM.get(name,()):b[k]=-a[{'phi':'lambda','lambda':'phi'}.get(k,k) if name in ('u','cu') else k]
    return b
counts={'amplitude':0,'pauli':0,'norm':0};max_error=mp.mpf(0);max_fast=mp.mpf(0);max_rel=mp.mpf(0);max_bound=0.;tight_relative=0;eligible=0
for case in range(12):
    n=4+case%3;gs=[];w=list(range(n));rng.shuffle(w)
    for layer in range(3):
        gs.extend(one(q) for q in w)
        gs.extend(two(w[j],w[(j+1)%n]) for j in range(n if layer==1 else n-1))
    if case%3==0:gs+=list(map(inv,reversed(gs)))
    if case%3==1:
        rev=list(map(inv,reversed(gs)));rev[len(rev)//2]=g('rz',0,theta=0.0000123);gs+=rev
    if case%3==2:gs.extend([g('cx',w[-1],[w[0]]),g('cu',w[1],[w[-1]],theta=.123,phi=-.37,**{'lambda':.18})])
    for x in gs:fast.validate(n,x)
    ms=cert.matrices(gs);state=[mp.mpc(int(x==0)) for x in range(1<<n)];b=fast.Budget(2**29,10**9,1000000);cb=fast.Budget(2**29,10**9,1000000)
    for i,h in enumerate(gs,1):
        state=evolve(state,h)
        if i not in (len(gs)//2,len(gs)):continue
        qs=[('amplitude',format(x,f'0{n}b'),state[x]) for x in range(1<<n)]
        qs.extend(('pauli',p,obs(state,p)) for p in [''.join(rng.choices('IXYZ',k=n)) for _ in range(8)])
        qs.append(('norm',None,mp.fsum(abs(z)**2 for z in state)))
        for kind,key,t in qs:
            q={'kind':kind};q.update({'bits':key} if kind=='amplitude' else {'pauli':key} if kind=='pauli' else {})
            v,_=fast.evaluate(n,gs[:i],q,b);u,_=cert.evaluate(n,gs[:i],q,cb,ms);z=cert.result(u);er=abs(mp.mpc(z['real'],z['imag'])-t);ef=abs(mp.mpc(v.real,v.imag)-t)
            assert er<=mp.mpf(z['absoluteErrorBound'])+mp.mpf('1e-100'),(case,i,q,er,z)
            assert ef<=mp.mpf('1e-13'),(case,i,q,ef)
            assert er<=mp.mpf('1e-13');max_error=max(max_error,er);max_fast=max(max_fast,ef);max_bound=max(max_bound,z['absoluteErrorBound']);counts[kind]+=1
            if kind=='amplitude' and abs(t)>mp.mpf('1e-90'):
                rr=er/abs(t);rf=ef/abs(t);assert rr<mp.mpf('1e-9') and rf<mp.mpf('1e-9');max_rel=max(max_rel,rr,rf);eligible+=1;tight_relative+=z['relativeErrorUpperBound'] is not None and z['relativeErrorUpperBound']<=1e-9
# Tiny amplitude on 60 independently rotated wires; separate high precision oracle.
n=60;gs=[g('ry',q,theta=2e-5) for q in range(n)];q={'kind':'amplitude','bits':'1'*n};u,_=cert.evaluate(n,gs,q,fast.Budget(2**29,10**9,1000000),cert.matrices(gs));v=cert.result(u);t=mp.sin(mp.mpf(2e-5)/2)**n;er=abs(mp.mpf(v['real'])-t);assert er<=mp.mpf(v['absoluteErrorBound']);assert v['relativeErrorUpperBound']<=1e-9
# Uncertified route refuses strict requests, and invalid operands are rejected.
req={'n':2,'gates':[g('h',0),g('cx',1,[0])],'queries':[{'id':'n','kind':'norm','prefix':2}],'method':'certified-auto','requireCertificate':True}
p=subprocess.run([sys.executable,'-B',str(ROOT/'native/query_contraction.py')],input=json.dumps(req),text=True,capture_output=True);assert p.returncode!=0 and 'Strict request rejected' in p.stderr
p=subprocess.run([sys.executable,'-B',str(ROOT/'native/query-audit.py'),'--measure-norms'],input=json.dumps(req),text=True,capture_output=True);r=json.loads(p.stdout);assert p.returncode==0 and r['records'][0]['stats']['normEvidence'].startswith('double-layer') and r['checkpointEvidence'].startswith('NOT_RUN')
print(json.dumps({'freshCircuits':12,'denseOracleDigits':110,'comparisonsPerBackend':sum(counts.values()),'counts':counts,'maxFastAbsError':float(max_fast),'maxIntervalAbsError':float(max_error),'maxRelativeAmplitudeError':float(max_rel),'maxIntervalRadius':max_bound,'relativeBoundsWithinTolerance':tight_relative,'eligibleNonzeroAmplitudes':eligible,'tinyAmplitude':v,'tinyExpected':mp.nstr(t,35),'strictDowngradeRejected':True,'measuredNormAuditSmoke':True},indent=2))
