# Diamond #70 forward-prefix verification

At width 100 and circuit seed 8377, the all-zero amplitude after the first 750 gates was evaluated in both directions. The real-valued forward prefix and its adjoint have the same all-zero matrix element. Each calculation included every slice and used the batched matrix-product kernel.

| Evaluation | Completed slices | Real amplitude | Imaginary amplitude | Predicted explicit array bytes | Seconds |
|---|---:|---:|---:|---:|---:|
| Forward, contraction seed 873 | 32 | 5.828866999687367e-9 | 0 | 261095424 | 81.422 |
| Adjoint, relabeled wires, contraction seed 42 | 128 | 5.828866999687377e-9 | 0 | 243335168 | 204.547 |

Windows x64, single-threaded OpenBLAS, FP64, 256 MiB explicit-array forecast budget per run. Both directions use the same engine. The separate small dense regression covered 12 amplitude comparisons and observed maximum absolute error 6.94e-17. At 100 layers the forward compact planner with one trial and seed 873 exceeded the 256-slice allowance. This prefix result does not fulfill #70.

```sh
OPENBLAS_NUM_THREADS=1 python tests/diamond70-slicing.py --depth 5
OPENBLAS_NUM_THREADS=1 python tests/diamond70-slicing.py --depth 5 --reverse --seed 42
```
