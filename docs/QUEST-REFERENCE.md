# Dense QuEST reference for Diamond #54

The comparison uses QuEST 3.7.0 CPU double precision at revision `d4f75f724993b4af8e43a796e3c09ce24ae11670`. Both engines process the same connected gate list. The Diamond harness bisects the same circuit, expands each crossing control as P0 ⊗ I + P1 ⊗ U, and lowers crossing SWAPs to three CNOTs. QuEST executes all branch subcircuits without renormalizing the projectors. The reference recombines complex amplitudes coherently, in basis order, from both registers and every branch. The comparator visits all coefficients and checks both norms. The standalone `quest` option still runs one dense QuEST register; its 30-qubit allocation alone needs 16 GiB.

On Linux, from the DSIQ checkout, with the numerical reference dependencies and GCC installed:

```sh
git clone https://github.com/QuEST-Kit/QuEST.git /tmp/dsiq-quest-src
git -C /tmp/dsiq-quest-src checkout --detach d4f75f724993b4af8e43a796e3c09ce24ae11670
cmake -S /tmp/dsiq-quest-src -B /tmp/dsiq-quest-build -DCMAKE_BUILD_TYPE=Release \
  -DPRECISION=2 -DGPUACCELERATED=OFF -DDISTRIBUTED=OFF -DMULTITHREADED=OFF \
  -DUSER_SOURCE="$PWD/tests/quest-vector.c"
cmake --build /tmp/dsiq-quest-build --config Release
export DSIQ_QUEST_VECTOR=/tmp/dsiq-quest-build/demo
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python -B tests/connected-frame-audit.py 25 quest
python -B tests/connected-frame-audit.py 30 quest-cut
node --max-old-space-size=3072 tests/diamond.test.mjs diamond-results.json
```

The standalone 25-qubit run checks the integration. The release harness evaluates #54 at exactly 30 qubits when the QuEST executable is configured. An incomplete reference stream, a failed reference process or a numerical mismatch rejects the comparison. The Linux harness builds its DSIQ reconstruction library with GCC. Windows can supply the equivalent native library through `DSIQ_FRAME_STREAM_LIBRARY`.
