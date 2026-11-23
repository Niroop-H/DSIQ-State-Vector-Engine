"""Holdout Grover probes for a seeded marked state with an analytical reference."""
import argparse
import json
import random
import subprocess
from pathlib import Path
import mpmath as mp

def check(exe, n, rounds):
    rng = random.Random(750743 + n)
    target = rng.randrange(1 << n)
    gates = []

    def gate(name, q, cs=()):
        gates.append(' '.join(map(str, [name, q, 0, len(cs), *cs])))

    def mcphase():
        gate('h', n - 1)
        gate('mcx', n - 1, range(n - 1))
        gate('h', n - 1)
    for q in range(n):
        gate('h', q)
    for _ in range(rounds):
        zeros = [q for q in range(n) if not target >> q & 1]
        for q in zeros:
            gate('x', q)
        mcphase()
        for q in zeros:
            gate('x', q)
        for q in range(n):
            gate('h', q)
            gate('x', q)
        mcphase()
        for q in range(n):
            gate('x', q)
            gate('h', q)
    probes = sorted({0, target, (1 << n) - 1, *rng.sample(range(1 << n), 32)})
    payload = '\n'.join([f'{n} {len(gates)} {len(probes)}', *gates, *map(str, probes)])
    obs = json.loads(subprocess.run([exe], input=payload, text=True, capture_output=True, timeout=120, check=True).stdout)
    with mp.workdps(60):
        # The implemented diffusion operator contributes a minus sign per round.
        theta = mp.asin(1 / mp.sqrt(1 << n))
        phi = (2 * rounds + 1) * theta
        marked = (-1) ** rounds * mp.sin(phi)
        background = (-1) ** rounds * mp.cos(phi) / mp.sqrt((1 << n) - 1)
        expected = [marked if i == target else background for i in probes]
        errors = [abs(mp.mpc(*x) - y) for x, y in zip(obs['values'], expected, strict=True)]
        absolute = float(max(errors))
        relative = float(max((e / abs(y) for e, y in zip(errors, expected))))
    return dict(n=n, rounds=rounds, marked=target, probes=len(probes), gates=len(gates), ms=obs['ms'], max_abs=absolute, max_relative=relative, passed=absolute <= 1e-12 and relative <= 1e-09)
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    exe = parser.parse_args().executable.resolve()
    rows = [check(exe, n, r) for n, r in ((12, 37), (16, 151), (20, 607), (24, 2071))]
    print(json.dumps(rows, indent=2))
    raise SystemExit(any((not r['passed'] for r in rows)))
