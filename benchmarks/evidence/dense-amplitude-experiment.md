# Dense two-layer QAOA amplitude experiment

The target is the all-zero amplitude of the same 50-qubit, 587-edge graph in the [wide QAOA benchmark](./qaoa-wide.md). Its 3,672 gates have SHA-256 digest `637560482d7262597b75c8c149f0b930dad702f32a14aff493d32c5665d3483f` under the JSON serialization in the verification script. The benchmark rebuilds the H, CNOT, RZ and RX stream from the graph and angles and compares it gate for gate before running either method.

## Native selected-amplitude method

The standalone C++20 CPU executable accepts two uniform-angle ZZ cost layers and two uniform-angle RX mixer layers after a uniform superposition. It computes a requested computational-basis amplitude in complex double precision. Both the prepared state and the circuit are invariant under flipping all bits, so complementary basis amplitudes coincide. The direct implementation stores one coefficient per complementary pair after the first cost layer, applies the first mixer, and contracts the second cost and mixer layers into the requested output row.

The tiled implementation fixes high bits on both sides of the first mixer. An exact-in-form sum over all tiles gives the same amplitude. Keeping L low bits requires a coefficient buffer of 16 × 2^L bytes. The number of high-bit pairs is 2^(2(n−L)−1). Different output tiles can reuse the prepared low-bit buffer for the same input prefix. A single-tile request emits a value labeled `partial_tile`. Only the full execution modes emit an amplitude. All methods use floating-point arithmetic.

## Independent contraction

The Python implementation expresses the same amplitude as a sum over two binary spin variables per qubit. The factors are the initial state weights, the two layers of ZZ phases and the matrix elements of both mixers. The code selects a variable-elimination order, conditions variables when a product would exceed the tensor width budget, and sums all conditional contractions with compensation. The reference has no dependency on the C++ kernel. Small cases are also checked against gate-by-gate dense NumPy states, including nonzero output strings.

## Completed amplitudes

All values below are for the all-zero output. The NumPy elimination sums every required slice for each verification. The two native methods and the reference evaluate the same circuit in different arithmetic orders.

| Qubits | Edges | Native seconds | Relative difference from independent contraction |
|---:|---:|---:|---:|
| 24 | 133 | 2.12 | 2.120e-15 |
| 28 | 181 | 30.66 | 4.324e-15 |
| 30 | 210 | 60.59 | 3.741e-15 |

The 30-qubit run used 2 GiB for the coefficient buffer and returned (3.698356417013739e-05+1.528647728871396e-05j). The reference summed 4,096 slices. Timings are single local measurements.

## Resource boundary on the unchanged target

* Direct complement storage needs 9,007,199,254,740,992 coefficient bytes (8 PiB).
* With 27 low bits and a 2 GiB coefficient buffer, the tiled native route needs 35,184,372,088,832 tiles. One of these large tiles was executed. Four additional smaller tiles on the same circuit were numerically verified against the independent conditional contractions. Individual tile values depend on the partition and cannot stand in for the requested amplitude.
* With a maximum of 20 axes per tensor product, the variable-elimination planner selected 46 conditioned spins, giving 70,368,744,177,664 slices. Five slices were executed. These counts describe specific schedules and do not establish a complexity lower bound for the circuit.
* The 50-qubit amplitude remains unknown in this experiment. The evidence records it as null.

## Reproduction

From the repository root, use Python with NumPy and a C++20 compiler. The last command is a longer independent verification and can use multiple CPU cores. The 2 GiB limit refers to the native coefficient buffer. Python workers consume additional memory. Timings are individual local runs.

```sh
g++ -std=c++20 -O3 -march=native native/qaoa_amplitude.cpp -o /tmp/qaoa-amplitude
export OPENBLAS_NUM_THREADS=1
python benchmarks/global/check_contraction.py
python benchmarks/global/compare_routes.py /tmp/qaoa-amplitude
python benchmarks/global/check_tiles.py /tmp/qaoa-amplitude target
python benchmarks/global/check_tiles.py /tmp/qaoa-amplitude 30 --workers 6
```

The executable reads `n m gamma0 beta0 gamma1 beta1 output_bitstring` followed by m undirected edge pairs on standard input. Angles use the gate convention exp(−i theta P/2). Wire zero is the rightmost output bit. Optional positional arguments are the coefficient budget in MiB, the number of low bits, and a pair of tile indices. For example, for a two-wire graph with one edge, this asks for the full amplitude of 01.

```sh
printf '2 1 0.8 0.3 1.1 -0.2 01\n0 1\n' | /tmp/qaoa-amplitude
```

[Raw numerical results](./dense-amplitude-experiment.json)
