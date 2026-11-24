"""Check amplitudes of the original connected fixture by reversing its monomial suffix."""
import cmath
import json
import math
import pathlib
import subprocess
import time
import random
import tempfile

fixture = pathlib.Path(__file__).with_name("connected-frame-fixture.mjs")


def check(n):
    start = time.perf_counter()
    rng = random.Random(772851+n)
    queries = [format(i, f"0{n}b") for i in (0, (1<<n)-1, 1, 1<<(n-1))]
    queries += [format(rng.getrandbits(n), f"0{n}b") for _ in range(256)]
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory)/"queries.json"
        path.write_text(json.dumps(queries))
        raw = subprocess.check_output(["node", str(fixture), str(n), str(path)])
    data = json.loads(raw)
    gates = data["gates"]
    split = max(i for i, gate in enumerate(gates) if gate["name"] == "ry") + 1
    blocks = [[1+0j] + [0j] * ((1 << min(2, n-q)) - 1) for q in range(0, n, 2)]
    for gate in gates[:split]:
        q, op = gate["q"], gate["name"]
        state = blocks[q//2]
        bit = 1 << (q%2)
        for i in range(len(state)):
            if i & bit:
                continue
            j = i | bit
            a, b = state[i], state[j]
            t = gate["theta"]/2
            if op == "ry":
                state[i], state[j] = math.cos(t)*a-math.sin(t)*b, math.sin(t)*a+math.cos(t)*b
            elif op == "rz":
                state[i], state[j] = cmath.exp(-1j*t)*a, cmath.exp(1j*t)*b
            elif op == "cx":
                c, = gate["controls"]
                assert c//2 == q//2
                if i & (1 << (c%2)):
                    state[i], state[j] = b, a
            else:
                raise ValueError(op)
    # Each suffix gate permutes basis indices or multiplies by a unit phase.
    assert all(abs(a)>0 for block in blocks for a in block)
    max_rel = max_abs = 0.
    for probe in data["probes"]:
        index = int(probe["bits"], 2)
        amplitude = 1+0j
        for gate in reversed(gates[split:]):
            q, op = gate["q"], gate["name"]
            b = (index >> q) & 1
            if op == "s":
                amplitude *= 1j if b else 1
                continue
            c, = gate["controls"]
            control = (index >> c) & 1
            if op == "cx":
                index ^= control << q
            elif op == "cz":
                amplitude *= -1 if control and b else 1
            elif op == "swap":
                if b != control:
                    index ^= (1 << c) | (1 << q)
            else:
                raise ValueError(op)
        for block in blocks:
            amplitude *= block[index & (len(block)-1)]
            index //= len(block)
        error = abs(complex(probe["real"],probe["imag"])-amplitude)
        assert math.isfinite(error) and error <= 1e-13 and error/abs(amplitude) <= 1e-10
        max_rel = max(max_rel,error/abs(amplitude))
        max_abs = max(max_abs,error)
    assert len(data["probes"]) == 324 and abs(data["norm"]-1)<1e-12
    return dict(n=n,gates=len(gates),probes=324,engine_peak_rss_kib=data["enginePeakRssKiB"],max_relative=max_rel,max_absolute=max_abs,
                norm=data["norm"],seconds=time.perf_counter()-start)


if __name__ == "__main__":
    print(json.dumps([check(n) for n in (25,30,40,50,75,100)], indent=2))
