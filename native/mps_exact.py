"""Untruncated matrix-product state backend. NumPy/LAPACK for QR, no simulator.
No singular-value cutoff, approximate low-rank compression or benchmark templates.
All reduced QR columns are retained, including columns associated with zero rank.
"""
import json, math, sys, time, resource
import numpy as np
from bond_contract import Boundary, gate_matrix

I=np.eye(2,dtype=np.complex128)
SWAP=I.reshape(2,1,2,1)*I.reshape(1,2,1,2)
SWAP=SWAP.transpose(1,0,2,3).reshape(4,4)

def compile_ops(n,gates):
    if type(n)!=int or not 1<=n<=4096 or not isinstance(gates,list) or len(gates)>100000:raise ValueError('Invalid circuit')
    ops=[]
    for g in gates:
        q=g['q'];cs=g['controls'];name=g['name']
        if type(q)!=int or not 0<=q<n or len(cs)>1 or any(type(c)!=int or not 0<=c<n or c==q for c in cs):raise ValueError('Invalid gate wires')
        if name not in ('swap','i','h','x','y','z','s','sdg','t','tdg','rx','ry','rz','p','u','cx','cy','cz','crx','cry','crz','cp','cu','fsim'):raise Boundary('Unsupported MPS gate '+name)
        two=name in ('swap','cx','cy','cz','crx','cry','crz','cp','cu','fsim')
        if len(cs)!=int(two):raise ValueError('Invalid gate arity')
        for key in {'rx':('theta',),'ry':('theta',),'rz':('theta',),'p':('theta',),'cp':('theta',),'crx':('theta',),'cry':('theta',),'crz':('theta',),'u':('theta','phi','lambda'),'cu':('theta','phi','lambda'),'fsim':('theta','phi')}.get(name,()):
            if not isinstance(g.get(key),(int,float)) or not math.isfinite(g[key]):raise ValueError('Invalid angle '+key)
        if not two:
            m=np.asarray(gate_matrix(g),dtype=np.complex128);ops.append((q,m));continue
        c=cs[0];l,h=sorted((q,c));
        if name=='swap':m=SWAP.copy()
        elif name=='fsim':
            a,b=g['theta'],g['phi'];m=np.array([[1,0,0,0],[0,math.cos(a),-1j*math.sin(a),0],[0,-1j*math.sin(a),math.cos(a),0],[0,0,0,complex(math.cos(b),-math.sin(b))]],complex)
        else:
            m=np.zeros((4,4),complex);m[:2,:2]=I;m[2:,2:]=gate_matrix(g)
            if c>q:m=SWAP@m@SWAP
        if not np.all(np.isfinite(m)):raise ValueError('Nonfinite gate matrix')
        # Bring the right endpoint next to the left, apply, restore wire order.
        ops.extend((i,SWAP) for i in range(h-1,l,-1));ops.append((l,m));ops.extend((i,SWAP) for i in range(l+1,h))
        if len(ops)>1000000:raise Boundary('Routed gate limit')
    return ops

