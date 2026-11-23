"""Amplitude queries by contracting a product bra from the output towards an MPS."""
import numpy as np
from mps_exact import ExactMPS, Boundary
from bond_contract import gate_matrix


def amplitude(n, gates, bits, max_bytes=64*2**20, max_work=2**36):
    if len(bits)!=n or set(bits)-set('01'):
        raise ValueError('Invalid output basis')
    # Rows below represent bras directly, so right multiplication uses U.
    rows=np.eye(2,dtype=complex)[[int(b) for b in bits[::-1]]]
    split=len(gates)
    while split:
        g=gates[split-1]
        q=g['q']
        if not 0<=q<n:
            raise ValueError('Invalid target')
        if g['name']=='cx' and len(g['controls'])==1:
            c=g['controls'][0]
            if not 0<=c<n or c==q:
                raise ValueError('Invalid control')
            if rows[c,1]==0:
                pass
            elif rows[c,0]==0:
                rows[q]=rows[q,::-1].copy()
            else:
                break
        elif not g['controls'] and g['name'] in ('h','x','y','z','ry','rx','rz','p','u','s','sdg','t','tdg','i'):
            rows[q]=rows[q] @ gate_matrix(g)
        else:
            break
        split-=1
    ket=ExactMPS(n,gates[:split],max_bytes,max_work)
    v=np.ones(1,complex)
    for q,site in zip(ket.order,ket.a):
        ket.charge(12*site.shape[0]*site.shape[2])
        v=v @ (rows[q,0]*site[:,0,:]+rows[q,1]*site[:,1,:])
    result=complex(v[0])
    if not np.isfinite(result):
        raise Boundary('Nonfinite product projection')
    return result,split
