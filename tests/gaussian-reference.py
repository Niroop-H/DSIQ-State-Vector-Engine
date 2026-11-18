# Test-only independent spin-space and spectral reference; not imported by DSIQ.
import json, sys, numpy as np
from scipy.linalg import eigh, expm

def pf(m):
    n=len(m)
    if n==0:return 1+0j
    if n%2:return 0j
    return sum((-1)**(j+1)*m[0,j]*pf(m[np.ix_([i for i in range(1,n) if i!=j],[i for i in range(1,n) if i!=j])]) for j in range(1,n))
def check(case):
    h,J,t=case['h'],case['J'],case['t'];n=len(h);d=2*n
    A=np.zeros((d,d))
    for i,v in enumerate(h):A[2*i,2*i+1]=2*v
    for i,v in enumerate(J):A[2*i+1,2*i+2]=2*v
    A-=A.T
    lam,V=eigh(-1j*A);R=(V*np.exp(1j*lam*t))@V.conj().T
    assert np.max(abs(R.imag))<1e-12;R=R.real
    S=R.T;C=np.zeros_like(A)
    for i in range(n):C[2*i,2*i+1]=-1;C[2*i+1,2*i]=1
    cov=R@C@R.T;P=(S[::2,::2]+S[1::2,1::2]+1j*(S[1::2,::2]-S[::2,1::2]))/2;Q=(S[::2,::2]-S[1::2,1::2]+1j*(S[1::2,::2]+S[::2,1::2]))/2
    Z=-np.linalg.solve(P,Q);vac=np.exp(np.log(np.linalg.eigvals(P)).sum()/2)
    # Spectral eigenvector cancellation can obscure very small pair amplitudes.
    # Independently refine using a long-double banded exponential and Neumann solve.
    # The relative comparison uses this reference; the absolute spectral check remains.
    D=-np.asarray(A*t,dtype=np.longdouble);D.fill(0)
    for i,v in enumerate(h):D[2*i,2*i+1]=-2*np.longdouble(v)*np.longdouble(t);D[2*i+1,2*i]=-D[2*i,2*i+1]
    for i,v in enumerate(J):D[2*i+1,2*i+2]=-2*np.longdouble(v)*np.longdouble(t);D[2*i+2,2*i+1]=-D[2*i+1,2*i+2]
    T=np.eye(d,dtype=np.longdouble);S2=T.copy()
    for k in range(1,33):
        B=np.zeros_like(T);B[:-1]+=np.diag(D,1)[:,None]*T[1:];B[1:]+=np.diag(D,-1)[:,None]*T[:-1];T=B/k;S2+=T
    P2=(S2[::2,::2]+S2[1::2,1::2]+1j*(S2[1::2,::2]-S2[::2,1::2]))/2
    Q2=(S2[::2,::2]-S2[1::2,1::2]+1j*(S2[1::2,::2]+S2[::2,1::2]))/2
    E=P2-np.eye(n,dtype=np.clongdouble);assert np.max(np.sum(abs(E),axis=1))<.7
    W=-Q2.copy()
    for _ in range(64):W=-Q2-E@W
    assert np.max(abs(P2@W+Q2))<1e-16
    ref2=[]
    out=[];dense=None
    if n<=8:
        N=1<<n;H=np.zeros((N,N),complex)
        for x in range(N):
            H[x,x]=-sum(a*(1-2*((x>>j)&1)) for j,a in enumerate(h))
            for j,a in enumerate(J):H[x^(3<<j),x]-=a
        dense=expm(-1j*t*H)[:,0]
    for b in case['bits']:
        ids=[i for i in range(n) if b[n-1-i]=='1'];v=vac*pf(Z[np.ix_(ids,ids)])
        if dense is not None:assert abs(v-dense[int(b,2)])<1e-12
        out.append([v.real,v.imag]);w=vac*pf(W[np.ix_(ids,ids)]);ref2.append([float(w.real),float(w.imag)])
    return {'amps':out,'refined':ref2,'cov':cov.ravel().tolist(),'energy':float(sum(h[i]*cov[2*i,2*i+1] for i in range(n))+sum(J[i]*cov[2*i+1,2*i+2] for i in range(n-1))),'denseNorm':float(np.vdot(dense,dense).real) if dense is not None else None}
print(json.dumps([check(c) for c in json.load(sys.stdin)]))
