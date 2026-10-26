# Multi-City Lighting — Graph Colouring as a CSP

Modern AI Group Assignment · Topic: Constraint Satisfaction Problems

This document describes the project requirements, how the program works, the three methods that are compared, the theory behind them, and how the work is divided.

---

## 1. Requirements

### 1.1 Project brief
*n* cities are placed at random on a 2D map and connected with the maximum number of straight, non-crossing roads. Every city must then be lit so that no two cities joined by a road share a colour.

| | Requirement | Where it is addressed |
|---|---|---|
| a | Generate and plot a 2D map from a user input *n* | Block 1 (`make_map`, `plot_map`) and Block 4 (`main`) |
| b | Colour all cities with 3 colours (Red, Green, Blue) | Every method, k = 3 |
| c | Colour all cities with 4 colours (Red, Green, Blue, Yellow) | Every method, k = 4 |
| d | Use three distinct algorithms and compare their performance against *n* | M1, M2, M3 (Section 3) and the experiments (Section 5) |
| e | Plot the coloured map for a given *n* and *k* | Block 1 (`plot_map`) and Block 4 (`demo_single_map`) |

"Each city assigned a unique colour" in the brief is read as: each city receives **one** colour. It does not require all cities to have different colours.

### 1.2 Method requirements
- At least **three meaningfully different methods** are implemented and evaluated. Changing parameters alone does not count as a different method.
- At least **one research article with a DOI** that describes a method for this or a similar problem is used.
- The methods may include a method from an article, an established method, and a proposed method.
- The methods are compared systematically, and their behaviour, strengths, limitations and observed differences are explained with **theoretical and mathematical reasoning**.
- The aim is not only to identify the fastest method, but to explain what was done, why, what happened, and why it happened.

---

## 2. How the program works

### 2.1 The map
- **Cities:** *n* random points in [0, 1] × [0, 1]. A fixed seed makes every map reproducible.
- **Roads:** Delaunay triangulation. Roads are straight and never cross, and no further road can be added without crossing an existing one, so the map is *maximally* connected.
- **Road count:** |E| = 3n − 3 − h, where h is the number of cities on the outer boundary.
- **Validation:** every map is checked by `validate_map()`:
  - adjacency matches the roads
  - no two roads cross
  - no road passes through another city
  - no city is left out of the triangulation
  - the road count is exactly 3n − 3 − h
- **Special cases:** n = 1 has no roads, n = 2 has one road, and cities on one straight line are connected as a path.

### 2.2 The CSP
| Component | Definition |
|---|---|
| Variables | the cities 0 … n−1 |
| Domain | {R, G, B} for k = 3, {R, G, B, Y} for k = 4 |
| Constraint | for every road (i, j): colour(i) ≠ colour(j) |

### 2.3 Result statuses
| Status | Meaning |
|---|---|
| `SAT` | a colouring was found and verified by `verify_solution()` |
| `UNSAT` | a complete method **proved** that no colouring exists |
| `TIMEOUT` | the time limit was reached. **This proves nothing** |
| `FAILED` | Min-Conflicts used up its step budget. **This proves nothing** |

---

## 3. Methods

| Name | Code name | Method | Type | Category |
|---|---|---|---|---|
| Baseline | `A1` | Naive backtracking | Complete, systematic search | Reference point |
| **M1** | `A2` | Backtracking + MRV + Degree + LCV + Forward Checking | Complete, systematic search with heuristics | Established method |
| **M2** | `A3` | Min-Conflicts | Incomplete, stochastic local search | Method from a research article |
| **M3** | `M3` | Structure-Aware Solver | Complete, constructive, uses the structure of the map | Proposed method |

The three methods represent different approaches: **systematic search** (M1), **local search** (M2), and **exploitation of the mathematical structure of the map** (M3).

### Baseline — Naive backtracking (A1)
Cities are coloured in order 0, 1, 2, …, with colours tried in a fixed order and a step back on every conflict. No heuristics are used. The baseline shows how much the ideas in M1 and M3 contribute.

### M1 — Backtracking with heuristics (A2)
- **MRV:** the city with the fewest remaining colours is coloured first.
- **Degree:** ties are broken by choosing the city with the most uncoloured neighbours.
- **LCV:** the colour that removes the fewest options from neighbours is tried first.
- **Forward Checking:** after each assignment the colour is removed from the neighbours, and the search steps back as soon as a neighbour has no colours left.

