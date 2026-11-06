# Final results

These CSV files are our own experiment runs. The first four give every number in the
report and in `projectoverview.md`. They were made with `multi_city_lighting.py`
at commit `73d83a0`, on Windows with Python 3.12, using a 30-second time limit per run.
We made the fifth one, `results_m3plus.csv`, later on to compare M3 with M3+.

| File | What it covers | Rows |
|---|---|---:|
| `results.csv` | Main comparison: n = 5, 10, 20, 30, 50, 75, 100; k = 3 and 4; A1, A2, A3, M3 | 1,120 |
| `results_large.csv` | Larger maps: n = 150, 200; k = 3 and 4; A3 and M3 | 240 |
| `results_a3_norestart.csv` | A3 without restarts: n = 50 to 200; k = 4 | 250 |
| `results_ablation.csv` | M1 ablation: every n from 5 to 50; k = 3 and 4; A1, A2, BT+MRV, BT+FC | 3,680 |
| `results_m3plus.csv` | M3 against M3+ (added after the presentation): n = 5 to 200; k = 3 and 4. Run on a different machine, so don't compare its times with the other files | 360 |

Each row is one run of one method on one map.

| Column | Meaning |
|---|---|
| `algorithm` | `A1` baseline, `A2` = M1, `A3` = M2, `M3`, `M3+`, or the ablation variants `BT+MRV` and `BT+FC` |
| `n` | number of cities |
| `k` | number of colours (3 or 4) |
| `map_seed` | seed of the map, `1000 * n + trial` with trial 0 to 9 |
| `run_seed` | seed of the run's random number generator (0 for complete methods, 0 to 4 for A3) |
| `status` | `SAT` colouring found and verified; `UNSAT` proved impossible; `TIMEOUT` hit the time limit; `FAILED` A3 used up its repairs. TIMEOUT and FAILED prove nothing about the map |
| `runtime_seconds` | time of the solver call, excluding map generation and the final check |
| `constraint_checks` | number of colour comparisons through `csp.check()` |
| `assignment_attempts` | colours tried by backtracking (for M3 and M3+ with k = 4, above 0 means the fallback ran) |
| `backtracks` | times backtracking undid a colour |
| `repair_iterations` | repairs made by A3 |
| `restarts` | attempts A3 made after its first one |
| `parity` | for k = 3: `UNSAT` if an inner city has an odd number of neighbours, otherwise `NEEDS_CHECK`; `N/A` for k = 4 |
| `instance_status` | what is known about this map and k from all runs: `SOLVABLE`, `UNSAT` or `UNRESOLVED` |

To look at the results, rerun the experiments yourself, or compare your rerun with these
files, see `projectoverview.md`, Section 9. A rerun writes to `my_results/`, so it never
overwrites these files. Runtimes depend on the machine; the counters do not, apart
from the few runs that finish on one machine and hit the time limit on another.
