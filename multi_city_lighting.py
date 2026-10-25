"""
Multi-City Lighting — Graph Colouring as a CSP
See README.md for the overview and team tasks.

    BLOCK 0  Shared                       (everyone — agree first, then freeze)
    BLOCK 1  Map, A1, plots               (Person 1)
    BLOCK 2  A2 smart backtracking        (Person 2)
    BLOCK 3  A3 min-conflicts, experiments(Person 3)
    BLOCK 4  Main                         (Person 1)

Only edit your own block.
"""

# =============================================================================
# BLOCK 0 — SHARED (everyone)
# =============================================================================
import csv
import random
import time
from collections import Counter
from dataclasses import dataclass, asdict, field

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import Delaunay, QhullError

COLOURS_BY_K = {
    3: ["Red", "Green", "Blue"],
    4: ["Red", "Green", "Blue", "Yellow"],
}
COLOUR_HEX = {"Red": "#d62728", "Green": "#2ca02c",
              "Blue": "#1f77b4", "Yellow": "#f2c418"}

EPS = 1e-12
SHOW_PLOTS = False        # True = open windows, False = only save PNG files
DEFAULT_TIMEOUT = 30.0    # seconds (A1, A2)
DEFAULT_MAX_STEPS = 10_000  # Min-Conflicts

# Run status (one algorithm run)
SAT, UNSAT, TIMEOUT, FAILED = "SAT", "UNSAT", "TIMEOUT", "FAILED"
NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
# Instance status (one map + k)
SOLVABLE, UNRESOLVED, NEEDS_CHECK = "SOLVABLE", "UNRESOLVED", "NEEDS_CHECK"


class MapValidationError(Exception):
    pass


class SearchTimeout(Exception):
    pass


@dataclass
class Metrics:
    constraint_checks: int = 0     # all algorithms (counted in csp.check)
    assignment_attempts: int = 0   # A1, A2
    backtracks: int = 0            # A1, A2
    repair_iterations: int = 0     # A3
    restarts: int = 0              # A3


@dataclass
class RunResult:
    algorithm: str
    n: int
    k: int
    status: str
    colouring: dict = None
    runtime_seconds: float = 0.0
    map_seed: object = None
    run_seed: object = None
    metrics: Metrics = field(default_factory=Metrics)

    def to_row(self):
        """Flat dict for results.csv."""
        row = {"algorithm": self.algorithm, "n": self.n, "k": self.k,
               "map_seed": self.map_seed, "run_seed": self.run_seed,
               "status": self.status, "runtime_seconds": self.runtime_seconds}
        row.update(asdict(self.metrics))
        return row


class TimeGuard:
    """Call guard.check() inside loops / recursion to respect the time limit."""

    def __init__(self, timeout_seconds=None):
        self.deadline = None if timeout_seconds is None else time.perf_counter() + timeout_seconds

    def check(self):
        if self.deadline is not None and time.perf_counter() > self.deadline:
            raise SearchTimeout()


class MapColouringCSP:
    """Variables = cities 0..n-1, domain = colours, constraint = neighbours differ."""

    def __init__(self, adjacency, colours):
        self.n = len(adjacency)
        self.variables = list(range(self.n))
        self.colours = list(colours)
        self.domains = {v: list(colours) for v in self.variables}
        self.neighbours = adjacency            # list of sets
        self.metrics = Metrics()

    def check(self, colour_a, colour_b):
        """The ONLY place a constraint check is counted. True = allowed."""
        self.metrics.constraint_checks += 1
        return colour_a != colour_b

    def is_consistent(self, var, value, assignment):
        """True if no assigned neighbour of var already has `value`."""
        return all(self.check(value, assignment[nb])
                   for nb in self.neighbours[var] if nb in assignment)

    def count_conflicts(self, var, value, assignment):
        """How many assigned neighbours of var have `value`."""
        return sum(1 for nb in self.neighbours[var]
                   if nb in assignment and not self.check(value, assignment[nb]))


