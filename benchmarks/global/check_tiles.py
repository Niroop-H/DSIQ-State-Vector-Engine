import argparse
import json
import math
import multiprocessing
from pathlib import Path
import time

from compare_routes import native
from check_contraction import get_terms, plan, contract_slice


def contract_chunk(job):
    terms, schedule, start, stop = job
    fixed=schedule['fixed']
    vals=[]
    for index in range(start,stop):
        assignment={wire:(index>>j)&1 for j,wire in enumerate(fixed)}
        vals.append(contract_slice(terms,schedule['order'],assignment))
    return complex(math.fsum(x.real for x in vals),math.fsum(x.imag for x in vals))


def check_wide(exe,n,workers):
    terms,gates,sha=get_terms(n,'0'*n)
    measured=native(n,'0'*n,exe,2048,n-3)
    if 'value' not in measured:
        raise RuntimeError(measured)
    schedule=plan(terms,20)
    start=time.perf_counter()
    count=schedule['slices']
    tasks=((terms,schedule,i,min(i+8,count)) for i in range(0,count,8))
    with multiprocessing.Pool(workers) as pool:
        sums=list(pool.imap(contract_chunk,tasks))
    ref=complex(math.fsum(x.real for x in sums),math.fsum(x.imag for x in sums))
    err=abs(ref-complex(*measured['value']))
    assert err<1e-12 and err<1e-9*abs(ref)
    return dict(n=n,sha256=sha,gates=len(gates),native=measured,low_bits=n-3,
                coefficient_bytes=16*(1<<(n-3)),reference=[ref.real,ref.imag],
                reference_seconds=time.perf_counter()-start,reference_workers=workers,
                reference_slices=count,abs_error=err,relative_error=err/abs(ref))


def boundary_tiles(exe):
    n=50
    lo=10
    zero='0'*n
    t0,_,sha=get_terms(n,zero)
    t1,_,_=get_terms(n,'1'*n)
    rows=[]
    for u,v in ((0,0),(7,7),(1048579,1048577),(373007,373005)):
        assignment={k:(u>>(k-lo))&1 for k in range(lo,n)}
        assignment.update({n+k:(v>>(k-lo))&1 for k in range(lo,n)})
        order=list(range(lo))+list(range(n,n+lo))
        ref=sum(contract_slice(ts,order,assignment) for ts in (t0,t1))
        obs=native(n,zero,exe,32,lo,u,v)
        err=abs(ref-complex(*obs['partial_tile']))
        assert err<=1e-9*abs(ref)
        rows.append(dict(u=u,v=v,reference=[ref.real,ref.imag],observed=obs,
                         relative_error=err/abs(ref)))
    pilot=native(50,zero,exe,2048,27,0,0)
    return dict(n=n,sha256=sha,checked_tile_low_bits=lo,checks=rows,
                pilot_low_bits=27,pilot=pilot,tiles_required=2**45,complete=False,amplitude=None)


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('executable',type=Path)
    ap.add_argument('mode',choices=['target','30'])
    ap.add_argument('--workers',type=int,default=4)
    args=ap.parse_args()
    exe=args.executable.resolve()
    value=boundary_tiles(exe) if args.mode=='target' else check_wide(exe,30,args.workers)
    print(json.dumps(value,indent=2))
