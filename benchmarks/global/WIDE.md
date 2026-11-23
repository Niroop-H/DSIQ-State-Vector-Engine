# Wide non-Clifford verification

Run from the checkout root on Linux with Python 3.12 and NumPy 2.3.5.

```sh
OPENBLAS_NUM_THREADS=1 python benchmarks/global/wide_statevector.py
OPENBLAS_NUM_THREADS=1 python benchmarks/global/excitation_check.py > excitation-results.json
```

The first command writes wide-results.json. It runs the existing native untruncated MPS backend in separate processes on alternating nearest-neighbor CZ layers with arbitrary local RY and phase gates. A separate spatial path sum checks eight amplitudes at each width/depth, including relative errors on tiny outputs. A dense causal-cone calculation checks a central X observable. There is one seed per width/depth. Each engine process has a 120-second timeout and 2 GiB address-space limit.

The second command exercises the native direct excitation-sector state vector. It compares every reachable coefficient in two-excitation circuits against a separately implemented two-particle coordinate calculation. It cross-checks with a full dense simulation at eight qubits and exercises additional excitation sectors at six qubits. The two references were authored with these tests. External blind validation remains open. Timings in the JSON files are individual observations.

## Direct engine entry point

```sh
printf '%s\n' '{"n":50,"gates":[{"name":"x","q":0,"controls":[]},{"name":"fsim","q":49,"controls":[0],"theta":0.7,"phi":0.2}],"queries":["00000000000000000000000000000000000000000000000001","10000000000000000000000000000000000000000000000000"]}' | python native/excitation_statevector.py
```

These two outputs are cos(0.7) and -i sin(0.7). Initial X gates prepare a basis state. Subsequent fSim, SWAP, P, RZ, CZ and CP gates can act on any valid wires. The standalone Python entry point evolves every coefficient in the fixed-excitation basis in complex128. For width n and excitation count k, the coefficient count is binomial(n,k). The default ceiling is 50,000 coefficients plus a work budget. Unsupported gates and over-budget circuits return an error and nonzero exit status. The native backend is explicitly invoked and has no browser integration.
