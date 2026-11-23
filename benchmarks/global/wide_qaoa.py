"""Exact two-layer path-graph QAOA, checked by spatial transfer of spin histories."""
import itertools
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys

import numpy as np


def fixture(n, seed):
    rng = random.Random(seed)
    edges = [[rng.uniform(-1.2, 1.2) for _ in range(n-1)] for _ in range(2)]
    mixer = [[rng.uniform(-1, 1) for _ in range(n)] for _ in range(2)]
    probes = [format(rng.getrandbits(n), f'0{n}b') for _ in range(8)]
    gates = [dict(name='h', q=q, controls=[]) for q in range(n)]
    for costs, angles in zip(edges, mixer):
        for parity in (0, 1):
            for q in range(parity, n-1, 2):
                cx = dict(name='cx', q=q+1, controls=[q])
                gates.extend([cx, dict(name='rz', q=q+1, controls=[], theta=costs[q]), cx])
        gates.extend(dict(name='rx', q=q, controls=[], theta=t) for q,t in enumerate(angles))
    return dict(n=n, gates=gates, queries=probes), edges, mixer


def amplitude(bits, edges, mixer):
    # A history holds the two bits immediately before the two mixer layers.
    histories = list(itertools.product((0,1), repeat=2))
    prev = None
    for q, bit in enumerate(reversed(bits)):
        weights = []
        for x, y in histories:
            value = 1 / math.sqrt(2)
            for a, b, t in ((x,y,mixer[0][q]), (y,int(bit),mixer[1][q])):
                value *= math.cos(t/2) if a==b else -1j*math.sin(t/2)
            weights.append(value)
        if prev is None:
            prev = np.array(weights)
        else:
            links = np.array([[np.exp(-0.5j*sum(
                edges[k][q-1]*(1 if left[k]==right[k] else -1) for k in range(2)
            )) for right in histories] for left in histories])
            prev = (prev @ links)*weights
    return sum(prev)


def check(n, seed, root):
    doc, edges, mixer = fixture(n, seed)
    proc = subprocess.run([sys.executable, str(root/'native/mps_exact.py')],
                          input=json.dumps(doc), text=True, capture_output=True,
                          env=dict(os.environ,OPENBLAS_NUM_THREADS='1'), timeout=120)
    r = json.loads(proc.stdout)
    if proc.returncode:
        return dict(n=n,seed=seed,passed=False,error=r)
    ref=np.array([amplitude(bits, edges, mixer) for bits in doc['queries']])
    actual=np.array([complex(a['real'],a['imag']) for a in r['amplitudes']])
    error=abs(actual-ref)
    rel=float(max(error/abs(ref)))
    return dict(n=n, seed=seed, probes=len(ref), gates=len(doc['gates']),
                max_relative=rel, max_absolute=float(max(error)), norm=r['norm'],
                passed=rel<1e-9 and max(error)<1e-13 and abs(r['norm']-1)<1e-12)


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    rows=[check(n,381011+n,root) for n in (8,50,75,100)]
    print(json.dumps(rows,indent=2))
    sys.exit(any(not r['passed'] for r in rows))
