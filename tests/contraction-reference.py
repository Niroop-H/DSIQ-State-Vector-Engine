# Test-only independent tensor network convention: full controlled gate tensor.
import json,sys,numpy as np,opt_einsum as oe

def evaluate(n,gates,bits,compact=False):
    wires=list(range(n));cur=n;t=[]
    for i in wires:t.extend([np.array([1,0],complex),[i]])
    for g in gates:
        name,q,c=g['name'],g['q'],g['controls'];a=g.get('theta',0);a=0 if a is None else a
        if name=='ry':M=np.array([[np.cos(a/2),-np.sin(a/2)],[np.sin(a/2),np.cos(a/2)]],complex)
        elif name=='rx':M=np.array([[np.cos(a/2),-1j*np.sin(a/2)],[-1j*np.sin(a/2),np.cos(a/2)]])
        elif name=='rz':M=np.diag(np.exp(np.array([-1j,1j])*a/2))
        elif name=='h':M=np.array([[1,1],[1,-1]])/np.sqrt(2)
        elif name=='cx':M=np.array([[0,1],[1,0]])
        elif name=='cz':M=np.diag([1,-1])
        elif name=='cp':M=np.diag([1,np.exp(1j*a)])
        else:raise ValueError(name)
        if c:
            assert len(c)==1;v=c[0]
            if compact:
                V=np.stack([np.eye(2),M]);t.extend([V,[wires[v],cur,wires[q]]]);wires[q]=cur;cur+=1
            else:
                V=np.zeros((2,2,2,2),complex);V[0,:,0,:]=np.eye(2);V[1,:,1,:]=M;t.extend([V,[cur,cur+1,wires[v],wires[q]]]);wires[v]=cur;wires[q]=cur+1;cur+=2
        else:t.extend([M,[cur,wires[q]]]);wires[q]=cur;cur+=1
    for q,v in enumerate(wires):t.extend([np.array([int(bits[n-1-q]=='0'),int(bits[n-1-q]=='1')],complex),[v]])
    limit=2097152 if compact else 262144
    path,info=oe.contract_path(*t,[],optimize='greedy')
    if info.largest_intermediate>limit or info.opt_cost>1000000000:return None
    value=oe.contract(*t,[],optimize=path);return [float(value.real),float(value.imag)]
x=json.load(sys.stdin);print(json.dumps([evaluate(x['n'],x['gates'],b,x.get('compact',False)) for b in x['bits']]))
