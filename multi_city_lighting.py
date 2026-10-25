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
#
#   1.1 Map generation      generate_cities, generate_roads, build_adjacency, make_map
#   1.2 Map validation      validate_map (+ helpers)
#   1.3 Parity check        check_3colour_parity          (k = 3 analysis)
#   1.4 Algorithm A1        backtracking_search           (naive backtracking)
#   1.5 Plots               plot_map, plot_comparison
# =============================================================================

# ---- 1.1 Map generation ------------------------------------------------------
def _road(a, b):
    """A road in canonical form: (smaller index, larger index)."""
    return (int(a), int(b)) if a < b else (int(b), int(a))


def _triangle_edges(tri):
    """Yield the three edges of every triangle (shared edges appear twice)."""
    for a, b, c in tri.simplices:
        yield _road(a, b)
        yield _road(b, c)
        yield _road(a, c)


def _is_collinear(cities):
    """True if all cities lie on one straight line (Delaunay is impossible)."""
    if len(cities) < 3:
        return True
    return np.linalg.matrix_rank(cities - cities.mean(axis=0), tol=1e-10) < 2


def _roads_along_line(cities):
    """Roads for collinear cities: connect neighbours along the line.
    Any other road would pass through a city, so this is already maximal."""
    centred = cities - cities.mean(axis=0)
    direction = np.linalg.svd(centred)[2][0]
    order = np.argsort(centred @ direction)
    return {_road(a, b) for a, b in zip(order[:-1], order[1:])}


def generate_cities(n, seed=None):
    """Place n random cities in [0, 1] x [0, 1]. Returns an array of shape (n, 2)."""
    if n < 1:
        raise ValueError("n must be at least 1")
    return np.random.default_rng(seed).random((n, 2))


def generate_roads(cities):
    """Connect the cities with the maximum number of non-crossing straight roads.

    Uses Delaunay triangulation. Returns (roads, triangulation):
      roads         : set of (i, j) with i < j
      triangulation : scipy Delaunay object, or None for n < 3 / collinear cities
    """
    n = len(cities)
    if n == 1:
        return set(), None
    if n == 2:
        return {(0, 1)}, None
    if _is_collinear(cities):
        return _roads_along_line(cities), None
    try:
        tri = Delaunay(cities)
    except QhullError:                      # numerically almost collinear
        return _roads_along_line(cities), None
    return set(_triangle_edges(tri)), tri


def build_adjacency(n, roads):
    """adjacency[i] = set of cities directly connected to city i."""
    adjacency = [set() for _ in range(n)]
    for a, b in roads:
        adjacency[a].add(b)
        adjacency[b].add(a)
    return adjacency


def make_map(n, seed=None):
    """Generate and validate one complete map.

    Returns a dict with keys: n, seed, cities, roads, triangulation, adjacency.
    """
    cities = generate_cities(n, seed)
    roads, tri = generate_roads(cities)
    adjacency = build_adjacency(n, roads)
    validate_map(cities, roads, adjacency, tri)
    return {"n": n, "seed": seed, "cities": cities, "roads": roads,
            "triangulation": tri, "adjacency": adjacency}


