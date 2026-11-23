"""Probe MPS planning and bounded adaptive replay on two-layer dense random graphs."""
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import numpy as np


def make_circuit(n):
    adjacency=np.random.default_rng(10).integers(0,2,(n,n))
    edges=[(i,j) for i in range(n) for j in range(i+1,n) if adjacency[i,j]]
    gates=[dict(name='h',q=i,controls=[]) for i in range(n)]
    for layer in range(2):
        for i,j in edges:
            cx=dict(name='cx',q=j,controls=[i])
            gates.extend([cx,dict(name='rz',q=j,controls=[],theta=2*(.317+.241*(2+layer))),cx])
        gates.extend(dict(name='rx',q=i,controls=[],theta=2*(.317+.241*layer)) for i in range(n))
    return edges, gates


def check(n, root):
    edges, gates = make_circuit(n)
    payload=dict(n=n,gates=gates,queries=['0'*n])
    p=subprocess.run([sys.executable,str(root/'native/mps_exact.py')],input=json.dumps(payload),
                     text=True,capture_output=True,timeout=120,env=dict(os.environ,OPENBLAS_NUM_THREADS='1'))
    with tempfile.TemporaryDirectory() as temp:
        circuit=Path(temp)/'circuit.json'
        circuit.write_text(json.dumps(dict(n=n,gates=gates,indices=[0])))
        try:
            proc=subprocess.run(['node','--max-old-space-size=256',
                str(root/'benchmarks/global/adaptive_probe.mjs'),str(circuit)],capture_output=True,
                text=True,timeout=30,cwd=temp)
            adaptive=dict(exit_code=proc.returncode,result=json.loads(proc.stdout) if proc.stdout else proc.stderr[-800:])
        except subprocess.TimeoutExpired:
            adaptive=dict(timeout_seconds=30)
    return dict(n=n, edges=len(edges),gates=len(gates),native_exit=p.returncode,
                native=json.loads(p.stdout),adaptive=adaptive)


if __name__=='__main__':
    print(json.dumps([check(n,Path.cwd()) for n in (50,75,100)],indent=2))
