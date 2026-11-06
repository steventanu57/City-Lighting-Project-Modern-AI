"""
Multi-City Lighting: graph colouring as a CSP
CSCI323 Modern AI, Group 17. projectoverview.md explains the methods,
theory and experiments, and how to run everything.

The file is split into blocks (who wrote each one, from the commit history):
    BLOCK 0  Shared code used by every method          (Jeannice)
    BLOCK 1  Maps, A1, M3 and plots                    (Jeannice)
             M3+, an improved M3                       (Steven)
    BLOCK 2  A2 and its ablation variants              (Hong Shen)
    BLOCK 3  A3 and instance status                    (Edric)
             experiment runner and summaries           (Steven)
    BLOCK 4  Main: the demo for one n                  (Jeannice)

Code names and report names:
    A1  naive backtracking                 -> Baseline
    A2  backtracking + MRV/Degree/LCV/FC   -> M1 (established method)
    A3  min-conflicts local search         -> M2 (method from a research article)
    M3  structure-aware solver             -> M3 (proposed method)
    M3+ improved structure-aware solver    -> M3+ (faster version of M3)
"""

# =============================================================================
# BLOCK 0: SHARED CODE (used by every block)
# =============================================================================
import csv
import heapq
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
DEFAULT_TIMEOUT = 30.0    # seconds per run, for every method
DEFAULT_MAX_STEPS = 10_000  # Min-Conflicts repairs per attempt. The demo uses this;
                            # the final experiments used 1,000 with 9 restarts.

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
    constraint_checks: int = 0     # every method (counted in csp.check)
    assignment_attempts: int = 0   # backtracking: A1, A2, BT+MRV, BT+FC, M3's fallback
    backtracks: int = 0            # backtracking, same methods as above
    repair_iterations: int = 0     # A3
    restarts: int = 0              # A3, attempts after the first one


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
    """Time limit for one run. Call guard.check() inside loops / recursion.

    The clock is only read at those calls, so a run can go slightly over the
    limit before it stops. It is not a hard cutoff.
    """

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
        """Compare two colours and count one constraint check. True = allowed.
        Every method compares colours here, so their counts can be compared."""
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
      None from a complete method (A1, A2, BT+MRV, BT+FC, M3) -> UNSAT
      None from local search (A3)                             -> FAILED

    The runtime covers the call itself, including creating the time guard and
    the random number generator. It stops before the colouring is verified.
    """
    func, is_complete = ALGORITHMS[name]
    csp = MapColouringCSP(adjacency, colours)
    status = None
    start = time.perf_counter()
    try:
        colouring = func(csp, TimeGuard(timeout_seconds), random.Random(run_seed), **params)
    except SearchTimeout:
        colouring, status = None, TIMEOUT
    except NotImplementedError:
        colouring, status = None, NOT_IMPLEMENTED
    runtime = time.perf_counter() - start      # stop the timer before verifying

    if status is None:
        if colouring is None:
            status = UNSAT if is_complete else FAILED
        elif verify_solution(adjacency, colouring, colours):
            status = SAT
        else:
            raise AssertionError(f"{name} returned an invalid colouring (bug)")
    return RunResult(name, len(adjacency), len(colours), status,
                     colouring if status == SAT else None,
                     runtime, map_seed, run_seed, csp.metrics)


# =============================================================================
# BLOCK 1: MAPS, A1, M3 AND PLOTS (Jeannice)
# Makes and checks the maps, the baseline (A1), the proposed method (M3)
# and all the pictures.
#
#   1.1 Map generation      generate_cities, generate_roads, build_adjacency, make_map
#   1.2 Map validation      validate_map (+ helpers)
#   1.3 Parity check        check_3colour_parity          (k = 3 analysis)
#   1.4 Algorithm A1        backtracking_search           (naive backtracking, baseline)
#   1.5 Algorithm M3        structure_aware_solver        (proposed method)
#   1.5b Algorithm M3+      structure_aware_solver_plus   (improved M3, Steven)
#   1.6 Plots               plot_map, plot_comparison
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


def find_roads_through_cities(cities, roads):
    """Return every (road, city) where a road passes straight through another
    city (should be empty). Such a road would really be two roads."""
    problems = []
    all_cities = np.arange(len(cities))
    for a, b in roads:
        others = all_cities[(all_cities != a) & (all_cities != b)]
        p, q, r = cities[a], cities[b], cities[others]
        on_line = _orientation(p[None, :], q[None, :], r) == 0
        between = np.all((r >= np.minimum(p, q) - EPS) & (r <= np.maximum(p, q) + EPS), axis=1)
        problems += [((a, b), int(c)) for c in others[on_line & between]]
    return problems


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
    through = find_roads_through_cities(cities, roads)
    need(not through, f"roads passing through a city, e.g. {through[:3]}")

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
    """O(n) test of whether a map can be coloured with 3 colours.

    In a triangulation the neighbours of an inner city form a closed ring.
    An odd ring already needs 3 colours, so together with the centre city it
    needs 4. Outer (boundary) cities have no closed ring and are skipped.

    Returns UNSAT if some inner city has an odd number of neighbours,
    otherwise NEEDS_CHECK.

    For maps that pass validate_map() the test works both ways: a map with
    no odd inner city can always be coloured with 3 colours (see M3's
    triangle propagation and projectoverview.md, Section 4.2). It still
    returns NEEDS_CHECK rather than SAT, because SAT is only recorded once
    a solver has found and verified a colouring.
    """
    return UNSAT if odd_inner_cities(adjacency, tri) else NEEDS_CHECK


def odd_inner_cities(adjacency, tri):
    """Inner cities with an odd number of neighbours. Each one alone proves
    that the map cannot be coloured with 3 colours. Used by the parity check
    and to highlight the proof on k = 3 pictures."""
    if tri is None:                          # n < 3 or collinear: a path, no inner cities
        return []
    outer = {city for edge in boundary_edges(tri) for city in edge}
    return [city for city, neighbours in enumerate(adjacency)
            if city not in outer and len(neighbours) % 2 == 1]


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


# ---- 1.5 Algorithm M3: Structure-Aware Solver --------------------------------
def structure_aware_solver(csp, guard, rng):
    """M3. Uses the structure of the map (a planar triangulation) instead of
    generic search.

      k = 3 : triangle propagation      -> SAT colouring, or None = proven UNSAT
      k = 4 : smallest-last + Kempe chains, with A1 as a complete fallback

    Fallback indicator: Kempe colouring never touches assignment_attempts,
    so for k = 4 `metrics.assignment_attempts > 0` means A1 was used.
    """
    k = len(csp.colours)
    if k == 3:
        return _m3_triangle_propagation(csp, guard)
    if k == 4:
        return _m3_kempe_colouring(csp, guard, rng)
    raise ValueError(f"M3 supports k = 3 or k = 4, got k = {k}")


def _find_triangles(adjacency):
    """All triples of cities that are pairwise connected by roads.
    Returns (triangles, edge_to_triangles).

    This work is part of M3's runtime but adds no constraint checks, which is
    why M3 at k = 3 has few checks but a high time per check."""
    triangles = []
    edge_to_triangles = {}
    for u in range(len(adjacency)):
        for v in adjacency[u]:
            if v <= u:
                continue
            for w in adjacency[u] & adjacency[v]:
                if w <= v:
                    continue
                t = len(triangles)
                triangles.append((u, v, w))
                for edge in ((u, v), (v, w), (u, w)):
                    edge_to_triangles.setdefault(edge, []).append(t)
    return triangles, edge_to_triangles


def _m3_two_colouring(csp, guard):
    """Graph without triangles (n < 3 or collinear cities: a path).
    Colour it with two alternating colours by breadth-first search."""
    first, second = csp.colours[0], csp.colours[1]
    colour = {}
    for start in csp.variables:
        if start in colour:
            continue
        colour[start] = first
        queue = [start]
        for city in queue:
            guard.check()
            other = second if colour[city] == first else first
            for nb in csp.neighbours[city]:
                if nb not in colour:
                    colour[nb] = other
                    queue.append(nb)
                elif not csp.check(colour[nb], colour[city]):
                    raise RuntimeError("M3: map without triangles is not 2-colourable; "
                                       "this map does not satisfy M3's assumptions")
    return colour


def _m3_triangle_propagation(csp, guard):
    """k = 3. Colour one triangle R, G, B, then spread through triangles that
    share an edge: the third city of each triangle has only one colour left.

    A conflict proves that no 3-colouring exists (any 3-colouring would be
    reproduced exactly, up to renaming colours), so None means UNSAT.

    Why visited triangles can be skipped: a city's colour is set once and never
    changed, and when a triangle is visited all three of its roads are checked
    (x != y, and w gets the third colour). A later visit through another shared
    edge would only re-check the same, unchanged colours.
    """
    triangles, edge_to_triangles = _find_triangles(csp.neighbours)
    if not triangles:
        return _m3_two_colouring(csp, guard)

    colour = dict(zip(triangles[0], csp.colours))
    visited = {0}
    queue = [0]
    for t in queue:
        a, b, c = triangles[t]
        for x, y in ((a, b), (b, c), (a, c)):
            for t2 in edge_to_triangles[(x, y)]:
                if t2 in visited:
                    continue
                guard.check()
                visited.add(t2)
                queue.append(t2)

                # conflict type 1: the two shared cities already have the same colour
                if not csp.check(colour[x], colour[y]):
                    return None
                w = next(city for city in triangles[t2] if city not in (x, y))
                forced = next(col for col in csp.colours
                              if csp.check(col, colour[x]) and csp.check(col, colour[y]))
                if w not in colour:
                    colour[w] = forced
                elif csp.check(colour[w], forced):
                    # conflict type 2: the third city already has another colour
                    return None

    if len(colour) < csp.n:
        raise RuntimeError("M3: some cities were not reached by triangle propagation; "
                           "this map does not satisfy M3's assumptions")
    return colour


def _smallest_last_order(csp, guard):
    """Repeatedly remove the city with the fewest remaining neighbours; colour
    in the reverse order. In a planar map a removed city always has <= 5
    remaining neighbours, so each city sees at most 5 coloured neighbours.
    With 4 colours those 5 can still block every colour, which is when a
    Kempe swap is needed.

    Each removal scans all remaining cities, so the ordering is O(n^2)."""
    degree = {v: len(csp.neighbours[v]) for v in csp.variables}
    removed = []
    remaining = set(csp.variables)
    while remaining:
        guard.check()
        v = min(remaining, key=lambda city: (degree[city], city))
        remaining.remove(v)
        removed.append(v)
        for nb in csp.neighbours[v]:
            if nb in remaining:
                degree[nb] -= 1
    return removed[::-1]


def _kempe_chain(csp, guard, start, colour, a, b):
    """All coloured cities reachable from `start` using only colours a and b."""
    chain = {start}
    stack = [start]
    while stack:
        guard.check()
        city = stack.pop()
        for nb in csp.neighbours[city]:
            if nb in colour and nb not in chain and (
                    not csp.check(colour[nb], a) or not csp.check(colour[nb], b)):
                chain.add(nb)
                stack.append(nb)
    return chain


def _swap(colour, chain, a, b):
    """Swap colours a and b on every city in the chain."""
    for city in chain:
        colour[city] = b if colour[city] == a else a


def _free_colour_with_kempe(csp, guard, v, colour):
    """Try to free a colour for v by swapping one Kempe chain. Returns the freed
    colour, or None if no single swap works. That can happen, which is why
    M3 keeps A1 as a fallback."""
    for a in csp.colours:
        for b in csp.colours:
            if a == b:
                continue
            for start in [nb for nb in csp.neighbours[v]
                          if nb in colour and not csp.check(colour[nb], a)]:
                chain = _kempe_chain(csp, guard, start, colour, a, b)
                _swap(colour, chain, a, b)
                if csp.is_consistent(v, a, colour):
                    return a
                _swap(colour, chain, a, b)          # undo, try the next chain
    return None


def _m3_kempe_colouring(csp, guard, rng):
    """k = 4. Smallest-last order + Kempe chain recolouring. If no swap frees a
    colour, A1 colours the whole map again from scratch, under the same time
    limit, as a complete fallback."""
    colour = {}
    for v in _smallest_last_order(csp, guard):
        guard.check()
        free = next((c for c in csp.colours if csp.is_consistent(v, c, colour)), None)
        if free is None:
            free = _free_colour_with_kempe(csp, guard, v, colour)
        if free is None:
            result = backtracking_search(csp, guard, rng)     # complete fallback
            if result is None:
                raise RuntimeError("M3: A1 found no 4-colouring, which is impossible "
                                   "for a planar map; check the input map")
            return result
        colour[v] = free
    return colour


# ---- 1.5b Algorithm M3+: refined M3 -----------------------------------------
# Added after the presentation, when we were asked if M3 could be improved.
# M3 is left as it was, so the final results still match it.
def structure_aware_solver_plus(csp, guard, rng):
    """M3+. Works like M3 but skips work M3 did for nothing.

      k = 3 : only finds a triangle when propagation gets to it, so on most
              maps it stops at the first conflict before finding the rest
      k = 4 : smallest-last order from a heap, and a Kempe swap that doesn't
              build chains that can't work
      fallback: M1 instead of A1, since A1 is too slow on big maps

    For k = 4 the colouring is the same as M3's, just with fewer checks.
    assignment_attempts > 0 means the fallback ran, same as M3.
    """
    k = len(csp.colours)
    if k == 3:
        return _m3plus_lazy_propagation(csp, guard)
    if k == 4:
        return _m3plus_kempe_colouring(csp, guard, rng)
    raise ValueError(f"M3+ supports k = 3 or k = 4, got k = {k}")


def _m3plus_lazy_propagation(csp, guard):
    """k = 3. Same idea as _m3_triangle_propagation, except we don't list all
    the triangles first. When we reach an edge (x, y), the third cities are
    just the common neighbours of x and y. The order we visit triangles in
    doesn't change the answer (lemma in projectoverview.md, Section 4.2),
    so None still means UNSAT."""
    adjacency = csp.neighbours
    first = None
    for u in csp.variables:                  # same first triangle as M3
        for v in adjacency[u]:
            if v > u:
                third = [w for w in adjacency[u] & adjacency[v] if w > v]
                if third:
                    first = (u, v, third[0])
                    break
        if first:
            break
    if first is None:
        return _m3_two_colouring(csp, guard)

    colour = dict(zip(first, csp.colours))
    visited = {frozenset(first)}
    queue = [first]
    for a, b, c in queue:
        for x, y in ((a, b), (b, c), (a, c)):
            for w in adjacency[x] & adjacency[y]:
                triangle = frozenset((x, y, w))
                if triangle in visited:
                    continue
                guard.check()
                visited.add(triangle)
                queue.append((x, y, w))

                if not csp.check(colour[x], colour[y]):
                    return None
                forced = next(col for col in csp.colours
                              if csp.check(col, colour[x]) and csp.check(col, colour[y]))
                if w not in colour:
                    colour[w] = forced
                elif csp.check(colour[w], forced):
                    return None

    if len(colour) < csp.n:
        raise RuntimeError("M3+: some cities were not reached by triangle propagation; "
                           "this map does not satisfy M3's assumptions")
    return colour


def _m3plus_smallest_last_order(csp, guard):
    """Gives the same order as _smallest_last_order, but uses a heap to find
    the city with the fewest neighbours left instead of scanning all of them
    every time (O(m log n) instead of O(n^2)). When a city's degree drops we
    just push it again and skip the old entry when it comes out."""
    degree = {v: len(csp.neighbours[v]) for v in csp.variables}
    queue = [(d, v) for v, d in degree.items()]
    heapq.heapify(queue)
    removed, gone = [], set()
    while queue:
        guard.check()
        d, v = heapq.heappop(queue)
        if v in gone or d != degree[v]:
            continue
        gone.add(v)
        removed.append(v)
        for nb in csp.neighbours[v]:
            if nb not in gone:
                degree[nb] -= 1
                heapq.heappush(queue, (degree[nb], nb))
    return removed[::-1]


def _m3plus_free_colour(csp, guard, v, colour):
    """Same result as _free_colour_with_kempe, but cheaper.

    Swapping a and b on a chain only frees colour a for v if all of v's
    a-coloured neighbours are in the chain and none of its b-coloured ones
    are. So we only need one chain per (a, b) pair, we can stop walking as
    soon as we hit a b-neighbour, and we only swap when it's going to work
    (M3 swapped first, checked, then swapped back). The pairs are tried in
    the same order as M3, so it picks the same swap."""
    coloured = [nb for nb in csp.neighbours[v] if nb in colour]
    for a in csp.colours:
        a_neighbours = [nb for nb in coloured if not csp.check(colour[nb], a)]
        if not a_neighbours:
            continue
        for b in csp.colours:
            if a == b:
                continue
            b_neighbours = {nb for nb in coloured if not csp.check(colour[nb], b)}
            start = a_neighbours[0]
            chain, stack, blocked = {start}, [start], False
            while stack and not blocked:
                guard.check()
                city = stack.pop()
                for nb in csp.neighbours[city]:
                    if nb in colour and nb not in chain and (
                            not csp.check(colour[nb], a) or not csp.check(colour[nb], b)):
                        if nb in b_neighbours:
                            blocked = True      # this neighbour would turn into a
                            break
                        chain.add(nb)
                        stack.append(nb)
            if not blocked and all(nb in chain for nb in a_neighbours):
                _swap(colour, chain, a, b)
                return a
    return None


def _m3plus_kempe_colouring(csp, guard, rng):
    """k = 4. Same as _m3_kempe_colouring but with the faster order and Kempe
    swap. If no swap works, M1 colours the map from scratch (same time limit)."""
    colour = {}
    for v in _m3plus_smallest_last_order(csp, guard):
        guard.check()
        free = next((c for c in csp.colours if csp.is_consistent(v, c, colour)), None)
        if free is None:
            free = _m3plus_free_colour(csp, guard, v, colour)
        if free is None:
            result = backtracking_fc(csp, guard, rng)          # fallback: M1
            if result is None:
                raise RuntimeError("M3+: M1 found no 4-colouring, which is impossible "
                                   "for a planar map; check the input map")
            return result
        colour[v] = free
    return colour


# ---- 1.6 Plots ----------------------------------------------------------------
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
             save_path=None, show=SHOW_PLOTS, highlight=None):
    """Draw the map. colouring=None gives a blank map (black cities);
    otherwise colouring = {city: colour name}. Only pass SAT colourings.

    highlight: optional list of cities to mark with a red ring (used to show
    the inner cities with an odd number of neighbours on k = 3 UNSAT maps).
    """
    fig, ax = plt.subplots(figsize=(8, 7))

    for a, b in roads:
        ax.plot(*zip(cities[a], cities[b]), color="gray", linewidth=1, zorder=1)

    if highlight:
        marked = list(highlight)
        ax.scatter(cities[marked, 0], cities[marked, 1], s=260, facecolors="none",
                   edgecolors="red", linewidths=2, zorder=3,
                   label="inner city with an odd number of neighbours")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), frameon=False)

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


UNANSWERED = (TIMEOUT, FAILED)      # statuses that prove nothing


def _points_for_algorithm(runs, metric):
    """Mean, error bars and hollow flags per n for one algorithm and one k.
    Returns (points, unanswered) where points = list of (n, mean, low, high, hollow)."""
    points, unanswered = [], 0
    for n in sorted({int(r["n"]) for r in runs}):
        at_n = [r for r in runs if int(r["n"]) == n]
        finished = [float(r[metric]) for r in at_n if r["status"] not in UNANSWERED]
        unanswered += len(at_n) - len(finished)
        if not finished or np.mean(finished) <= 0:     # nothing to show on a log axis
            continue
        mean, std = np.mean(finished), np.std(finished)
        low = min(std, mean - min(finished))           # keep error bar above 0 on log axis
        points.append((n, mean, low, std, len(finished) < len(at_n)))
    return points, unanswered


def plot_comparison(rows, metric="runtime_seconds", save_path=None, show=SHOW_PLOTS):
    """Plot `metric` against n: one subplot per k, one line per algorithm.

    rows   : list of dicts from RunResult.to_row() (or read back from results.csv)
    metric : "runtime_seconds" or "constraint_checks"

    Unanswered rule (summarise_results uses the same rule):
      - TIMEOUT and FAILED runs prove nothing, so they are left out of the
        mean and std (NOT_IMPLEMENTED runs are ignored completely).
        SAT and UNSAT runs are real answers and are included.
      - If some runs at an n were unanswered, the point is HOLLOW: the mean
        only covers the answered runs, so the real cost is higher.
      - If every run at an n was unanswered, no point is drawn for that n.
      - The legend shows how many runs of each algorithm were unanswered,
        also for an algorithm that answered nothing at all.
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
        for i, alg in enumerate(algorithms):
            colour = f"C{i}"                       # same colour for an algorithm in every panel
            runs = [r for r in rows if r["algorithm"] == alg and int(r["k"]) == k
                    and r["status"] != NOT_IMPLEMENTED]
            if not runs:
                continue
            points, unanswered = _points_for_algorithm(runs, metric)
            name = f"{alg} ({REPORT_NAMES[alg]})" if alg in REPORT_NAMES else alg
            if unanswered:
                name += f", {unanswered}/{len(runs)} unanswered"
            if not points:                         # nothing answered: legend entry only
                ax.plot([], [], marker="o", linestyle="none", color=colour,
                        markerfacecolor="white", label=name)
                continue

            ns, means, lows, highs, hollow = zip(*points)
            line = ax.errorbar(ns, means, yerr=[lows, highs], marker="o", color=colour,
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

    fig.suptitle(f"{label} vs n (hollow = some runs timed out or failed; "
                 "mean covers answered runs only)")
    _finish_figure(fig, save_path, show)


# =============================================================================
# BLOCK 2: A2 (MRV + DEGREE + LCV + FORWARD CHECKING) (Hong Shen)
# Complete backtracking with heuristics, plus the ablation variants.
# Colours are only compared through csp.check(), like every other method.
# =============================================================================
def select_unassigned_variable(csp, assignment, domains, use_mrv=True, use_fc=True):
    """Choose the next unassigned city using MRV and the degree tie-break.

    With forward checking disabled, count colours consistent with the current
    assignment instead of relying on domains that have not been pruned.
    Ties go to the city with the most unassigned neighbours, then lowest index.
    When MRV is disabled, choose the lowest-index unassigned city.

    This scans every unassigned city on each call. With forward checking on,
    the scan adds no constraint checks, so A2's time per check grows with n.
    """
    unassigned = [v for v in csp.variables if v not in assignment]

    if not use_mrv:
        return unassigned[0]

    def remaining_values(var):
        return sum(
            csp.is_consistent(var, value, assignment)
            for value in domains[var]
        )

    return min(
        unassigned,
        key=lambda v: (
            len(domains[v]) if use_fc else remaining_values(v),
            -sum(1 for nb in csp.neighbours[v] if nb not in assignment),
            v,
        ),
    )


def order_domain_values(csp, var, assignment, domains, use_lcv=True):
    """Order a city's available colours using the least-constraining value.

    LCV puts first the colour that rules out the fewest values in unassigned
    neighbours. When disabled, colours keep their current order.
    """
    if not use_lcv:
        return list(domains[var])

    def eliminated_options(value):
        eliminated = 0

        for nb in csp.neighbours[var]:
            if nb in assignment:
                continue

            for neighbour_value in domains[nb]:
                if not csp.check(value, neighbour_value):
                    eliminated += 1

        return eliminated

    return sorted(domains[var], key=eliminated_options)


def forward_check(csp, var, value, assignment, domains):
    """Remove `value` from the colours left for each unassigned neighbour.

    Returns (new_domains, ok). ok is False as soon as a neighbour has no
    colour left. Only the changed neighbours get new lists; the others share
    the old lists, which are never changed in place.
    """
    new_domains = domains.copy()

    for nb in csp.neighbours[var]:
        if nb in assignment:
            continue

        new_domains[nb] = [
            neighbour_value
            for neighbour_value in domains[nb]
            if csp.check(value, neighbour_value)
        ]

        if not new_domains[nb]:
            return new_domains, False

    return new_domains, True


def backtracking_generic(csp, guard, rng, use_mrv=True, use_lcv=True, use_fc=True):
    """Complete backtracking. MRV, LCV and forward checking can each be turned
    off, which is how the ablation variants are made.

    A colour that fails is removed from the assignment before the next one
    is tried. Each level of recursion gets its own domains, so going back
    needs no undo step. is_consistent() is still called when forward
    checking is on, and those checks are counted.
    """
    assignment = {}
    domains = {
        v: list(csp.domains[v]) for v in csp.variables
    }

    def backtrack(current_domains):
        guard.check()

        if len(assignment) == csp.n:
            return dict(assignment)

        var = select_unassigned_variable(
            csp, assignment, current_domains, use_mrv, use_fc
        )

        values = order_domain_values(
            csp, var, assignment, current_domains, use_lcv
        )

        for value in values:
            guard.check()
            csp.metrics.assignment_attempts += 1

            if csp.is_consistent(var, value, assignment):
                assignment[var] = value

                if use_fc:
                    next_domains, ok = forward_check(
                        csp, var, value, assignment, current_domains
                    )
                else:
                    next_domains, ok = current_domains, True

                if ok:
                    result = backtrack(next_domains)

                    if result is not None:
                        return result

                del assignment[var]
                csp.metrics.backtracks += 1

        return None

    return backtrack(domains)


def backtracking_fc(csp, guard, rng):
    """Run A2 with MRV, degree tie-breaking, LCV and forward checking."""
    return backtracking_generic(
        csp, guard, rng,
        use_mrv=True, use_lcv=True, use_fc=True
    )


# Ablation variants: A2 with some of its parts turned off.
def bt_mrv(csp, guard, rng):
    """Backtrack with MRV and degree tie-breaking, without LCV or FC."""
    return backtracking_generic(
        csp, guard, rng,
        use_mrv=True, use_lcv=False, use_fc=False
    )


def bt_fc(csp, guard, rng):
    """Backtrack with forward checking but no MRV or LCV."""
    return backtracking_generic(
        csp, guard, rng,
        use_mrv=False, use_lcv=False, use_fc=True
    )

# =============================================================================
# BLOCK 3: A3 (MIN-CONFLICTS) AND EXPERIMENTS
# min_conflicts and determine_instance_status (Edric); run_experiment and
# summarise_results (Steven). Produces the comparison data for requirement (d).
# =============================================================================
def min_conflicts(csp, guard, rng, max_steps=DEFAULT_MAX_STEPS, max_restarts=0):
    """Repair a random complete colouring using Min-Conflicts.

    max_steps is the repair limit per attempt. max_restarts counts extra
    attempts, so the total repair limit is (max_restarts + 1) * max_steps.
    All attempts share the same time limit and random number generator.

    After each repair only the changed city and its neighbours have their
    conflict status updated. The conflicted cities are sorted before
    rng.choice, so the same seed always picks the same city.
    Returns a colouring, or None when all attempts fail (this does not
    prove UNSAT).
    """
    for name, value in (("max_steps", max_steps), ("max_restarts", max_restarts)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")

    for attempt in range(max_restarts + 1):
        guard.check()
        if attempt > 0:
            csp.metrics.restarts += 1

        assignment = {}
        for city in csp.variables:
            guard.check()
            assignment[city] = rng.choice(csp.colours)

        # Find all conflicting cities once at the start of this attempt.
        conflicted = set()
        for city in csp.variables:
            guard.check()
            if csp.count_conflicts(city, assignment[city], assignment) > 0:
                conflicted.add(city)

        # Also check the colouring after the last allowed repair.
        for step in range(max_steps + 1):
            guard.check()
            if not conflicted:
                return assignment
            if step == max_steps:
                break

            city = rng.choice(sorted(conflicted))
            scores = []
            for colour in csp.colours:
                guard.check()
                scores.append(csp.count_conflicts(city, colour, assignment))

            minimum = min(scores)
            best_colours = [colour for colour, score in zip(csp.colours, scores)
                            if score == minimum]
            assignment[city] = rng.choice(best_colours)
            csp.metrics.repair_iterations += 1

            # Other cities cannot be affected by this colour change.
            affected = csp.neighbours[city] | {city}
            for other in sorted(affected):
                guard.check()
                if csp.count_conflicts(other, assignment[other], assignment) > 0:
                    conflicted.add(other)
                else:
                    conflicted.discard(other)

    return None


def determine_instance_status(k, parity_label, runs):
    """Label one map and k as SOLVABLE, UNSAT or UNRESOLVED from all its runs.

    SOLVABLE    a run found a verified colouring, or k = 4 (Four Colour Theorem)
    UNSAT       k = 3 with an inner city of odd degree, or a complete method
                searched everything and returned UNSAT
    UNRESOLVED  neither a colouring nor a proof of impossibility
    FAILED, TIMEOUT and NOT_IMPLEMENTED runs count as no evidence either way.

    All runs must come from the same validated map and the same k; the
    function can only check this when map seeds are given. Raises ValueError
    for bad labels, runs from different maps, UNSAT from local search, or
    results that contradict each other.
    """
    if k not in (3, 4):
        raise ValueError("k must be 3 or 4")
    if parity_label not in (NEEDS_CHECK, UNSAT):
        raise ValueError("Invalid parity result")

    solvable = k == 4
    impossible = k == 3 and parity_label == UNSAT
    if len({(run.n, run.map_seed) for run in runs}) > 1:
        raise ValueError("Runs must belong to the same map")

    for run in runs:
        if run.k != k or run.algorithm not in ALGORITHMS:
            raise ValueError("Run does not match the experiment")
        if run.status not in (SAT, UNSAT, FAILED, TIMEOUT, NOT_IMPLEMENTED):
            raise ValueError("Invalid run status")

        if run.status == SAT:
            solvable = True
        elif run.status == UNSAT:
            if not ALGORITHMS[run.algorithm][1]:
                raise ValueError("This algorithm cannot prove UNSAT")
            impossible = True

    if solvable and impossible:
        raise ValueError("Results contradict each other")
    if solvable:
        return SOLVABLE
    if impossible:
        return UNSAT
    return UNRESOLVED


def run_experiment(n_values, k_values=(3, 4), trials=10,
                   algorithms=("A1", "A2", "A3", "M3"), timeout_seconds=DEFAULT_TIMEOUT,
                   max_steps=DEFAULT_MAX_STEPS, a3_runs=5, csv_path="results.csv",
                   max_restarts=0):
    """Run all algorithms on the SAME maps and save results.csv.

    For every n, `trials` maps are made with the fixed seed 1000 * n + trial,
    so every algorithm sees exactly the same maps and a rerun gives the same
    maps. Complete algorithms run once per (map, k). Local search (A3) is
    random, so it runs `a3_runs` times with run seeds 0, 1, 2, ...

    A3 gets max_steps repairs per attempt and max_restarts extra attempts,
    all under one time limit. The defaults give one attempt of 10,000
    repairs. The final experiments used max_steps=1000, max_restarts=9,
    which also allows at most 10,000 repairs per run. a3_runs counts whole runs.

    Each row is RunResult.to_row() plus two columns:
      parity          : check_3colour_parity() for k = 3, "N/A" for k = 4
      instance_status : determine_instance_status() for that (map, k)
    Returns the rows. csv_path is rewritten after every map, so a run that
    stops early (crash or Ctrl+C) keeps the finished maps.
    """
    for name, value in (("trials", trials), ("a3_runs", a3_runs)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    for name, value in (("max_steps", max_steps), ("max_restarts", max_restarts)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    if timeout_seconds is not None and (not np.isfinite(timeout_seconds) or timeout_seconds < 0):
        raise ValueError("timeout_seconds must be finite and non-negative, or None")
    n_values, k_values, algorithms = list(n_values), tuple(k_values), tuple(algorithms)
    if not n_values or any(isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 1 for n in n_values):
        raise ValueError("n_values must contain positive integers")
    if not k_values or any(k not in COLOURS_BY_K for k in k_values):
        raise ValueError("k_values must contain 3 or 4")
    if not algorithms or any(name not in ALGORITHMS for name in algorithms):
        raise ValueError("Unknown or empty algorithm list")
    if len(set(n_values)) != len(n_values) or len(set(k_values)) != len(k_values) or len(set(algorithms)) != len(algorithms):
        raise ValueError("Experiment lists must not contain duplicates")
    if trials >= 1000:
        raise ValueError("trials must be below 1000 (map seed = 1000 * n + trial)")

    rows = []
    for n in n_values:
        start = time.perf_counter()
        for trial in range(trials):
            map_seed = 1000 * n + trial
            m = make_map(n, map_seed)
            parity = check_3colour_parity(m["adjacency"], m["triangulation"])

            for k in k_values:
                runs = []
                for name in algorithms:
                    is_complete = ALGORITHMS[name][1]
                    run_seeds = [0] if is_complete else range(a3_runs)
                    params = {} if is_complete else {"max_steps": max_steps,
                                                      "max_restarts": max_restarts}
                    for run_seed in run_seeds:
                        runs.append(run_algorithm(name, m["adjacency"], COLOURS_BY_K[k],
                                                  map_seed=map_seed, run_seed=run_seed,
                                                  timeout_seconds=timeout_seconds, **params))

                status = determine_instance_status(k, parity, runs)
                for run in runs:
                    row = run.to_row()
                    row["parity"] = parity if k == 3 else "N/A"
                    row["instance_status"] = status
                    rows.append(row)
            save_results_csv(rows, csv_path)       # after every map, see docstring
        print(f"run_experiment: n={n} done ({trials} maps, {time.perf_counter() - start:.1f}s)")

    return rows


def save_results_csv(rows, csv_path="results.csv"):
    """Write a list of dicts to a CSV file, one row per run."""
    if rows:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def summarise_results(rows):
    """Table per (n, k): #SOLVABLE/#UNSAT/#UNRESOLVED, % finished for A1/A2,
    A3 success rate (on SOLVABLE maps only), mean/std runtime and checks.
    Also the status counts and the M3 fallback rate (projectoverview.md, Section 5.2).

    rows: from run_experiment(), or read back from results.csv (all strings).
    Same rule as plot_comparison: TIMEOUT and FAILED runs prove nothing, so only
    runs that ended in SAT or UNSAT count in the mean and std, and a mean that
    leaves runs out is marked with *. NOT_IMPLEMENTED runs are ignored.
    Prints three tables (instances, outcomes, cost) and returns
    {"instances": [...], "algorithms": [...]}.
    """
    if not rows:
        print("summarise_results: no rows to summarise, skipped.")
        return {"instances": [], "algorithms": []}

    groups = sorted({(int(r["n"]), int(r["k"])) for r in rows})
    algorithms = list(dict.fromkeys(r["algorithm"] for r in rows))   # first-seen order

    # Instances: one per (map, k); every row of a map carries its status
    instances = []
    for n, k in groups:
        status_of_map = {r["map_seed"]: r["instance_status"] for r in rows
                         if int(r["n"]) == n and int(r["k"]) == k}
        counts = Counter(status_of_map.values())
        instances.append({"n": n, "k": k, "maps": len(status_of_map),
                          SOLVABLE: counts[SOLVABLE], UNSAT: counts[UNSAT],
                          UNRESOLVED: counts[UNRESOLVED]})

    # Algorithms: one line per (n, k, algorithm)
    summary = []
    for n, k in groups:
        for alg in algorithms:
            runs = [r for r in rows if int(r["n"]) == n and int(r["k"]) == k
                    and r["algorithm"] == alg]
            if not runs:
                continue
            implemented = [r for r in runs if r["status"] != NOT_IMPLEMENTED]
            answered = [r for r in implemented if r["status"] not in UNANSWERED]
            statuses = Counter(r["status"] for r in implemented)
            line = {"n": n, "k": k, "algorithm": alg, "runs": len(runs),
                    "implemented": bool(implemented),
                    SAT: statuses[SAT], UNSAT: statuses[UNSAT],
                    FAILED: statuses[FAILED], TIMEOUT: statuses[TIMEOUT],
                    "finished_pct": None, "success_pct": None, "fallback_pct": None,
                    "runtime_mean": None, "runtime_std": None,
                    "checks_mean": None, "checks_std": None}

            is_complete = ALGORITHMS[alg][1]
            if implemented and is_complete:              # complete: SAT or UNSAT = finished
                line["finished_pct"] = 100 * len(answered) / len(implemented)
            on_solvable = [r for r in implemented if r["instance_status"] == SOLVABLE]
            if on_solvable and not is_complete:          # local search: SOLVABLE maps only
                line["success_pct"] = 100 * sum(r["status"] == SAT
                                                for r in on_solvable) / len(on_solvable)
            if implemented and alg in ("M3", "M3+") and k == 4:   # fallback indicator (Section 3)
                line["fallback_pct"] = 100 * sum(int(r["assignment_attempts"]) > 0
                                                 for r in implemented) / len(implemented)
            if answered:
                runtimes = [float(r["runtime_seconds"]) for r in answered]
                checks = [float(r["constraint_checks"]) for r in answered]
                line.update(runtime_mean=np.mean(runtimes), runtime_std=np.std(runtimes),
                            checks_mean=np.mean(checks), checks_std=np.std(checks))
            summary.append(line)

    def pct(value):
        return "-" if value is None else f"{value:.0f}%"

    def head(row):
        return f"{row['n']:>5} {row['k']:>2}  {row['algorithm']:<9} {row['runs']:>5}"

    print("\nInstances (one per map and k)")
    print(f"{'n':>5} {'k':>2} {'maps':>5} {SOLVABLE:>9} {UNSAT:>6} {UNRESOLVED:>11}")
    for row in instances:
        print(f"{row['n']:>5} {row['k']:>2} {row['maps']:>5} {row[SOLVABLE]:>9} "
              f"{row[UNSAT]:>6} {row[UNRESOLVED]:>11}")

    print("\nOutcomes per algorithm")
    print("  finished = complete methods: % of runs that ended in SAT or UNSAT")
    print("  success  = local search: % of runs that found a colouring, on SOLVABLE maps only")
    print("  fallback = M3/M3+ with k = 4: % of runs that used the fallback (A1 for M3, M1 for M3+)")
    print(f"{'n':>5} {'k':>2}  {'algorithm':<9} {'runs':>5} {SAT:>5} {UNSAT:>6} {FAILED:>7} "
          f"{TIMEOUT:>8} {'finished':>9} {'success':>8} {'fallback':>9}")
    for row in summary:
        if not row["implemented"]:
            print(f"{head(row)}  not implemented")
            continue
        print(f"{head(row)} {row[SAT]:>5} {row[UNSAT]:>6} {row[FAILED]:>7} {row[TIMEOUT]:>8} "
              f"{pct(row['finished_pct']):>9} {pct(row['success_pct']):>8} "
              f"{pct(row['fallback_pct']):>9}")

    print("\nCost per algorithm (mean +/- std over runs that ended in SAT or UNSAT;")
    print("  * = some runs timed out or failed and are left out, so the real cost is higher)")
    print(f"{'n':>5} {'k':>2}  {'algorithm':<9} {'runs':>5} {'runtime (s)':>22} "
          f"{'constraint checks':>28}")
    for row in summary:
        if row["runtime_mean"] is None:
            print(f"{head(row)}  {'every run timed out or failed' if row['implemented'] else 'not implemented'}")
            continue
        print(f"{head(row)} {row['runtime_mean']:>11.4f} +/- {row['runtime_std']:<8.4f}"
              f"{row['checks_mean']:>15,.0f} +/- {row['checks_std']:<10,.0f}"
              f"{'*' if row[TIMEOUT] or row[FAILED] else ''}")

    return {"instances": instances, "algorithms": summary}


# =============================================================================
# ALGORITHM REGISTRY
# name -> (function, is_complete). The names are stored in the CSV files,
# so renaming one would break reading old results.
# =============================================================================
ALGORITHMS = {
    "A1": (backtracking_search, True),
    "A2": (backtracking_fc, True),
    "A3": (min_conflicts, False),
    "BT+MRV": (bt_mrv, True),
    "BT+FC": (bt_fc, True),
    "M3": (structure_aware_solver, True),
    "M3+": (structure_aware_solver_plus, True),
}


# =============================================================================
# BLOCK 4: MAIN (Jeannice)
# =============================================================================
COMPARED_ALGORITHMS = ("A1", "A2", "A3", "M3", "M3+")   # baseline, 3 methods, M3+
REPORT_NAMES = {"A1": "Baseline", "A2": "M1", "A3": "M2", "M3": "M3", "M3+": "M3+"}


def demo_single_map(n, seed=42):
    """Requirements (a), (b), (c), (e) for one n.

    Uses map seed 42 and runs every compared method with k = 3 and k = 4,
    saving one PNG per result. A3 runs with its defaults (one attempt of
    10,000 repairs), not the restart settings of the final experiments.
    """
    m = make_map(n, seed)
    print(f"Cities: {n} | Roads: {len(m['roads'])}")
    saved = [f"map_n{n}.png"]
    plot_map(m["cities"], m["roads"], title=f"Blank map (n={n})", save_path=saved[0])

    odd = odd_inner_cities(m["adjacency"], m["triangulation"])
    if odd:
        print(f"\n3 colours are impossible for this map: inner cities {odd} "
              "have an odd number of neighbours (ringed in red on the k = 3 maps).")

    for k in (3, 4):
        print(f"\nk = {k}")
        for name in COMPARED_ALGORITHMS:
            label = f"{name} ({REPORT_NAMES[name]})"
            res = run_algorithm(name, m["adjacency"], COLOURS_BY_K[k],
                                map_seed=seed, run_seed=0)
            print(f"  {label:15s} {res.status:16s} {res.runtime_seconds:.4f}s "
                  f"checks={res.metrics.constraint_checks}")
            if res.status == NOT_IMPLEMENTED:
                continue
            show_proof = k == 3 and res.status != SAT and odd
            path = f"map_n{n}_k{k}_{name}.png"
            plot_map(m["cities"], m["roads"], res.colouring,
                     title=f"n={n}, k={k}, {label}: {res.status}",
                     save_path=path, highlight=odd if show_proof else None)
            saved.append(path)

    print("\nSaved in the folder the program was run from:")
    for path in saved:
        print(f"  {path}")


def ask_number_of_cities():
    """Ask until the user types a whole number of at least 1."""
    while True:
        text = input("Enter the number of cities n: ").strip()
        try:
            n = int(text)
        except ValueError:
            print(f"  '{text}' is not a whole number. Please try again.")
            continue
        if n < 1:
            print("  n must be at least 1. Please try again.")
            continue
        return n


def main():
    n = ask_number_of_cities()
    demo_single_map(n)

    # Requirement (d) is run separately, with the commands in
    # projectoverview.md, Section 9.2. The main comparison, for example:
    # rows = run_experiment([5, 10, 20, 30, 50, 75, 100],
    #                       algorithms=COMPARED_ALGORITHMS,
    #                       max_steps=1000, max_restarts=9)
    # summarise_results(rows)
    # plot_comparison(rows, "runtime_seconds", "compare_time.png")
    # plot_comparison(rows, "constraint_checks", "compare_checks.png")


if __name__ == "__main__":
    main()