# ---- 1.2 Map validation ------------------------------------------------------
def _orientation(p, q, r):
    """Which side of line p->q the point r is on: +1 left, -1 right, 0 on the line.
    Works on single points and on arrays of points."""
    cross = (q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - \
            (q[..., 1] - p[..., 1]) * (r[..., 0] - p[..., 0])
    return np.where(np.abs(cross) <= EPS, 0, np.sign(cross))


def _boxes_overlap(p1, q1, p2, q2):
    """True where the bounding boxes of segments p1-q1 and p2-q2 overlap."""
    overlap = np.ones(len(p1), dtype=bool)
    for d in (0, 1):
        low = np.maximum(np.minimum(p1[:, d], q1[:, d]), np.minimum(p2[:, d], q2[:, d]))
        high = np.minimum(np.maximum(p1[:, d], q1[:, d]), np.maximum(p2[:, d], q2[:, d]))
        overlap &= low <= high + EPS
    return overlap


def boundary_edges(tri):
    """Roads on the outer boundary of the map (they belong to only one triangle)."""
    count = Counter(_triangle_edges(tri))
    return {edge for edge, times in count.items() if times == 1}


def find_crossing_roads(cities, roads):
    """Return every pair of roads that cross each other (should be empty).
    Roads that only share an end city are fine."""
    road_list = list(roads)
    if len(road_list) < 2:
        return []

    ends = np.array(road_list)
    i, j = np.triu_indices(len(road_list), k=1)          # every pair once
    a1, b1, a2, b2 = ends[i, 0], ends[i, 1], ends[j, 0], ends[j, 1]
    separate = (a1 != a2) & (a1 != b2) & (b1 != a2) & (b1 != b2)
    i, j = i[separate], j[separate]
    p1, q1 = cities[a1[separate]], cities[b1[separate]]
    p2, q2 = cities[a2[separate]], cities[b2[separate]]

    o1, o2 = _orientation(p1, q1, p2), _orientation(p1, q1, q2)
    o3, o4 = _orientation(p2, q2, p1), _orientation(p2, q2, q1)
    proper_cross = (o1 * o2 < 0) & (o3 * o4 < 0)
    collinear_overlap = (o1 == 0) & (o2 == 0) & _boxes_overlap(p1, q1, p2, q2)

    bad = proper_cross | collinear_overlap
    return [(road_list[x], road_list[y]) for x, y in zip(i[bad], j[bad])]


def validate_map(cities, roads, adjacency, tri=None):
    """Check that the map is a valid, maximal, non-crossing road network.
    Raises MapValidationError with a clear message on the first problem."""
    n = len(cities)

    def need(ok, message):
        if not ok:
            raise MapValidationError(message)

    # graph is consistent
    need(len(adjacency) == n, "adjacency must have one entry per city")
    for a, b in roads:
        need(0 <= a < n and 0 <= b < n and a != b, f"invalid road {(a, b)}")
        need(b in adjacency[a] and a in adjacency[b], f"adjacency is missing road {(a, b)}")
    need(sum(map(len, adjacency)) == 2 * len(roads),
         "adjacency contains neighbours that have no road")

    # roads do not cross
    crossings = find_crossing_roads(cities, roads)
    need(not crossings, f"crossing roads found, e.g. {crossings[:3]}")

    # roads are maximal
    if tri is None:                          # n < 3 or collinear: a simple path
        need(len(roads) == n - 1, f"expected {n - 1} roads, got {len(roads)}")
        return
    need(len(tri.coplanar) == 0, "some cities were left out of the triangulation")
    h = len(boundary_edges(tri))             # = cities on the outer boundary
    expected = 3 * n - 3 - h
    need(len(roads) == expected, f"expected {expected} roads (3n - 3 - h), got {len(roads)}")


# ---- 1.3 Parity check for k = 3 ---------------------------------------------
def check_3colour_parity(adjacency, tri):
    """Quick proof that a map cannot be coloured with 3 colours.

    In a triangulation the neighbours of an inner city form a closed ring.
    An odd ring already needs 3 colours, so together with the centre city it
    needs 4. Outer (boundary) cities have no closed ring and are skipped.

    Returns UNSAT if some inner city has an odd number of neighbours,
    otherwise NEEDS_CHECK ("not proven UNSAT" - NOT proof that a solution exists).
    """
    if tri is None:                          # n < 3 or collinear: a path, 2 colours suffice
        return NEEDS_CHECK

    outer = {city for edge in boundary_edges(tri) for city in edge}
    for city, neighbours in enumerate(adjacency):
        if city not in outer and len(neighbours) % 2 == 1:
            return UNSAT
    return NEEDS_CHECK


# ---- 1.4 Algorithm A1: Naive Backtracking -----------------------------------
def backtracking_search(csp, guard, rng):
    """A1. Naive backtracking.

    Cities in order 0, 1, 2, ...; colours in the fixed order of csp.colours.
    No heuristics, no inference, no randomness (rng is unused).
    Returns {city: colour}, or None after every option was tried (-> UNSAT).
    """
    assignment = {}

    def backtrack():
        guard.check()
        if len(assignment) == csp.n:
            return dict(assignment)

        var = next(v for v in csp.variables if v not in assignment)
        for value in csp.colours:
            csp.metrics.assignment_attempts += 1
            if csp.is_consistent(var, value, assignment):
                assignment[var] = value
                result = backtrack()
                if result is not None:
                    return result
                del assignment[var]
                csp.metrics.backtracks += 1
        return None

    return backtrack()


# ---- 1.5 Plots ----------------------------------------------------------------
METRIC_LABELS = {"runtime_seconds": "Runtime (s)",
                 "constraint_checks": "Constraint checks"}


def _finish_figure(fig, save_path, show):
    """Save and/or show a figure, then free its memory."""
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    if show:
        plt.show()
    plt.close(fig)


def plot_map(cities, roads, colouring=None, title="City Map",
             save_path=None, show=SHOW_PLOTS):
    """Draw the map. colouring=None gives a blank map (black cities);
    otherwise colouring = {city: colour name}. Only pass SAT colourings."""
    fig, ax = plt.subplots(figsize=(8, 7))

    for a, b in roads:
        ax.plot(*zip(cities[a], cities[b]), color="gray", linewidth=1, zorder=1)

    if colouring is None:
        point_colours = ["black"] * len(cities)
    else:
        point_colours = [COLOUR_HEX.get(colouring.get(i), "black")
                         for i in range(len(cities))]
    ax.scatter(cities[:, 0], cities[:, 1], c=point_colours, s=55,
               edgecolors="black", linewidths=0.6, zorder=2)

    for i, (x, y) in enumerate(cities):
        ax.annotate(str(i), (x, y), xytext=(4, 4), textcoords="offset points", fontsize=8)

    ax.set(title=title, xlim=(-0.05, 1.05), ylim=(-0.05, 1.05), xlabel="X", ylabel="Y")
    ax.set_aspect("equal")
    _finish_figure(fig, save_path, show)


def _points_for_algorithm(runs, metric):
    """Mean, error bars and hollow flags per n for one algorithm and one k.
    Returns (points, timeouts) where points = list of (n, mean, low, high, hollow)."""
    points, timeouts = [], 0
    for n in sorted({int(r["n"]) for r in runs}):
        at_n = [r for r in runs if int(r["n"]) == n]
        finished = [float(r[metric]) for r in at_n if r["status"] != TIMEOUT]
        timeouts += len(at_n) - len(finished)
        if not finished or np.mean(finished) <= 0:     # nothing to show on a log axis
            continue
        mean, std = np.mean(finished), np.std(finished)
        low = min(std, mean - min(finished))           # keep error bar above 0 on log axis
        points.append((n, mean, low, std, len(finished) < len(at_n)))
    return points, timeouts


def plot_comparison(rows, metric="runtime_seconds", save_path=None, show=SHOW_PLOTS):
    """Plot `metric` against n: one subplot per k, one line per algorithm.

    rows   : list of dicts from RunResult.to_row() (or read back from results.csv)
    metric : "runtime_seconds" or "constraint_checks"

    TIMEOUT rule (Person 3 uses the same rule in summarise_results):
      - TIMEOUT and NOT_IMPLEMENTED runs are left out of the mean and std.
      - If some runs at an n timed out, the point is HOLLOW: the mean only
        covers the runs that finished, so the real cost is higher.
      - If every run at an n timed out, no point is drawn for that n.
      - The legend shows how many runs of each algorithm timed out.
    Error bars show the std; the lower end is clipped at the smallest
    observed value so it stays visible on the log axis.
    """
    rows = [r for r in rows if r["status"] != NOT_IMPLEMENTED]
    if not rows:
        print("plot_comparison: no finished runs to plot, skipped.")
        return

    label = METRIC_LABELS.get(metric, metric)
    algorithms = sorted({r["algorithm"] for r in rows})
    k_values = sorted({int(r["k"]) for r in rows})
    all_n = sorted({int(r["n"]) for r in rows})

    fig, axes = plt.subplots(1, len(k_values), figsize=(6 * len(k_values), 5),
                             squeeze=False)
    for ax, k in zip(axes[0], k_values):
        for alg in algorithms:
            runs = [r for r in rows if r["algorithm"] == alg and int(r["k"]) == k
                    and r["status"] != NOT_IMPLEMENTED]
            points, timeouts = _points_for_algorithm(runs, metric)
            if not points:
                continue

            ns, means, lows, highs, hollow = zip(*points)
            name = alg if timeouts == 0 else f"{alg} ({timeouts} timeouts)"
            line = ax.errorbar(ns, means, yerr=[lows, highs], marker="o",
                               capsize=3, label=name)[0]
            ax.plot([x for x, h in zip(ns, hollow) if h],
                    [y for y, h in zip(means, hollow) if h],
                    "o", markersize=9, markerfacecolor="white",
                    markeredgecolor=line.get_color())

        ax.set_yscale("log")
        ax.set_xticks(all_n)
        ax.set(title=f"k = {k}", xlabel="Number of cities n", ylabel=label)
        ax.grid(True, which="both", alpha=0.3)
        if ax.get_legend_handles_labels()[0]:     # only if something was drawn
            ax.legend()

    fig.suptitle(f"{label} vs n (hollow = some runs timed out, mean is a lower bound)")
    _finish_figure(fig, save_path, show)


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
