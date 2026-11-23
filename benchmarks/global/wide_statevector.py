"""Check wide connected circuits with independent path sums and dense local observables.

Run from the repository root with OPENBLAS_NUM_THREADS=1 python benchmarks/global/wide_statevector.py.
"""
import json
import math
import os
from pathlib import Path
import platform
import random
import resource
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "native/mps_exact.py"


def fixture(n, depth, seed):
    rng = random.Random(seed)
    angles = []
    gates = []
    for layer in range(depth + 1):
        row = []
        for q in range(n):
            turn = rng.uniform(0.6, 2.5)
            phase = rng.uniform(-2.8, 2.8)
            row.append((turn, phase))
            gates.extend([dict(name="ry", controls=[], q=q, theta=turn),
                          dict(name="p", controls=[], q=q, theta=phase)])
        angles.append(row)
        if layer < depth:
            for left in range(layer % 2, n - 1, 2):
                gates.append(dict(name="cz", controls=[left], q=left + 1))
    bits = ["0" * n, "1" * n] + [format(rng.getrandbits(n), f"0{n}b") for _ in range(6)]
    return angles, gates, bits


def local_matrix(pair):
    angle, phase = pair
    c, s = math.cos(angle / 2), math.sin(angle / 2)
    z = np.exp(1j * phase)
    return np.array([[c, -s], [s*z, c*z]])


def reference_amplitudes(angles, bits):
    # Sum over time histories one physical site at a time. A CZ contributes
    # -1 exactly when both histories occupy 1 at its active layer.
    depth, n = len(angles) - 1, len(angles[0])
    histories = np.arange(2**depth)
    spin = [(histories >> t) & 1 for t in range(depth)]
    signs = []
    for parity in (0, 1):
        mask = sum(1 << t for t in range(parity, depth, 2))
        intersections = (histories[:, None] & histories[None, :]) & mask
        signs.append(np.array([[(-1)**int(v).bit_count() for v in row]
                               for row in intersections], dtype=complex))
    partial = np.ones((len(histories), len(bits)), complex)
    for q in range(n):
        weight = np.ones(len(histories), complex)
        previous = 0
        for t, current in enumerate(spin):
            weight *= local_matrix(angles[t][q])[current, previous]
            previous = current
        output = np.array([int(b[-1-q]) for b in bits])
        finish = local_matrix(angles[-1][q])[output[None, :], previous[:, None]]
        if q:
            partial = signs[(q-1) % 2] @ partial
        partial *= weight[:, None] * finish
    return partial.sum(axis=0)


def reference_x(angles, center):
    # Each CZ layer expands the backwards causal cone by at most one site.
    depth, n = len(angles) - 1, len(angles[0])
    lo, hi = max(0, center-depth), min(n, center+depth+1)
    indices = np.arange(1 << (hi-lo))
    state = np.zeros(len(indices), complex)
    state[0] = 1
    for t, row in enumerate(angles):
        for q in range(lo, hi):
            stride = 1 << (q-lo)
            pairs = state.reshape(-1, 2, stride)
            pairs[:] = local_matrix(row[q]) @ pairs
        if t < depth:
            for q in range(lo, hi-1):
                if q % 2 == t % 2:
                    state[((indices >> (q-lo)) & 3) == 3] *= -1
    return float(np.vdot(state, state[indices ^ (1 << (center-lo))]).real)


def limit_worker():
    limit = 2 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def run_case(n, depth, seed):
    angles, gates, bits = fixture(n, depth, seed)
    center = n // 2
    query = dict(n=n, gates=gates, queries=bits, paulis=["I"*(n-1-center)+"X"+"I"*center])
    start = time.monotonic()
    proc = subprocess.run([sys.executable, str(BACKEND)], input=json.dumps(query),
                          text=True, capture_output=True, timeout=120, preexec_fn=limit_worker,
                          env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1"))
    row = dict(qubits=n, entangling_layers=depth, gates=len(gates), seed=seed,
               process_seconds=time.monotonic()-start)
    if proc.returncode:
        return dict(**row, passed=False, error=proc.stdout[-500:] or proc.stderr[-500:])
    result = json.loads(proc.stdout)
    expected = reference_amplitudes(angles, bits)
    actual = np.array([complex(v["real"], v["imag"]) for v in result["amplitudes"]])
    error = abs(actual-expected)
    if np.any(abs(expected) == 0):
        raise ValueError("Relative error undefined for a zero reference")
    relative = error / abs(expected)
    reference = reference_x(angles, center)
    x_error = abs(result["observables"][0]-reference)
    norm_error = abs(result["norm"]-1)
    passed = bool(max(error) <= 1e-13 and max(relative) <= 1e-9
                  and x_error <= 1e-12 and norm_error <= 1e-12)
    return dict(**row, passed=passed, max_abs=float(max(error)), max_relative=float(max(relative)),
                x_error=x_error, norm_error=norm_error, peak_rss_kib=result["processPeakRSSKiB"],
                backend=result["stats"]["mode"], bond=result["stats"]["actualMaxBond"],
                probes=[dict(bits=b, reference=[v.real,v.imag], actual=[a.real,a.imag])
                        for b,v,a in zip(bits,expected,actual,strict=True)],
                x_actual=result["observables"][0], x_reference=reference)


if __name__ == "__main__":
    report = dict(python=platform.python_version(), numpy=np.__version__, cases=[])
    widths_depths = [(8, 2), (8, 4)] + [(n, d) for n in (50, 100) for d in (2, 4, 6)]
    for base in (87001, 34213, 99041):
        for n, depth in widths_depths:
            seed = base + 100 * n + depth
            try:
                row = run_case(n, depth, seed)
            except Exception as exc:
                row = dict(qubits=n, entangling_layers=depth, seed=seed, passed=False, error=repr(exc))
            report["cases"].append(row)
            print(n, depth, seed, row["passed"], row.get("max_relative"), row.get("error"), flush=True)
    Path("wide-results.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    sys.exit(any(not c["passed"] for c in report["cases"]))
