"""Independent source-scatter extended-precision reference for the active code.
No DSIQ gate matrices or reference-frame code imported. Linux long double only;
report precision explicitly and refuse silently downgraded reference precision.
"""
import json, sys, numpy as np
if np.finfo(np.longdouble).nmant <= 52:
    raise RuntimeError('Extended precision not available')
p=json.load(sys.stdin); n=p['n']; z=np.zeros(1<<n,dtype=np.clongdouble);z[0]=1
inds=np.arange(1<<n); pi=np.arccos(np.longdouble(-1)); root=np.sqrt(np.longdouble('0.5'))
for g in p['gates']:
    q=g['q']; name=g['name']; bits=(inds>>q)&1; flip=inds^(1<<q); on=np.ones(len(z),dtype=bool)
    for c in g['controls']: on &= ((inds>>c)&1)!=0
    new=np.zeros_like(z); new[~on]=z[~on]; x=inds[on]; y=flip[on]; a=bits[on]; v=z[on]
    if name=='cx': new[y]+=v
    elif name=='h': new[x]+=v*np.where(a==0,root,-root);new[y]+=v*root
    elif name=='ry':
        t=np.longdouble(g['theta'])/2;new[x]+=v*np.cos(t);new[y]+=v*np.where(a==0,np.sin(t),-np.sin(t))
    elif name=='rz':
        t=np.longdouble(g['theta'])/2;new[x]+=v*np.exp(np.clongdouble(1j)*np.where(a==0,-t,t))
    elif name in ('t','tdg'):
        t=pi/4*(1 if name=='t' else -1);new[x]+=v*np.exp(np.clongdouble(1j)*t*a)
    else: raise ValueError(name)
    z=new
json.dump({'mantissaBits':int(np.finfo(np.longdouble).nmant)+1,'amplitudes':[[float(x.real),float(x.imag)] for x in z],'norm':float(np.sum(np.abs(z)**2))},sys.stdout)
