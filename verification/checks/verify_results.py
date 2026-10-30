"""Check the Phase D result files. Usage: python verify_results.py <repo>"""
import csv, os, sys
from collections import Counter, defaultdict

repo = sys.argv[1]
COMPLETE = {"A1", "A2", "M3", "BT+MRV", "BT+FC"}
files = {  # name: (n values, k values, algorithms, A3 runs per map)
    "results.csv": ([5, 10, 20, 30, 50, 75, 100], [3, 4], ["A1", "A2", "A3", "M3"], 5),
    "results_large.csv": ([150, 200], [3, 4], ["A3", "M3"], 5),
    "results_a3_norestart.csv": ([50, 75, 100, 150, 200], [4], ["A3"], 5),
    "results_ablation.csv": (list(range(5, 51)), [3, 4], ["A1", "A2", "BT+MRV", "BT+FC"], 5),
}
ok_all = True
def check(name, cond, detail=""):
    global ok_all; ok_all &= bool(cond)
    print(f"   [{'PASS' if cond else 'FAIL'}] {name}" + (f" -> {detail}" if not cond and detail else ""))

data = {}
for fname, (ns, ks, algs, a3_runs) in files.items():
    path = os.path.join(repo, fname)
    print(f"\n{fname}")
    if not os.path.exists(path):
        check("file exists", False); continue
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    data[fname] = rows
    per_map = sum(a3_runs if a == "A3" else 1 for a in algs)
    want = len(ns) * 10 * len(ks) * per_map
    check(f"{len(rows)} rows = {len(ns)} n x 10 maps x {len(ks)} k x {per_map} runs", len(rows) == want, want)
    check("n, k and algorithms exactly as asked",
          sorted({int(r['n']) for r in rows}) == ns and sorted({int(r['k']) for r in rows}) == ks
          and sorted({r['algorithm'] for r in rows}) == sorted(algs))
    check("map seeds are 1000 * n + trial (same maps for every method)",
          all(int(r["map_seed"]) - 1000 * int(r["n"]) in range(10) for r in rows))
    check("no NOT_IMPLEMENTED", not any(r["status"] == "NOT_IMPLEMENTED" for r in rows))
    by_map = defaultdict(list)
    for r in rows:
        by_map[(r["n"], r["map_seed"], r["k"])].append(r)
    disagree = [m for m, rs in by_map.items()
                if len({r["status"] for r in rs if r["algorithm"] in COMPLETE and r["status"] in ("SAT", "UNSAT")}) > 1]
    check("complete methods never disagree on a map (SAT vs UNSAT)", not disagree, disagree[:3])
    one_status = all(len({r["instance_status"] for r in rs}) == 1 for rs in by_map.values())
    check("one instance status per (map, k)", one_status)
    bad = [m for m, rs in by_map.items()
           if (rs[0]["instance_status"] == "SOLVABLE") != (any(r["status"] == "SAT" for r in rs) or m[2] == "4")]
    check("SOLVABLE exactly when some method found a colouring, or k = 4 (Four Colour Theorem)", not bad, bad[:3])
    if COMPLETE & set(algs):
        bad = [m for m, rs in by_map.items() if m[2] == "4"
               and not any(r["status"] == "SAT" and r["algorithm"] in COMPLETE for r in rs)]
        check("every k = 4 map really got a verified colouring from a complete method", not bad, bad[:3])
    bad = [m for m, rs in by_map.items() if m[2] == "3" and rs[0]["parity"] == "UNSAT"
           and any(r["status"] == "SAT" for r in rs)]
    check("no colouring on a map the parity proof rules out", not bad, bad[:3])
    print("   statuses per algorithm:", {a: dict(Counter(r["status"] for r in rows if r["algorithm"] == a))
                                         for a in algs})
    print("   instances:", dict(Counter(rs[0]["instance_status"] for rs in by_map.values())))

print("\nRestarts (k = 4, A3 success rate on SOLVABLE maps)")
def success(rows, n):
    rs = [r for r in rows if r["algorithm"] == "A3" and r["k"] == "4" and int(r["n"]) == n
          and r["instance_status"] == "SOLVABLE"]
    return f"{100 * sum(r['status'] == 'SAT' for r in rs) / len(rs):.0f}% of {len(rs)}" if rs else "-"
with_r = data.get("results.csv", []) + data.get("results_large.csv", [])
for n in (50, 75, 100, 150, 200):
    print(f"   n={n:3d}: with restarts {success(with_r, n):>10} | without {success(data.get('results_a3_norestart.csv', []), n):>10}")

print("\nAblation: runs that timed out (out of 20 per n), n >= 30")
abl = data.get("results_ablation.csv", [])
for a in ("A1", "A2", "BT+MRV", "BT+FC"):
    t = {n: sum(r["status"] == "TIMEOUT" for r in abl if r["algorithm"] == a and int(r["n"]) == n) for n in range(30, 51)}
    print(f"   {a:7}: total {sum(t.values()):3d}, first n with a timeout: {min([n for n, v in t.items() if v] or [None], key=lambda x: x or 99)}")
print("\nALL CHECKS PASSED" if ok_all else "\nSOME CHECKS FAILED")
