"""Bounded seven-product complex matrix multiplication, uncertified only.
Work charges classical products *and* all extra block additions. No reduced
precision. The planner may select it only when it has lower arithmetic work.
"""
import functools
import numpy as np
@functools.lru_cache(maxsize=8192)
def choose(m,k,n,d=4):
    base=m*k*n
    if not d or min(m,k,n)<32:return base,0
    c,_=choose(m//2,k//2,n//2,d-1)
    z=7*c+(5*m*k+5*k*n+8*m*n)//4
    return (z,d) if z<base else (base,0)

def matmul(a,b,d=4):
    m,k=a.shape[-2:];n=b.shape[-1];cost,depth=choose(m,k,n,d)
    if not depth:return a@b
    u=m//2;v=k//2;w=n//2
    a11,a12,a21,a22=a[...,:u,:v],a[...,:u,v:],a[...,u:,:v],a[...,u:,v:];b11,b12,b21,b22=b[...,:v,:w],b[...,:v,w:],b[...,v:,:w],b[...,v:,w:]
    # Accumulate outputs sequentially instead of retaining seven products.
    z=np.empty(a.shape[:-2]+(m,n),dtype=np.result_type(a,b));x11,x12,x21,x22=z[...,:u,:w],z[...,:u,w:],z[...,u:,:w],z[...,u:,w:]
    p=matmul(a11+a22,b11+b22,d-1);x11[...]=p;x22[...]=p
    p=matmul(a21+a22,b11,d-1);x21[...]=p;x22-=p
    p=matmul(a11,b12-b22,d-1);x12[...]=p;x22+=p
    p=matmul(a22,b21-b11,d-1);x11+=p;x21+=p
    p=matmul(a11+a12,b22,d-1);x11-=p;x12+=p
    p=matmul(a21-a11,b11+b12,d-1);x22+=p
    p=matmul(a12-a22,b21+b22,d-1);x11+=p
    return z

def maskcost(a,b,out):
    inter=(a&b).bit_count();k=(a|b).bit_count()-out.bit_count();batch=inter-k;m=a.bit_count()-inter;n=b.bit_count()-inter
    if min(k,batch,m,n)<0:raise ValueError('Inconsistent tree masks')
    return (1<<batch)*choose(1<<m,1<<k,1<<n)[0]
