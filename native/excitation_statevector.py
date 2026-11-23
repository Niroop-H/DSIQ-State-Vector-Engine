"""Direct complex128 state vector in a fixed-excitation basis, without truncation.

Input uses the native gate schema. Initial X gates prepare a basis state from
vacuum. Subsequent fSim, SWAP, P, RZ, CZ and CP gates preserve excitation count.
Qubit zero is the least significant bit. See benchmarks/global/excitation_check.py.
"""
import itertools
import json
import math
import sys
import time

import numpy as np


def execute(n, gates, queries, max_states=50000, max_work=100_000_000):
    if type(n) is not int or not 1 <= n <= 128:
        raise ValueError("Register width outside [1,128]")
    if type(max_states) is not int or not 1 <= max_states <= 50000:
        raise ValueError("Invalid coefficient budget")
    if type(max_work) is not int or not 1 <= max_work <= 100_000_000:
        raise ValueError("Invalid work budget")
    if not isinstance(gates, list) or len(gates) > 100000:
        raise ValueError("Invalid gate count")
    if not isinstance(queries, list) or len(queries) > 50000 or any(
        not isinstance(b, str) or len(b) != n or set(b) - {"0","1"} for b in queries
    ):
        raise ValueError("Invalid amplitude queries")

    start = time.perf_counter()
    prepared = 0
    operations = []
    parameters = {"x": (), "swap": (), "cz": (), "p": ("theta",), "rz": ("theta",),
                  "cp": ("theta",), "fsim": ("theta","phi")}
    for gate in gates:
        name, q, controls = gate["name"], gate["q"], gate["controls"]
        if name not in parameters or set(gate) != {"name","q","controls",*parameters[name]}:
            raise ValueError("Unsupported gate or parameters")
        if type(q) is not int or not 0 <= q < n or not isinstance(controls,list):
            raise ValueError("Invalid operands")
        if len(controls) != int(name in {"swap","cz","cp","fsim"}) or any(
            type(c) is not int or not 0 <= c < n or c == q for c in controls
        ):
            raise ValueError("Invalid gate arity or wire")
        for key in parameters[name]:
            if type(gate[key]) not in (int,float) or not math.isfinite(gate[key]):
                raise ValueError("Invalid gate angle")
        if name == "x":
            if operations:
                raise ValueError("X allowed only in initial basis preparation")
            prepared ^= 1 << q
        else:
            operations.append(gate)

    weight = prepared.bit_count()
    size = math.comb(n, weight)
    if size > max_states or size * (len(operations) + min(weight,n-weight) + 1) > max_work:
        raise ValueError(f"Sector exceeds budget ({size} coefficients)")
    # Enumerate holes for near-full occupation, preserving logical bit order.
    flip = (1 << n)-1 if weight > n//2 else 0
    basis = [flip ^ sum(1 << q for q in occupied)
             for occupied in itertools.combinations(range(n),min(weight,n-weight))]
    index = {word:i for i,word in enumerate(basis)}
    state = np.zeros(size, dtype=np.complex128)
    state[index[prepared]] = 1
    for gate in operations:
        name, q = gate["name"], 1 << gate["q"]
        theta = gate.get("theta",0)
        if name in ("p","rz"):
            occupied = np.fromiter((bool(word & q) for word in basis),bool,count=size)
            if name == "rz":
                state *= np.exp(-0.5j*theta)
            state[occupied] *= np.exp(1j*theta)
            continue
        c = 1 << gate["controls"][0]
        if name in ("cz","cp","fsim"):
            both = np.fromiter((word & (c|q) == (c|q) for word in basis),bool,count=size)
            phase = -1 if name == "cz" else np.exp(1j*(theta if name == "cp" else -gate["phi"]))
            state[both] *= phase
        if name in ("fsim","swap"):
            left = np.fromiter((i for i,word in enumerate(basis) if word & c and not word & q),int)
            right = np.fromiter((index[basis[i] ^ c ^ q] for i in left),int)
            a,b = state[left],state[right]
            if name == "swap":
                state[left],state[right] = b,a
            else:
                cos, mix = math.cos(theta), -1j*math.sin(theta)
                state[left],state[right] = cos*a + mix*b, mix*a + cos*b
    values = []
    for bits in queries:
        i = index.get(int(bits,2))
        z = state[i] if i is not None else 0j
        values.append([z.real,z.imag])
    return dict(mode="excitation-statevector", coefficients=size, weight=weight,
                norm=float(np.vdot(state,state).real), amplitudes=values,
                elapsed_seconds=time.perf_counter()-start)


if __name__ == "__main__":
    try:
        result = execute(**json.load(sys.stdin))
        if sys.platform.startswith("linux"):
            import resource
            result["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        print(json.dumps(result,allow_nan=False))
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        print(json.dumps({"error":str(exc)}))
        sys.exit(2)