Sources: Haralick & Elliott (1980) for forward checking, and Brélaz (1979) for the DSatur idea, which corresponds to MRV + Degree in graph colouring.

### M2 — Min-Conflicts (A3)
The method starts from a random full colouring. It then repeatedly selects a city in conflict and gives it the colour with the fewest conflicts. It is fast in practice, but it **cannot prove UNSAT** and may fail even when a solution exists.

Source: Minton et al. (1992).

### M3 — Structure-Aware Solver (proposed method)
M3 uses the fact that every generated map is a **planar triangulation**. It applies a different technique for each k:

| k | Technique | Result |
|---|---|---|
| 3 | **Triangle propagation:** one triangle is coloured R, G, B. In each neighbouring triangle the third city has only one colour left, so the colours spread through the whole map. | SAT with a colouring, or UNSAT with a proof. Linear in the number of triangles, no search |
| 4 | **Smallest-last ordering + Kempe chains:** cities are coloured in smallest-last order. When all four colours are taken by neighbours, the two colours along a Kempe chain are swapped to free one. | SAT. If Kempe chains ever fail, the baseline (A1) runs as a complete fallback |

Details:
- M3 only reads the road graph, so it follows the same interface as the other methods.
- If a map violates M3's assumptions, M3 raises an error instead of returning an unproven answer.
- **Fallback indicator:** for k = 4, `assignment_attempts > 0` means the fallback was used. The Kempe colouring itself never changes this counter.

Origin of each part of M3:

| Part of M3 | Origin |
|---|---|
| Smallest-last ordering | Matula & Beck (1983) |
| Kempe chain recolouring | Kempe (1879). Heawood (1890) showed that the argument can fail, so success is not guaranteed in theory |
| 3-colourable triangulation ⇔ every inner vertex has even degree | Known result (Heawood) for full triangulations |
| **New in this project** | Combining these techniques into a single solver; adapting the k = 3 theorem and its proof to maps whose outer face is not a triangle; the complete fallback; the experimental validation |

---

## 4. Theory

### 4.1 k = 4
The generated maps are planar, so a 4-colouring **always exists** (Four Colour Theorem). Every k = 4 instance is solvable. A method that does not find a colouring has timed out or failed.

### 4.2 k = 3
Most generated maps **cannot** be coloured with 3 colours. This is a mathematical property of maximally connected maps, not a limitation of the implementation: no algorithm can do better. This section proves it, shows how often it happens, and explains what it means for requirement (b).

**Setting.** An *inner city* is a city that is not on the outer boundary of the map. Every map with at least 3 cities that passes `validate_map()` is a triangulation: the roads divide the area inside the boundary into triangles. Around an inner city these triangles fit together like slices of a pie, so its neighbours form a **closed ring**: going around the city, each neighbour is joined by a road to the next one, and the last neighbour is joined to the first. In graph terms, the city and its ring form a *wheel*. (Maps with fewer than 3 cities, or with all cities on one line, are simple paths. They have no inner cities, and 2 colours already suffice.)

**Theorem 1 (odd ring ⇒ no 3-colouring).** If some inner city has an odd number of neighbours, the map cannot be coloured with 3 colours.

*Proof.* Suppose the map has a 3-colouring, and let *v* be an inner city with *d* neighbours. Rename the colours so that *v* is Red. Every neighbour is joined to *v* by a road, so every neighbour is Green or Blue. Neighbours that are next to each other on the ring are also joined by a road, so they have different colours: going around the ring, the colour switches between Green and Blue at every step. The ring is closed, so after *d* steps we are back at the first neighbour, which still has its original colour. Each step flips the colour, so this is only possible if *d* is even. Hence in a 3-colourable map every inner city has an even number of neighbours, and a map with an odd one has no 3-colouring. ∎

*Example.* An inner city with 5 neighbours is Red. Going around its ring, the first four neighbours must be Green, Blue, Green, Blue. The 5th neighbour is joined to the city (Red), to the 4th neighbour (Blue) and to the 1st neighbour (Green), so no colour is left for it.

Theorem 1 does not depend on any algorithm, and applying it only requires counting neighbours. `check_3colour_parity()` does exactly this.

**Theorem 2 (converse).** If every inner city has an even number of neighbours, the map can be coloured with 3 colours.