def plan(n,ops,max_bytes,max_work):
    if type(max_bytes)!=int or not 1024<=max_bytes<=2**30 or type(max_work)!=int or not 1<=max_work<=2**44:raise ValueError('Invalid resource budgets')
    dims=[1]*(n+1);live=32*n;peak=live;maxrank=1;work=0
    for q,m in ops:
        a,b=dims[q:q+2]
        if m.shape==(2,2):
            temp=32*a*b;work+=8*a*b
        else:
            c=dims[q+2];r=min(2*a,2*c);old=32*b*(a+c);new=32*r*(a+c)
            # Conservative explicit-array model; LAPACK internal workspace separate.
            temp=16*(3*4*a*c+2*a*b+2*b*c+6*r*(a+c)+r*r)
            work+=4*a*b*c+16*a*c+16*a*c*r;live+=new-old;dims[q+1]=r;maxrank=max(maxrank,r)
        peak=max(peak,live+temp)
        if peak>max_bytes or work>max_work:raise Boundary(f'MPS predicted resource limit: {peak} bytes, {work} work units')
    # Right canonical sweep with reduced QR; all columns retained. Scratch bound
    # covers reduced QR plus the adjacent matrix absorption.
    for q in range(n-1,0,-1):
        a,b,c=dims[q-1:q+2];r=min(b,2*c);old=32*b*(a+c);new=32*r*(a+c)
        temp=16*(4*b*c+4*r*c+2*r*b+4*a*r+2*a*b+2*r*r);live+=new-old;dims[q]=r
        peak=max(peak,live+temp);work+=8*b*c*r+4*a*b*r
        if peak>max_bytes or work>max_work:raise Boundary('MPS canonicalization exceeds budget')
    # Transfer queries use bond-squared scratch, not full statevector.
    query_scratch=16*12*maxrank*maxrank;peak=max(peak,live+query_scratch)
    if peak>max_bytes:raise Boundary('MPS transfer scratch exceeds budget')
    return dict(predictedExplicitArrayBytes=peak,finalCoefficientBytes=live,maxBond=maxrank,plannedWorkUnits=work,routedOperations=len(ops))

