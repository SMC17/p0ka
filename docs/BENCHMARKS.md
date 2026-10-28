# Local microbenchmarks

- Captured: 2026-10-28T04:49:05.019807+00:00
- Python: 3.13.5
- OS: Linux-6.18.55-x86_64-with-glibc2.41
- These are **local illustrative measurements**, not the official Sequoia interpreter, hardware or end-to-end Agent interface.
- A warmed function-call benchmark omits Agent input parsing, bot startup, CPU contention, I/O and sandbox enforcement; values should **not** be used as proof of the 1 ms limit.
- The test cases are not representative of the unknown tournament variant.

| Workload | Samples | P50 (us) | P99 (us) | Max (us) | >1 ms |
|---|---:|---:|---:|---:|---:|
| Policy call (known equity) | 1000 | 0.52 | 0.68 | 39.97 | 0 |
| Eight-player exact ICM | 200 | 244.59 | 366.01 | 463.18 | 0 |
| Seven-card reference evaluation | 200 | 27.88 | 42.84 | 50.22 | 0 |
| Uniform equity, 100 samples | 30 | 7074.07 | 8935.54 | 8935.54 | 30 |

## Interpretation

- ICM and the reference evaluator are suitable correctness baselines, not proven deployment hot paths.
- Monte Carlo equity scales with samples and opponents; limit samples or replace with precomputed approximations under the actual deadline.
- Cold-start and full-adapter latency must be measured as soon as the official kit is available.
