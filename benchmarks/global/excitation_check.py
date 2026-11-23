"""Verify the direct sector engine against dense small states and a two-particle oracle."""
import itertools
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import time

import numpy as np

ENGINE = Path(__file__).resolve().parents[2] / "native/excitation_statevector.py"


def run(request):
    result = subprocess.run([sys.executable,str(ENGINE)], input=json.dumps(request), text=True,
                            capture_output=True, timeout=120)
    return result.returncode, json.loads(result.stdout)


def fixture(n, seed=None):
    rng = random.Random(4083+n if seed is None else seed)
    gates = [dict(name="x",q=q,controls=[]) for q in (0,n//2)]
    for layer in range(14):
        wires = list(range(n))
        if layer == 1:
            wires = wires[1:] + wires[:1]
        elif layer > 1:
            rng.shuffle(wires)
        for c,q in zip(wires[::2],wires[1::2]):
            gates.append(dict(name="fsim",controls=[c],q=q,theta=rng.uniform(0.3,1.25),
                              phi=rng.uniform(-2,2)))
        for q in wires:
            gates.append(dict(name="rz",controls=[],q=q,theta=rng.uniform(-2,2)))
    gates.extend([dict(name="swap",q=0,controls=[1]),dict(name="cz",q=2,controls=[0]),
                  dict(name="cp",q=1,controls=[2],theta=0.73),
                  dict(name="p",q=1,controls=[],theta=-1.04)])
    return gates


def matrix(g):
    name = g["name"]
    t = g.get("theta",0)
    if name == "x": return np.array([[0,1],[1,0]])
    if name == "p": return np.diag([1,np.exp(1j*t)])
    if name == "rz": return np.diag(np.exp(1j*np.array([-t,t])/2))
    if name == "cz": return np.diag([1,1,1,-1])
    if name == "cp": return np.diag([1,1,1,np.exp(1j*t)])
    if name == "swap": return np.eye(4)[[0,2,1,3]]
    c,s = math.cos(t),-1j*math.sin(t)
    return np.array([[1,0,0,0],[0,c,s,0],[0,s,c,0],[0,0,0,np.exp(-1j*g["phi"])]])


def dense(n,gates):
    v = np.zeros((2,)*n,complex)
    v.flat[0] = 1
    for g in gates:
        axes = [n-1-q for q in [*g["controls"],g["q"]]]
        order = axes+[q for q in range(n) if q not in axes]
        m = matrix(g)
        values = m @ v.transpose(order).reshape(len(m),-1)
        v = values.reshape((2,)*n).transpose(np.argsort(order))
    return v.flatten()


def particle_oracle(n,gates):
    # Symmetric coordinate table. Updating a gate on sites c,q reduces to
    # a 2x2 rotation for every third spectator site, plus the occupied pair.
    a = np.zeros((n,n),complex)
    a[0,n//2] = a[n//2,0] = 1
    for g in gates[2:]:
        m, q = matrix(g), g["q"]
        if len(m) == 2:
            a *= m[0,0]
            a[q,:] *= m[1,1]/m[0,0]
            a[:,q] *= m[1,1]/m[0,0]
        else:
            c = g["controls"][0]
            sites = [c,q]
            other = [i for i in range(n) if i not in sites]
            block = np.ix_(sites,other)
            a[block] = m[1:3,1:3] @ a[block]
            a[np.ix_(other,sites)] = a[block].T
            a[c,q] *= m[3,3]
            a[q,c] = a[c,q]
    return a


def compare(n, seed):
    gates = fixture(n, seed)
    pairs = list(itertools.combinations(range(n),2))
    words = [(1<<i)|(1<<j) for i,j in pairs]
    queries = [format(w,f"0{n}b") for w in words]+["0"*n,"1"*n]
    start = time.monotonic()
    code,r = run(dict(n=n,gates=gates,queries=queries))
    elapsed = time.monotonic()-start
    if code: raise RuntimeError(r)
    table = particle_oracle(n,gates)
    expected = np.array([table[i,j] for i,j in pairs]+[0,0])
    if n == 8:
        truth = dense(n,gates)
        np.testing.assert_allclose(expected[:-2],truth[words],rtol=1e-12,atol=1e-14)
    output = np.asarray(r["amplitudes"])
    actual = output[:,0]+1j*output[:,1]
    delta = abs(actual-expected)
    significant = abs(expected)>1e-14
    relative = max(delta[significant]/abs(expected[significant]))
    passed = np.all(actual[-2:] == 0) and max(delta)<=1e-13 and relative<=1e-9 and abs(1-r["norm"])<=1e-12
    return dict(qubits=n,seed=seed,gates=len(gates),mixing_layers=14,coefficients=len(words),
                queries=len(queries),max_abs=float(max(delta)),max_relative=float(relative),
                peak_rss_kib=r["peak_rss_kib"],norm=r["norm"],engine_seconds=r["elapsed_seconds"],process_seconds=elapsed,
                passed=bool(passed))


if __name__ == "__main__":
    for kwargs in [dict(n=100,gates=[dict(name="x",q=i,controls=[]) for i in range(50)]),
                   dict(n=50,gates=[dict(name="h",q=0,controls=[])]),
                   dict(n=50,gates=[dict(name="cz",q=0,controls=[1]),dict(name="x",q=2,controls=[])])]:
        code,r = run(dict(**kwargs,queries=[]))
        if code != 2 or "error" not in r: raise RuntimeError("Expected explicit rejection")
    for weight in (0,1,3,5,6):
        gates = [dict(name="x",q=i,controls=[]) for i in range(weight)] + fixture(6)[2:]
        keys = [format(i,"06b") for i in range(64)]
        code,r = run(dict(n=6,gates=gates,queries=keys))
        if code: raise RuntimeError(r)
        out = np.array(r["amplitudes"])
        np.testing.assert_allclose(out[:,0]+1j*out[:,1],dense(6,gates),rtol=1e-12,atol=1e-14)
    rows = [compare(n, base+n) for base in (4083, 12071, 73519) for n in (8,50,100)]
    print(json.dumps(rows,indent=2,allow_nan=False))
    sys.exit(any(not row["passed"] for row in rows))
