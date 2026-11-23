"""Width-by-width accuracy audit. Angles are the exact binary64 fixture inputs."""
import argparse
import itertools
import json
import math
import platform
import sys
from importlib.metadata import version
from pathlib import Path

import mpmath as mp
import numpy as np

from excitation_check import compare as sector_check
from path_compare import worker
from wide_qaoa import fixture

HISTORIES = list(itertools.product((0, 1), repeat=2))


def reference(edges, mixer, probes):
    # Sweep across space. Each local history has a bit before each mixer.
    # Both diagonal cost layers couple only neighboring histories.
    with mp.workdps(60):
        columns = []
        for q in range(len(mixer[0])):
            rotations = [(mp.cos(mp.mpf(row[q])/2), -1j*mp.sin(mp.mpf(row[q])/2))
                         for row in mixer]
            local = [[rotations[0][x^y]*rotations[1][y^b]/mp.sqrt(2)
                      for x,y in HISTORIES] for b in (0,1)]
            if q:
                links = [[mp.exp(-0.5j * sum(mp.mpf(edges[k][q-1]) *
                            (1 if left[k]==right[k] else -1) for k in range(2)))
                          for left in HISTORIES] for right in HISTORIES]
            columns.append((local, links if q else None))
        values = []
        for bits in probes:
            state = None
            for bit,(local,links) in zip(reversed(bits),columns,strict=True):
                weights = local[int(bit)]
                state = weights if state is None else [
                    w*sum(a*b for a,b in zip(state,row)) for w,row in zip(weights,links)]
            values.append(sum(state))
        return values


def score(observed, ref):
    with mp.workdps(60):
        values = [mp.mpc(x,y) for x,y in observed['amplitudes']]
        error = [abs(a-b) for a,b in zip(values,ref,strict=True)]
        relative = [d/abs(v) for d,v in zip(error,ref) if v]
        absolute, rel = float(max(error)), float(max(relative,default=0))
    norm_error = abs(observed['norm']-1)
    return dict(max_abs=absolute,max_relative=rel,norm_error=norm_error,
                passed=all(map(math.isfinite,(absolute,rel,norm_error))) and
                absolute<1e-13 and rel<1e-9 and norm_error<1e-12)


def main(external):
    engines = ['dsiq','quimb'] if external else ['dsiq']
    report = dict(python=platform.python_version(),numpy=np.__version__,mpmath=mp.__version__,
                  reference_decimal_digits=60,widths=[])
    if external:
        report['quimb']=version('quimb')
    for n in range(1,101):
        seed=721308+n
        doc,edges,mixer=fixture(n,seed)
        if n<=8:
            doc['queries']=[format(i,f'0{n}b') for i in range(1<<n)]
        else:
            doc['queries']=list(dict.fromkeys(['0'*n,'1'*n,'01'*(n//2)+'0'*(n%2),*doc['queries']]))
        ref=reference(edges,mixer,doc['queries'])
        row=dict(n=n,path_seed=seed,probes=len(ref),path={})
        for engine in engines:
            try:
                row['path'][engine]=score(worker(engine,doc),ref)
            except Exception as exc:
                row['path'][engine]=dict(passed=False,error=repr(exc))
        if n>=3:
            row['sector']=sector_check(n,213946+n)
        report['widths'].append(row)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--quimb',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=main(args.quimb)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    sys.exit(any(not all(v['passed'] for v in r['path'].values()) or
                 not r.get('sector',{}).get('passed',True) for r in result['widths']))