def verify_solution(adjacency, colouring, colours):
    """True only if every city has an allowed colour and no road has equal colours."""
    if colouring is None or len(colouring) != len(adjacency):
        return False
    if any(colouring.get(c) not in colours for c in range(len(adjacency))):
        return False
    return all(colouring[a] != colouring[b]
               for a, nbs in enumerate(adjacency) for b in nbs)


def run_algorithm(name, adjacency, colours, map_seed=None, run_seed=None,
                  timeout_seconds=DEFAULT_TIMEOUT, **params):
    """Run any algorithm from ALGORITHMS and return a RunResult.

    Algorithm shape:  func(csp, guard, rng, **params) -> {city: colour} or None
      None from a complete algorithm (A1, A2) -> UNSAT
      None from local search (A3)             -> FAILED
    """
    func, is_complete = ALGORITHMS[name]
    csp = MapColouringCSP(adjacency, colours)
    start = time.perf_counter()
    try:
        colouring = func(csp, TimeGuard(timeout_seconds), random.Random(run_seed), **params)
        if colouring is None:
            status = UNSAT if is_complete else FAILED
        elif verify_solution(adjacency, colouring, colours):
            status = SAT
        else:
            raise AssertionError(f"{name} returned an invalid colouring (bug)")
    except SearchTimeout:
        colouring, status = None, TIMEOUT
    except NotImplementedError:
        colouring, status = None, NOT_IMPLEMENTED
    return RunResult(name, len(adjacency), len(colours), status,
                     colouring if status == SAT else None,
                     time.perf_counter() - start, map_seed, run_seed, csp.metrics)


# =============================================================================
# BLOCK 1 — PERSON 1: MAP, A1, PLOTS
# Aim: correct maps, all pictures, and the simplest algorithm.
# =============================================================================

# ---- Map generation (DONE) --------------------------------------------------
def generate_cities(n, seed=None):
    """n random cities in [0, 1] x [0, 1], shape (n, 2)."""
    if n < 1:
        raise ValueError("n must be at least 1")
    return np.random.default_rng(seed).random((n, 2))


def _is_collinear(cities):
    if len(cities) < 3:
        return True
    return np.linalg.matrix_rank(cities - cities.mean(axis=0), tol=1e-10) < 2


def _roads_along_line(cities):
    centred = cities - cities.mean(axis=0)
    order = np.argsort(centred @ np.linalg.svd(centred)[2][0])
    return {tuple(sorted((int(a), int(b)))) for a, b in zip(order[:-1], order[1:])}


def generate_roads(cities):
    """Delaunay roads. Returns (roads, triangulation); triangulation is None
    for n < 3 or collinear cities. roads = set of (i, j) with i < j."""
    n = len(cities)
    if n == 1:
        return set(), None
    if n == 2:
        return {(0, 1)}, None
    if _is_collinear(cities):
        return _roads_along_line(cities), None
    try:
        tri = Delaunay(cities)
    except QhullError:
        return _roads_along_line(cities), None
    roads = set()
    for a, b, c in tri.simplices:
        for e in ((a, b), (b, c), (a, c)):
            roads.add(tuple(sorted(map(int, e))))
    return roads, tri


def build_adjacency(n, roads):
    """adjacency[i] = set of neighbours of city i."""
    adjacency = [set() for _ in range(n)]
    for a, b in roads:
        adjacency[a].add(b)
        adjacency[b].add(a)
    return adjacency


def make_map(n, seed=None):
    """Generate + validate one map. Returns dict: n, seed, cities, roads,
    triangulation, adjacency."""
    cities = generate_cities(n, seed)
    roads, tri = generate_roads(cities)
    adjacency = build_adjacency(n, roads)
    validate_map(cities, roads, adjacency, tri)
    return {"n": n, "seed": seed, "cities": cities, "roads": roads,
            "triangulation": tri, "adjacency": adjacency}