*Proof sketch.* Colour one triangle R, G, B and spread the colours through neighbouring triangles, as M3 does: in each new triangle the third city has only one colour left. A conflict could only arise if two different chains of triangles forced different colours on the same city. Walking once around an inner city through its triangles, the city keeps its colour and its ring alternates between the other two colours, so the walk ends consistently exactly when the number of neighbours is even (the argument of Theorem 1). The triangles fill one region without holes, so every closed chain of triangles can be split into walks around single inner cities. If each of these walks is consistent, every chain gives the same colours, and propagation never reaches a conflict. ∎

Theorem 2 is not needed to trust the program's answers: every SAT colouring is checked by `verify_solution()`, and every UNSAT answer is backed by Theorem 1 or by the lemma below.

**Lemma (conflict ⇒ UNSAT).** If triangle propagation reaches a conflict, no 3-colouring exists.

*Proof sketch.* In any 3-colouring every triangle uses all three colours, because its cities are pairwise connected. Renaming colours keeps a colouring valid, so any 3-colouring can be renamed to match the colours of the first triangle. From then on every colour assigned by propagation is forced, so propagation would reproduce that colouring exactly and never reach a conflict. ∎

The lemma only requires that every triangle consists of three pairwise-connected cities, which holds for every map that passes validation.

**Why almost every larger map is impossible.** A map can be 3-coloured only if **every** inner city has an even number of neighbours, and a single inner city with an odd number is enough to rule it out (Theorem 1). In the generated maps about half of the inner cities have an odd number of neighbours, and the number of inner cities grows with *n*. Measured on 200 maps per *n* (seeds 0–199):

| *n* | Inner cities (average) | Inner cities with an odd number of neighbours (average) | 3-colourable maps |
|---|---|---|---|
| 5 | 0.8 | 0.3 | 146 / 200 (73%) |
| 10 | 3.9 | 1.9 | 20 / 200 (10%) |
| 15 | 7.9 | 3.9 | 0 / 200 |
| 20 | 12.2 | 6.2 | 0 / 200 |
| 30 | 21.2 | 10.8 | 0 / 200 |
| 50 | 39.9 | 20.3 | 0 / 200 |
| 100 | 88.0 | 43.8 | 0 / 200 |

From *n* = 15 on, a typical map has about 4 or more inner cities with an odd number of neighbours, and each of them rules out a 3-colouring on its own. A result of 0 / 200 does not mean that 3-colourable maps cannot exist for these *n*, only that they are very rare.

**Empirical check.** The theory and the program agree on every map tested:
- On 3,900 random maps (n = 3–15), the parity check (`check_3colour_parity`), complete search (A1) and M3 agreed in **every** case: 1,147 SAT and 2,753 UNSAT.
- On the 1,400 maps in the table above, the parity check and M3 agreed in **every** case, and A1 also agreed on all 800 maps with n ≤ 20.

**Consequence for requirement (b).** The program colours the map with 3 colours whenever this is possible, which in practice means mostly small *n*. Otherwise it reports UNSAT, and every UNSAT answer is backed by a proof: an inner city with an odd number of neighbours (Theorem 1), or a propagation conflict (Lemma). Removing roads to make 3 colours sufficient is not considered, because the map would no longer be maximally connected. Together with Section 4.1, this shows that 4 is the smallest number of colours that works for every generated map.

---

## 5. Experiments

- **Values of n:** 5, 10, 20 (functional tests), then 30, 50, 75, 100, then 150, 200. Larger values can be used for M3.
- **Maps:** several random maps per n with fixed seeds. **All methods are run on the same maps.**
- **Limits:** a time limit for the complete methods and a step limit for Min-Conflicts. Min-Conflicts is run several times per map with different seeds.
- **Metrics:**
  - runtime
  - **constraint checks**, counted in the same way for every method through `csp.check()`
  - status proportions
  - Min-Conflicts success rate, measured on solvable instances only
  - M3 fallback rate
- **Methods compared:** `COMPARED_ALGORITHMS = ("A1", "A2", "A3", "M3")`, defined in Block 4.
- **Outputs:** `results.csv`, `compare_time.png`, `compare_checks.png`, and coloured maps `map_n{n}_k{k}_{method}.png`.
- **Timeout rule in plots:** timed-out runs are excluded from the mean. A hollow point means that some runs timed out, so the mean is a lower bound.

Example (n = 20, k = 3): the baseline needed **22,911** constraint checks to prove UNSAT, while M3 needed **38**.

---

