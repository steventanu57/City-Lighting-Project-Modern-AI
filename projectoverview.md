# Multi-City Lighting — Graph Colouring as a CSP

Modern AI Assignment · Chapter 4: Constraint Satisfaction Problems

## 1. What the program does

1. Place *n* random cities on a 2D map and connect them with the maximum number of straight, non-crossing roads.
2. Colour ("light") every city so that two cities joined by a road never share a colour:
   - with **3 colours**: Red, Green, Blue
   - with **4 colours**: Red, Green, Blue, Yellow
3. Solve the colouring with **three different algorithms** and compare their performance as *n* grows.
4. Plot the blank map and the coloured map for a chosen *n* and *k*.

| Assignment requirement | Where in the program |
|---|---|
| (a) generate and plot map from user input *n* | Block 1 (map) + Block 4 (main) |
| (b) colour with 3 colours | Blocks 1–3 (algorithms), k = 3 |
| (c) colour with 4 colours | Blocks 1–3 (algorithms), k = 4 |
| (d) three algorithms, compare vs *n* | A1, A2, A3 + Block 3 (experiments) |
| (e) plot coloured map for given *n*, *k* | Block 1 (`plot_map`) + Block 4 |

## 2. How it works

### Map
- Cities: random points in [0, 1] × [0, 1], with a seed so results can be reproduced.
- Roads: **Delaunay triangulation**. It gives non-crossing straight roads, and no extra road can be added without crossing one, so the map is "maximally connected". Number of roads = 3n − 3 − h (h = cities on the outer boundary).
- Every map is checked by `validate_map()` (no crossings, no missing cities, correct road count).

### CSP formulation
| | |
|---|---|
| Variables | the cities |
| Domain | {R, G, B} for k = 3, {R, G, B, Y} for k = 4 |
| Constraint | for every road (i, j): colour(i) ≠ colour(j) |

### Algorithms
| | Algorithm | Type | Idea |
|---|---|---|---|
| A1 | Naive Backtracking | complete | try colours in fixed order, go back on conflict |
| A2 | Backtracking + MRV + Degree + LCV + Forward Checking | complete + heuristics | pick the most constrained city first, try the least constraining colour, remove impossible colours from neighbours early |
| A3 | Min-Conflicts | local search | start with random colours, repeatedly fix a conflicting city; fast but may fail even if a solution exists |

### Things to keep in mind
- **k = 4 always has a solution** (the map is planar → Four Colour Theorem).
- **k = 3 often has no solution.** If an inner city has an odd number of neighbours, its neighbours form an odd ring, which needs 4 colours. This check proves "no solution", but passing it does not prove a solution exists.
- Results use these statuses:
  - `SAT`: solution found and verified
  - `UNSAT`: complete search finished, no solution exists
  - `TIMEOUT`: ran out of time; this proves nothing
  - `FAILED`: Min-Conflicts gave up; this proves nothing
- All algorithms count **constraint checks** (colour comparisons) in the same way, so they can be compared fairly next to runtime.

### Experiments
- n = 5, 10, 20 (testing) → 30, 50, 75, 100 → 150, 200
- Several random maps per n; **all algorithms use the same maps**.
- Time limit for A1/A2, step limit for A3.
- Output: `results.csv`, plus plots of runtime and constraint checks vs n (separate for k = 3 and k = 4).

## 3. Code structure

Everything is in **one file**, `multi_city_lighting.py`, split into blocks. Each block has one owner.

| Block | Owner | Contents |
|---|---|---|
| 0. Shared | everyone | imports, colours, statuses, `MapColouringCSP`, `verify_solution`, `run_algorithm` |
| 1. Map & plots | Person 1 | map generation, validation, parity check, **A1**, plots |
| 2. Smart backtracking | Person 2 | **A2** (MRV, Degree, LCV, Forward Checking) |
| 3. Local search & experiments | Person 3 | **A3**, experiment runner, results summary |
| 4. Main | Person 1 | user input → map → colouring → plots |

Every algorithm has the same shape, so the blocks connect without extra work:

```python
def algorithm(csp, guard, rng) -> dict | None   # {city: colour} or None
```

You run any algorithm with `run_algorithm("A2", adjacency, colours)`. It returns the status, runtime and counters.

## 4. Team tasks

### Person 1 — Map, A1, Visualisation
**Aim:** produce correct maps and all pictures, and implement the simplest algorithm.
- Map generation + validation (already done)
- `check_3colour_parity()`: the odd-degree check for k = 3
- **A1** Naive Backtracking
- `plot_map()` (done) and `plot_comparison()` for the result graphs
- `main()`: tie everything together
- Report: map generation, theory for k = 3 / k = 4, A1

### Person 2 — CSP and A2
**Aim:** build the CSP base everyone uses, and the fastest complete algorithm.
- Lead the team review of Block 0 (names, statuses, counters) before coding starts
- **A2**: MRV + Degree tie-break, LCV, Forward Checking
- (Optional) ablation variants: A2 with some techniques switched off
- Report: CSP formulation, A2 explanation, A1 vs A2 comparison

### Person 3 — A3 and Experiments
**Aim:** implement local search and produce the comparison data for requirement (d).
- **A3** Min-Conflicts (step limit, optional restarts)
- `run_experiment()`: run all algorithms on the same maps, write `results.csv`
- Decide each map's final status (solvable / no solution / unknown)
- `summarise_results()`: tables per n and k
- Report: A3 explanation, experiment setup, results and conclusions

## 5. Working together
1. Agree on Block 0 first, then do not change it without asking everyone.
2. Only edit your own block. New imports go in Block 0.
3. Compare colours only through `csp.check()` and call `guard.check()` inside loops/recursion, so that counting and timeouts work the same for all algorithms.
4. Test with small n (5, 10, 20) before pushing. Every SAT result must pass `verify_solution()`.
5. Use your own Git branch, make small commits, and `git pull` often.

## 6. How to run

```bash
pip install numpy scipy matplotlib
python multi_city_lighting.py
# Enter the number of cities n: 20
```

Unfinished functions show `NOT_IMPLEMENTED` instead of crashing, so the program can be run at any stage.
