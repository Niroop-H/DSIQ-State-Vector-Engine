"""Diamond #70 diagnostics on the unchanged seeded matching circuit."""
import json
import pathlib
import runpy
import sys
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING
from itertools import islice
from hashlib import sha256
import numpy as np

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'native'))
from mps_projection import amplitude
from mps_exact import Boundary
from bond_contract import gate_matrix

fixture=runpy.run_path(str(ROOT/'tests/mps-random-uncompute.py'))


def echo_interval(gates):
    """Contract represented local adjoints with outward rounding; no midpoint state claim."""
    if len(gates)%2:
        raise ValueError('Odd echo length')
    factors=[]
    for left,right in zip(islice(gates,len(gates)//2),reversed(gates)):
        if (left['name'],left['q'],left['controls'])!=(right['name'],right['q'],right['controls']):
            raise ValueError('Mismatched gate or wires')
        if left['name']=='cx' and len(left['controls'])==1:
            continue
        if left['name']!='ry' or left['controls']:
            raise ValueError('Unsupported echo factor')
        a,b=gate_matrix(left),gate_matrix(right)
        c,s=a[0,0],a[1,0]
        if not (np.array_equal(a,[[c,-s],[s,c]]) and np.array_equal(b,a.T)):
            raise ValueError('Gate matrices are not represented adjoints')
        factors.append((Decimal.from_float(float(c)),Decimal.from_float(float(s))))
    bounds=[]
    for rounding in (ROUND_FLOOR,ROUND_CEILING):
        with localcontext() as ctx:
            ctx.prec=65
            ctx.rounding=rounding
            v=Decimal(1)
            for c,s in factors:
                v*=c*c+s*s
            bounds.append(v*v)
    return bounds


def main():
    small=fixture['make'](8,8377)[:36]
    dense=fixture['dense'](8,small)
    err=max(abs(amplitude(8,small,format(i,'08b'))[0]-z) for i,z in enumerate(dense))
    assert err<1e-13
    gates=fixture['make'](100,8377)
    points=[]
    for depth in (3,4,100):
        try:
            z,split=amplitude(100,gates[:150*depth],'0'*100)
            points.append(dict(depth=depth,real=z.real,imag=z.imag,ketGates=split))
        except Boundary as e:
            points.append(dict(depth=depth,boundary=str(e)))
    assert 'real' in points[0]
    echo=gates+fixture['inverse'](gates)
    lo,hi=echo_interval(echo)
    assert format(lo,'.12f')==format(hi,'.12f')=='1.000000000000'
    damaged=echo.copy()
    damaged[-1]=dict(damaged[-1],theta=damaged[-1]['theta']+.01)
    try:echo_interval(damaged)
    except ValueError:pass
    else:raise AssertionError('Noninverse accepted')
    print(json.dumps(dict(gates=len(echo),fixtureSHA256=sha256(json.dumps(echo,sort_keys=True).encode()).hexdigest(),
                          projectionDenseMaxError=err,prefixes=points,representedEchoProbability=[str(lo),str(hi)],
                          scope='Adjoint contraction certifies final composite only. Prefix contractions execute the stated forward prefixes.')))
if __name__=='__main__':main()