class ExactMPS:
    def __init__(self,n,gates,max_bytes=64*2**20,max_work=2**36):
        self.n=n;self.ops=compile_ops(n,gates);self.max_work=max_work;self.used_work=0;self.info=plan(n,self.ops,max_bytes,max_work);self.a=[np.array([[[1.],[0.]]],complex) for _ in range(n)];self.max_live=sum(x.nbytes for x in self.a);self.live=self.max_live
        for q,m in self.ops:
            x=self.a[q];dl,_,dm=x.shape
            if m.shape==(2,2):self.a[q]=np.einsum('uv,avb->aub',m,x,optimize=True)
            else:
                y=self.a[q+1];dr=y.shape[2];state=np.tensordot(x,y,axes=(2,0));state=np.einsum('uvst,astb->auvb',m.reshape(2,2,2,2),state,optimize=True)
                Q,R=np.linalg.qr(state.reshape(dl*2,2*dr),mode='reduced');r=Q.shape[1];self.a[q]=Q.reshape(dl,2,r);self.a[q+1]=R.reshape(r,2,dr);self.live+=self.a[q].nbytes+self.a[q+1].nbytes-x.nbytes-y.nbytes
            self.max_live=max(self.max_live,self.live)
        for q in range(n-1,0,-1):
            x=self.a[q];y=self.a[q-1];a,_,b=x.shape;Q,R=np.linalg.qr(x.reshape(a,2*b).T,mode='reduced');r=Q.shape[1];self.a[q]=Q.T.reshape(r,2,b);self.a[q-1]=np.tensordot(y,R.T,axes=(2,0));self.live+=self.a[q].nbytes+self.a[q-1].nbytes-x.nbytes-y.nbytes;self.max_live=max(self.max_live,self.live)
        if self.live!=self.info['finalCoefficientBytes'] or self.max_live>self.info['predictedExplicitArrayBytes']:raise RuntimeError('Shape prediction mismatch')
        if not all(np.all(np.isfinite(a)) for a in self.a):raise Boundary('Nonfinite state')
        self.used_work=self.info['plannedWorkUnits']
    def charge(self,work):
        self.used_work+=int(work)
        if self.used_work>self.max_work:raise Boundary('MPS query work budget exhausted')
    def amplitude(self,bits):
        if not isinstance(bits,str) or len(bits)!=self.n or set(bits)-set('01'):raise ValueError('Invalid basis index')
        v=np.ones(1,complex);e=0
        for a,b in zip(self.a,bits[::-1]):
            self.charge(a.shape[0]*a.shape[2]*4);v=v@a[:,int(b),:];m=float(np.max(np.abs(v)))
            if not math.isfinite(m):raise Boundary('Nonfinite amplitude')
            if not m:return dict(real=0.,imag=0.,log2Magnitude=None,phase=0.,componentUnderflow=False)
            _,k=math.frexp(m);k-=1;w=v/math.ldexp(1.,k)
            if np.any((v!=0)&(w==0)):raise Boundary('Scaling underflow')
            v=w;e+=k
        z=complex(v[0]);re=math.ldexp(z.real,e);im=math.ldexp(z.imag,e)
        return dict(real=re,imag=im,log2Magnitude=math.log2(abs(z))+e,phase=math.atan2(z.imag,z.real),componentUnderflow=bool((z.real and not re) or (z.imag and not im)))
    def expectation(self,pauli):
        if not isinstance(pauli,str) or len(pauli)!=self.n or set(pauli)-set('IXYZ'):raise ValueError('Invalid Pauli')
        mats={'I':I,'X':np.array([[0,1],[1,0]]),'Y':np.array([[0,-1j],[1j,0]]),'Z':np.diag([1,-1])};env=np.ones((1,1),complex)
        for a,p in zip(self.a,pauli[::-1]):
            l,_,r=a.shape;self.charge(16*(l*l*r+l*r*r));o=mats[p];env=np.einsum('ab,asx,st,bty->xy',env,a.conj(),o,a,optimize=True)
        z=complex(env[0,0]);
        if not math.isfinite(z.real) or not math.isfinite(z.imag) or abs(z.imag)>1e-9:raise Boundary('Observable lost numerical validity')
        return z.real
    def sample(self,rng):
        # Right-canonical suffix is an isometry. Projective conditionals are
        # squared norms of the two branch vectors, normalized at each wire.
        v=np.ones(1,complex);bits=[]
        for a in self.a:
            self.charge(16*a.shape[0]*a.shape[2]);w=np.stack((v@a[:,0,:],v@a[:,1,:]));p=np.sum(np.abs(w)**2,axis=1);total=float(p.sum())
            if not math.isfinite(total) or total<=0:raise Boundary('Invalid sampling norm')
            b=int(rng.random()*total>=p[0]);prob=float(p[b]);
            if prob<=0:raise Boundary('Zero sample branch')
            v=w[b]/math.sqrt(prob);bits.append(str(b))
        return ''.join(reversed(bits))
    def stats(self):return dict(self.info,coefficientBytes=self.live,peakLiveCoefficientBytes=self.max_live,actualMaxBond=max(a.shape[2] for a in self.a),workUnitsCharged=self.used_work,mode='untruncated-mps',precision='FP64 QR; all dimensional columns retained; no SVD cutoff; LAPACK scratch and total RSS separate')

def execute(n,gates,queries=None,paulis=None,shots=0,seed=0,max_bytes=64*2**20,max_work=2**36,plan_only=False):
    import random
    queries=[] if queries is None else queries;paulis=[] if paulis is None else paulis
    if not isinstance(queries,list) or len(queries)>10000 or not isinstance(paulis,list) or len(paulis)>1000 or type(shots)!=int or not 0<=shots<=10000:raise ValueError('Invalid query limits')
    if plan_only:return plan(n,compile_ops(n,gates),max_bytes,max_work)
    start=time.monotonic();d=ExactMPS(n,gates,max_bytes,max_work);norm=d.expectation('I'*n);a=[d.amplitude(b) for b in queries];p=[d.expectation(s) for s in paulis];rng=random.Random(seed);samples=[d.sample(rng) for _ in range(shots)]
    return dict(amplitudes=a,observables=p,norm=norm,samples=samples,stats=d.stats(),elapsedSeconds=time.monotonic()-start,processPeakRSSKiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
if __name__=='__main__':
    try:print(json.dumps(execute(**json.load(sys.stdin)),allow_nan=False))
    except (ValueError,Boundary,OverflowError,MemoryError) as e:print(json.dumps({'error':str(e)}));sys.exit(2)
