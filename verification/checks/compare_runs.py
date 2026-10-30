"""Compare the user's result files with the Phase D copies, row by row.
Usage: python compare_runs.py <user_dir> <phase_d_dir>
Runs are deterministic (fixed map and run seeds); only wall-clock time limits can differ."""
import csv, os, sys
from collections import Counter

COUNTERS = ("constraint_checks", "assignment_attempts", "backtracks", "repair_iterations", "restarts")
KEY = ("algorithm", "n", "k", "map_seed", "run_seed")
for f in ("results.csv", "results_large.csv", "results_a3_norestart.csv", "results_ablation.csv"):
    user = {tuple(r[c] for c in KEY): r for r in csv.DictReader(open(os.path.join(sys.argv[1], f)))}
    old = {tuple(r[c] for c in KEY): r for r in csv.DictReader(open(os.path.join(sys.argv[2], f)))}
    same_runs = user.keys() == old.keys()
    both_answered = [k for k in user if user[k]["status"] != "TIMEOUT" and old[k]["status"] != "TIMEOUT"]
    identical = sum(all(user[k][c] == old[k][c] for c in ("status", "parity", "instance_status") + COUNTERS)
                    for k in both_answered)
    flips = [k for k in user if (user[k]["status"] == "TIMEOUT") != (old[k]["status"] == "TIMEOUT")]
    print(f"{f}: same {len(user)} runs: {same_runs} | answered both times: {len(both_answered)}, "
          f"identical in status and every counter: {identical}")
    print(f"   per-map verdicts identical: {all(user[k]['instance_status'] == old[k]['instance_status'] for k in user)}")
    if flips:
        print(f"   runs that hit the 30 s limit only once: {len(flips)} "
              f"({dict(Counter(k[0] for k in flips))})")
        for k in flips:
            a, b = (user[k], old[k]) if old[k]["status"] == "TIMEOUT" else (old[k], user[k])
            print(f"     {k[0]} n={k[1]} k={k[2]} map {k[3]}: {a['status']} in "
                  f"{float(a['runtime_seconds']):.1f} s one time, TIMEOUT the other")
    t = lambda d: sum(float(r["runtime_seconds"]) for r in d.values())
    print(f"   total runtime: Phase D {t(old) / 60:.1f} min, yours {t(user) / 60:.1f} min")
