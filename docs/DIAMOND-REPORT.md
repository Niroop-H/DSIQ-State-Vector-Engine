# DSIQ v0.8 — Diamond-105 local run summary

81 PASS / 17 PARTIAL / 1 FAIL / 4 BLOCKED / 2 NOT_RUN. Release eligibility: false. All prior 78 passes retained. New passes #7, #10, #104.

PASS: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 45, 47, 49, 50, 51, 52, 55, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 69, 71, 72, 73, 74, 79, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 104
PARTIAL: 19, 43, 44, 46, 48, 53, 54, 56, 57, 68, 75, 76, 78, 98, 99, 102, 103
FAIL: 70
BLOCKED: 77, 90, 100, 105
NOT_RUN: 80, 101

The new frame-factor test executed a structured physically connected 1,024-qubit circuit, 5,886 source gates, 522,272 coefficient bytes, 12 amplitude queries. Dense small-case cross-checks: 1,600 amplitudes and 1,000 observables. No unrestricted 1,024-qubit claim.

Pair contraction measured 1,704,448 bytes of tracked tensor/index payload on the random depth-4 prefix; depth-5 selected-order estimate 9,059,704,832 bytes, not executed. The depth-100 uncompute remains failed. The reference-frame backend is structure-dependent.

Connected numerical certificates were tested against a 100-digit oracle (192 amplitudes, 48 observables); all-mode certification remains partial. Full suite peak process RSS 472,944 KiB. Local container ceiling 4 GiB. GPU, MPI, power, named external simulator comparisons, independent replication, frontend production build remain unverified.

Run `node --max-old-space-size=3072 tests/diamond.test.mjs diamond-results.json` to regenerate evidence. Nonzero exit is expected when releaseEligible=false. The full raw v0.8 local result is included in the separately packaged v0.8 workspace, not uploaded here because the evidence-file transfer was unavailable; the previous v0.7 report and raw results are preserved under docs/history. Local full raw result Git blob SHA cb7feba5ed5dd3aff84504c08d7e54fc3e7c7aa9. This summary is not an independent certificate.
