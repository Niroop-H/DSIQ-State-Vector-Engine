"""Cross-check the two exact-in-form amplitude routes on dense random graphs."""
from itertools import combinations
import json
import random
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from check_contraction import dense, get_terms, make_circuit, plan, amplitude


def native(n,bits,exe,budget,*args):
    edges,gates=make_circuit(n)
    costs=sorted({g['theta'] for g in gates if g['name']=='rz'})
    mixers=sorted({g['theta'] for g in gates if g['name']=='rx'})
    items=[str(x) for x in (n,len(edges),costs[0],mixers[0],costs[1],mixers[1],bits)]
    payload=' '.join(items)+'\n'+''.join(f'{i} {j}\n' for i,j in edges)
    start=time.perf_counter()
    proc=subprocess.run([str(exe),str(budget),*map(str,args)],input=payload,capture_output=True,text=True,timeout=300)
    if proc.returncode:
        return {'error':proc.stderr.strip()}
    fields=proc.stdout.split()
    partial=fields[0]=='partial_tile'
    return {('partial_tile' if partial else 'value'):list(map(float,fields[1:] if partial else fields)),'seconds':time.perf_counter()-start}


def check_native_variants(exe):
    rng=random.Random(93981)
    for n in (1,2,5,8):
        for edge_kind in ('empty','random','complete'):
            edges=[(u,v) for u,v in combinations(range(n),2)
                   if edge_kind=='complete' or (edge_kind=='random' and rng.random()<0.5)]
            rates = [rng.uniform(-5,5) for _ in range(4)]
            gs=[dict(name='h',q=q,controls=[]) for q in range(n)]
            for theta,beta in zip(rates[::2],rates[1::2]):
                for i,j in edges:
                    cx=dict(name='cx',q=j,controls=[i])
                    gs.extend([cx,dict(name='rz',q=j,controls=[],theta=theta),cx])
                gs.extend(dict(name='rx',q=q,controls=[],theta=beta) for q in range(n))
            ref=dense(n,gs)
            for idx in (0,1,(1<<n)-1):
                data=' '.join(map(str,[n,len(edges),*rates,format(idx,f'0{n}b')]))+'\n'+''.join(f'{u} {v}\n' for u,v in edges)
                for args in ([],[4,max(0,n-3)]):
                    p=subprocess.run([str(exe),*map(str,args)],input=data,text=True,capture_output=True,check=True)
                    a=complex(*map(float,p.stdout.split()))
                    assert abs(a-ref[idx])<1e-12
    print('72 native interface checks passed',file=sys.stderr)


def main(exe):
    check_native_variants(exe)
    rows=[]
    for n in (6,10,14,18,24,28,50):
        bits='0'*n
        terms,gates,sha=get_terms(n,bits)
        measured=native(n,bits,exe,3072)
        row=dict(n=n,edges=len(make_circuit(n)[0]),sha256=sha,native=measured)
        if n==50:
            assert measured=={'error':f'Coefficient bytes required: {16*(1<<49)}'}
        else:
            schedule=plan(terms,20)
            start=time.perf_counter()
            ref=amplitude(terms,schedule,4096)
            row.update(contraction_seconds=time.perf_counter()-start,slices=schedule['slices'],
                       contraction=[ref.real,ref.imag],abs_error=abs(ref-complex(*measured['value'])),
                       relative_error=abs(ref-complex(*measured['value']))/abs(ref))
            assert row['abs_error']<1e-12 and row['relative_error']<1e-9
            if n<=18:
                full=dense(n,gates)
                for index in (0,1,(1<<n)-1,(1<<n)//3):
                    value=native(n,format(index,f'0{n}b'),exe,3072)['value']
                    np.testing.assert_allclose(complex(*value),full[index],atol=1e-13,rtol=1e-9)
        rows.append(row)
        print(n,row.get('relative_error'),flush=True,file=sys.stderr)
    print(json.dumps(rows,indent=2))


if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