## 6. Code structure

The whole program is in **one file**, `multi_city_lighting.py`, divided into blocks.

| Block | Responsible | Contents |
|---|---|---|
| 0. Shared | All members | colours, statuses, `MapColouringCSP`, `verify_solution`, `run_algorithm` |
| 1. Map, baseline, M3, plots | Person 1 | map generation and validation, parity check, A1, M3, `plot_map`, `plot_comparison` |
| 2. M1 | Person 2 | MRV/Degree, LCV, Forward Checking, `backtracking_generic` |
| 3. M2 and experiments | Person 3 | Min-Conflicts, `determine_instance_status`, `run_experiment`, `summarise_results` |
| Registry | All members | `ALGORITHMS`: name → (function, is_complete) |
| 4. Main | Person 1 | demonstration for one n, experiment calls |

**Interface.** Every method has the same signature, so the blocks connect directly:
```python
def method(csp, guard, rng) -> dict | None     # {city: colour}, or None
```
- A method is run with `run_algorithm("A2", adjacency, colours)`, which returns the status, runtime and counters, and verifies every SAT result.
- For a complete method, `None` means UNSAT. For Min-Conflicts, `None` means FAILED.

**Conventions**
1. Each block is edited only by its responsible member. Imports are kept in Block 0.
2. Colours are compared only through `csp.check()`, and `guard.check()` is called inside loops and recursion, so constraint checks and time limits are measured identically for all methods.
3. Changes are tested with small n (5, 10, 20) before they are merged.

---

## 7. Responsibilities

### Person 1 — Map, baseline, M3, visualisation
- Code: map generation and validation, parity check, A1, M3, `plot_map`, `plot_comparison`, `main`.
- Report:
  - map generation
  - theory for k = 3 and k = 4 (Section 4)
  - A1 as the baseline
  - M3: design, sources, the parts that are new, and results

### Person 2 — M1
- Code: `select_unassigned_variable` (MRV + Degree), `order_domain_values` (LCV), `forward_check`, `backtracking_generic`. Optional ablation variants (`BT+MRV`, `BT+FC`) show which technique contributes most.
- Literature: Haralick & Elliott (1980), Brélaz (1979).
- Report:
  - CSP formulation
  - M1
  - baseline versus M1, and the ablation results

### Person 3 — M2 and experiments
- Code: `min_conflicts` (step limit, optional restarts), `determine_instance_status`, `run_experiment`, `summarise_results`. All methods in `COMPARED_ALGORITHMS` are run on the same maps.
- Literature: Minton et al. (1992).
- Report:
  - M2, and why it cannot prove UNSAT
  - experimental setup
  - results and their analysis (Section 5)

All members should be able to explain every method and result.

---

## 8. References

1. Minton, S., Johnston, M. D., Philips, A. B., & Laird, P. (1992). Minimizing conflicts: a heuristic repair method for constraint satisfaction and scheduling problems. *Artificial Intelligence*, 58(1–3), 161–205. https://doi.org/10.1016/0004-3702(92)90007-K
2. Haralick, R. M., & Elliott, G. L. (1980). Increasing tree search efficiency for constraint satisfaction problems. *Artificial Intelligence*, 14(3), 263–313. https://doi.org/10.1016/0004-3702(80)90051-X
3. Brélaz, D. (1979). New methods to color the vertices of a graph. *Communications of the ACM*, 22(4), 251–256.
4. Matula, D. W., & Beck, L. L. (1983). Smallest-last ordering and clustering and graph coloring algorithms. *Journal of the ACM*, 30(3), 417–427.
5. Kempe, A. B. (1879). On the geographical problem of the four colours. *American Journal of Mathematics*, 2(3), 193–200.
6. Heawood, P. J. (1890). Map-colour theorem. *Quarterly Journal of Pure and Applied Mathematics*, 24, 332–338.
7. Russell, S., & Norvig, P. *Artificial Intelligence: A Modern Approach*, chapter on Constraint Satisfaction Problems.

---

## 9. How to run

```bash
pip install numpy scipy matplotlib
python multi_city_lighting.py
# Enter the number of cities n: 20
```

- The program prints the result of every method for k = 3 and k = 4, and saves the maps as PNG files.
- Methods that are not yet implemented show `NOT_IMPLEMENTED` instead of stopping the program.
- Set `SHOW_PLOTS = True` in Block 0 to open plot windows instead of only saving PNG files.
