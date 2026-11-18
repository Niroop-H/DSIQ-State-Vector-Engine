"""Optional independent high-precision reference generator (test only).
Requires mpmath. No simulator runtime import. Use the exact IEEE-754 input,
not the intended symbolic value of pi, to check raw argument reduction.
"""
import json
import math
import mpmath as mp
mp.mp.dps = 400
cases = [1e6*math.pi, -1e6*math.pi, 1e20, -1e20, 1e100, -1e100,
         1e308, -1e308, 1e6*math.pi+0.123456789]
result = []
for x in cases:
    a, b = x.as_integer_ratio()
    t = mp.mpf(a) / mp.mpf(b)
    result.append([x, float(mp.cos(t)), float(mp.sin(t))])
print(json.dumps(result))
