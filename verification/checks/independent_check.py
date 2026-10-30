"""Independent check of maps and colourings: uses SciPy and its own code, not the project's
validate_map / verify_solution / check_3colour_parity. Usage: python independent_check.py <repo>"""
import functools, sys
from collections import Counter
from scipy.spatial import ConvexHull, Delaunay

print = functools.partial(print, flush=True)
sys.path.insert(0, sys.argv[1])
import multi_city_lighting as m

def own_roads(cities):
    edges = set()
    for a, b, c in Delaunay(cities).simplices:
        for u, v in ((a, b), (b, c), (a, c)):
            edges.add((min(u, v), max(u, v)))
    return edges

def own_odd_inner(cities, edges):
    hull = set(ConvexHull(cities).vertices)
    deg = Counter(x for e in edges for x in e)
    return sorted(int(v) for v in range(len(cities)) if v not in hull and deg[v] % 2)

def own_valid(colouring, edges, palette):
    return (colouring is not None and len(colouring) == len(set().union(*edges))
            and all(colouring[v] in palette for v in colouring)
            and all(colouring[a] != colouring[b] for a, b in edges))

def check_map(n, seed, methods):
    mp = m.make_map(n, seed)
    edges = own_roads(mp["cities"])
    roads = {(min(a, b), max(a, b)) for a, b in mp["roads"]}
    h = len(ConvexHull(mp["cities"]).vertices)
    ok_roads = roads == edges and len(edges) == 3 * n - 3 - h
    odd = own_odd_inner(mp["cities"], edges)
    results = {}
    for k in (3, 4):
        palette = m.COLOURS_BY_K[k]
        for name in methods:
            r = m.run_algorithm(name, mp["adjacency"], palette, map_seed=seed, run_seed=0, timeout_seconds=30)
            if r.status == m.SAT:
                good = own_valid(r.colouring, edges, palette) and not (k == 3 and odd)
            elif r.status == m.UNSAT:
                good = k == 3 and bool(odd) or k == 3          # UNSAT only possible for k = 3
                good = good and k == 3
            else:
                good = None                                    # FAILED / TIMEOUT prove nothing
            results[(k, name)] = (r.status, good)
    return ok_roads, odd, results

print("1. Demo map (n = 20, seed 42), all four methods")
ok_roads, odd, res = check_map(20, 42, ("A1", "A2", "A3", "M3"))
print(f"   roads identical to SciPy's Delaunay and = 3n-3-h: {ok_roads}")
print(f"   odd inner cities (own count): {odd}")
for (k, name), (status, good) in res.items():
    print(f"   k={k} {name}: {status:7} -> {'colouring checked: valid' if status == 'SAT' and good else 'UNSAT backed by odd cities' if status == 'UNSAT' and odd else 'proves nothing' if good is None else 'PROBLEM'}")

print("2. Every map used in the experiments: n = 5-50 (ablation), 75, 100, 150, 200; 10 maps each")
ns = list(range(5, 51)) + [75, 100, 150, 200]
maps = bad_roads = coloured = bad_colour = unsat = unsat_without_odd = sat3 = 0
for n in ns:
    for t in range(10):
        ok_roads, odd, res = check_map(n, 1000 * n + t, ("A2", "M3") if n <= 100 else ("M3",))
        maps += 1; bad_roads += not ok_roads
        for (k, name), (status, good) in res.items():
            if status == "SAT":
                coloured += 1; bad_colour += not good; sat3 += k == 3
            elif status == "UNSAT":
                unsat += 1; unsat_without_odd += not odd
print(f"   maps: {maps}, roads differ from SciPy or count wrong: {bad_roads}")
print(f"   colourings checked: {coloured} (of which k = 3: {sat3}), invalid: {bad_colour}")
print(f"   UNSAT answers: {unsat}, without an odd inner city to back them: {unsat_without_odd}")