# ---- Map validation (DONE) --------------------------------------------------
def _orientation(p, q, r):
    v = (q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - \
        (q[..., 1] - p[..., 1]) * (r[..., 0] - p[..., 0])
    return np.where(np.abs(v) <= EPS, 0, np.sign(v))


def boundary_edges(tri):
    """Edges on the outer boundary (belong to exactly one triangle)."""
    count = Counter()
    for a, b, c in tri.simplices:
        for e in ((a, b), (b, c), (a, c)):
            count[tuple(sorted(map(int, e)))] += 1
    return {e for e, k in count.items() if k == 1}


def find_crossing_roads(cities, roads):
    """Pairs of roads that cross (should be empty)."""
    rl = list(roads)
    if len(rl) < 2:
        return []
    idx = np.array(rl)
    i, j = np.triu_indices(len(rl), k=1)
    a1, b1, a2, b2 = idx[i, 0], idx[i, 1], idx[j, 0], idx[j, 1]
    keep = (a1 != a2) & (a1 != b2) & (b1 != a2) & (b1 != b2)
    i, j, a1, b1, a2, b2 = i[keep], j[keep], a1[keep], b1[keep], a2[keep], b2[keep]
    p1, q1, p2, q2 = cities[a1], cities[b1], cities[a2], cities[b2]
    o1, o2 = _orientation(p1, q1, p2), _orientation(p1, q1, q2)
    o3, o4 = _orientation(p2, q2, p1), _orientation(p2, q2, q1)
    lo = lambda a, b, d: np.minimum(a[:, d], b[:, d])
    hi = lambda a, b, d: np.maximum(a[:, d], b[:, d])
    box = np.ones(len(i), bool)
    for d in (0, 1):
        box &= np.maximum(lo(p1, q1, d), lo(p2, q2, d)) <= np.minimum(hi(p1, q1, d), hi(p2, q2, d)) + EPS
    bad = ((o1 * o2 < 0) & (o3 * o4 < 0)) | ((o1 == 0) & (o2 == 0) & box)
    return [(rl[x], rl[y]) for x, y in zip(i[bad], j[bad])]


def validate_map(cities, roads, adjacency, tri=None):
    """Raise MapValidationError if the map is not a valid maximal road network."""
    n = len(cities)

    def need(ok, msg):
        if not ok:
            raise MapValidationError(msg)

    need(len(adjacency) == n, "one adjacency entry per city")
    for a, b in roads:
        need(0 <= a < n and 0 <= b < n and a != b, f"bad road {(a, b)}")
        need(b in adjacency[a] and a in adjacency[b], f"adjacency missing {(a, b)}")
    need(sum(map(len, adjacency)) == 2 * len(roads), "adjacency has extra neighbours")
    crossings = find_crossing_roads(cities, roads)
    need(not crossings, f"crossing roads, e.g. {crossings[:3]}")

    if tri is None:
        need(len(roads) == n - 1, "small/collinear map should be a path")
        return
    need(len(tri.coplanar) == 0, "some cities were left out of the triangulation")
    h = len(boundary_edges(tri))
    need(len(roads) == 3 * n - 3 - h, f"expected {3 * n - 3 - h} roads, got {len(roads)}")


# ---- Parity check for k = 3 (TODO) ------------------------------------------
def check_3colour_parity(adjacency, tri):
    """Return UNSAT if some INNER city has odd degree, else NEEDS_CHECK.

    TODO:
      - tri is None -> NEEDS_CHECK
      - outer cities = cities in boundary_edges(tri); do not check them
      - inner city with odd len(adjacency[c]) -> UNSAT
    """
    raise NotImplementedError


# ---- A1: Naive Backtracking (TODO) ------------------------------------------
def backtracking_search(csp, guard, rng):
    """A1. Cities in order 0, 1, 2, ...; colours in fixed order; no heuristics.

    TODO:
      - recursive backtrack(assignment), call guard.check() each call
      - csp.is_consistent(...) to test a colour
      - count csp.metrics.assignment_attempts and csp.metrics.backtracks
      - return {city: colour} or None
    """
    raise NotImplementedError


# ---- Plots ------------------------------------------------------------------
def plot_map(cities, roads, colouring=None, title="City Map",
             save_path=None, show=SHOW_PLOTS):
    """Blank map (colouring=None) or coloured map (DONE)."""
    fig, ax = plt.subplots(figsize=(8, 7))
    for a, b in roads:
        ax.plot(*zip(cities[a], cities[b]), color="gray", linewidth=1, zorder=1)
    colours = ["black"] * len(cities) if colouring is None else \
        [COLOUR_HEX.get(colouring.get(i), "black") for i in range(len(cities))]
    ax.scatter(cities[:, 0], cities[:, 1], c=colours, s=55,
               edgecolors="black", linewidths=0.6, zorder=2)
    for i, (x, y) in enumerate(cities):
        ax.annotate(str(i), (x, y), xytext=(4, 4), textcoords="offset points", fontsize=8)
    ax.set(title=title, xlim=(-0.05, 1.05), ylim=(-0.05, 1.05), xlabel="X", ylabel="Y")
    ax.set_aspect("equal")
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    if show:
        plt.show()
    plt.close(fig)


def plot_comparison(rows, metric="runtime_seconds", save_path=None, show=SHOW_PLOTS):
    """Plot `metric` vs n, one line per algorithm, one subplot per k (TODO).

    TODO:
      - rows = list of dicts from RunResult.to_row()
      - mean (+ std) per n, log scale on y
      - decide with Person 3 how TIMEOUT runs are shown
    """
    raise NotImplementedError


# =============================================================================
# BLOCK 2 — PERSON 2: A2 (MRV + DEGREE + LCV + FORWARD CHECKING)
# Aim: the fastest complete algorithm. Compare colours only via csp.check().
# =============================================================================
def select_unassigned_variable(csp, assignment, domains, use_mrv=True):
    """MRV: city with fewest colours left; tie -> most unassigned neighbours
    (Degree); tie -> lowest index. use_mrv=False -> lowest index. (TODO)"""
    raise NotImplementedError


def order_domain_values(csp, var, assignment, domains, use_lcv=True):
    """LCV: colours that remove the fewest options from neighbours first.
    use_lcv=False -> domains[var] as is. (TODO)"""
    raise NotImplementedError


def forward_check(csp, var, value, assignment, domains):
    """Remove `value` from unassigned neighbours' domains (on a copy).
    Return (new_domains, ok); ok=False if a domain becomes empty. (TODO)"""
    raise NotImplementedError


def backtracking_generic(csp, guard, rng, use_mrv=True, use_lcv=True, use_fc=True):
    """Backtracking with switchable MRV / LCV / FC. Same skeleton and counters
    as A1. Return {city: colour} or None. (TODO)"""
    raise NotImplementedError


def backtracking_fc(csp, guard, rng):
    """A2 = all techniques on."""
    return backtracking_generic(csp, guard, rng, use_mrv=True, use_lcv=True, use_fc=True)


# Optional ablation variants (work automatically once backtracking_generic works)
def bt_mrv(csp, guard, rng):
    return backtracking_generic(csp, guard, rng, use_mrv=True, use_lcv=False, use_fc=False)


def bt_fc(csp, guard, rng):
    return backtracking_generic(csp, guard, rng, use_mrv=False, use_lcv=False, use_fc=True)


# =============================================================================
# BLOCK 3 — PERSON 3: A3 (MIN-CONFLICTS) + EXPERIMENTS
# Aim: local search, and the comparison data for requirement (d).
# =============================================================================
def min_conflicts(csp, guard, rng, max_steps=DEFAULT_MAX_STEPS, max_restarts=0):
    """A3. Random full colouring, then repeatedly recolour a random conflicting
    city with its least-conflict colour. (TODO)

    TODO:
      - use rng for all randomness, guard.check() every step
      - csp.count_conflicts(...) to measure conflicts
      - count csp.metrics.repair_iterations and csp.metrics.restarts
      - return {city: colour}, or None when the step budget is used up
    """
    raise NotImplementedError


def determine_instance_status(k, parity_label, runs):
    """Final status of one (map, k): SOLVABLE / UNSAT / UNRESOLVED. (TODO)

    Rules: k=4 -> SOLVABLE; parity UNSAT -> UNSAT; a complete run SAT/UNSAT ->
    that; only A3 SAT -> SOLVABLE (note it); otherwise UNRESOLVED.
    TIMEOUT and FAILED prove nothing.
    """
    raise NotImplementedError


def run_experiment(n_values, k_values=(3, 4), trials=10,
                   algorithms=("A1", "A2", "A3"), timeout_seconds=DEFAULT_TIMEOUT,
                   max_steps=DEFAULT_MAX_STEPS, a3_runs=5, csv_path="results.csv"):
    """Run all algorithms on the SAME maps and save results.csv. (TODO)

    TODO:
      - for each n and trial: make_map(n, seed) once, fixed seed per (n, trial)
      - for each k and algorithm: run_algorithm(...) (A3 several times)
      - add parity + instance status to each row, save_results_csv(rows, csv_path)
    """
    raise NotImplementedError


def save_results_csv(rows, csv_path="results.csv"):
    """Write list of dicts to CSV (DONE)."""
    if rows:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def summarise_results(rows):
    """Table per (n, k): #SOLVABLE/#UNSAT/#UNRESOLVED, % finished for A1/A2,
    A3 success rate (on SOLVABLE maps only), mean/std runtime and checks. (TODO)"""
    raise NotImplementedError


# =============================================================================
# ALGORITHM REGISTRY (everyone — add lines, never rename)
# name -> (function, is_complete)
# =============================================================================
ALGORITHMS = {
    "A1": (backtracking_search, True),
    "A2": (backtracking_fc, True),
    "A3": (min_conflicts, False),
    "BT+MRV": (bt_mrv, True),
    "BT+FC": (bt_fc, True),
}


# =============================================================================
# BLOCK 4 — MAIN (Person 1)
# =============================================================================
def demo_single_map(n, seed=42):
    """Requirements (a), (b), (c), (e) for one n."""
    m = make_map(n, seed)
    print(f"Cities: {n} | Roads: {len(m['roads'])}")
    plot_map(m["cities"], m["roads"], title=f"Blank map (n={n})",
             save_path=f"map_n{n}.png")

    for k in (3, 4):
        print(f"\nk = {k}")
        for name in ("A1", "A2", "A3"):
            res = run_algorithm(name, m["adjacency"], COLOURS_BY_K[k],
                                map_seed=seed, run_seed=0)
            print(f"  {name}: {res.status:16s} {res.runtime_seconds:.4f}s "
                  f"checks={res.metrics.constraint_checks}")
            if res.status != NOT_IMPLEMENTED:
                plot_map(m["cities"], m["roads"], res.colouring,
                         title=f"n={n}, k={k}, {name}: {res.status}",
                         save_path=f"map_n{n}_k{k}_{name}.png")


def main():
    n = int(input("Enter the number of cities n: "))
    demo_single_map(n)

    # Requirement (d), once Block 3 is done:
    # rows = run_experiment([5, 10, 20, 30, 50, 75, 100])
    # summarise_results(rows)
    # plot_comparison(rows, "runtime_seconds", "compare_time.png")
    # plot_comparison(rows, "constraint_checks", "compare_checks.png")


if __name__ == "__main__":
    main()
