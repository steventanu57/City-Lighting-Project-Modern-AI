# Multi-City Lighting — Graph Colouring as a CSP

Modern AI Group Assignment · Topic: Constraint Satisfaction Problems

This document describes the project requirements, program, comparison methods, theory, final experiments and responsibilities. The final numerical results use the same four CSVs as the revised report: `results.csv`, `results_large.csv`, `results_a3_norestart.csv` and `results_ablation.csv`. The files contain 5,290 recorded runs. Earlier exploratory studies are not used as the final results below.

---

## 1. Requirements

### 1.1 Project brief

*n* cities are placed at random on a 2D map and connected with the maximum number of straight, non-crossing roads. Every city must then be lit so that no two cities joined by a road share a colour.

|   | **Requirement**                                                         | **Where it is addressed**                              |
| - | ----------------------------------------------------------------------- | ------------------------------------------------------ |
| a | Generate and plot a 2D map from a user input *n*                        | Block 1 (`make_map`, `plot_map`) and Block 4 (`main`)  |
| b | Colour all cities with 3 colours (Red, Green, Blue)                     | Every method, k = 3                                    |
| c | Colour all cities with 4 colours (Red, Green, Blue, Yellow)             | Every method, k = 4                                    |
| d | Use three distinct algorithms and compare their performance against *n* | M1, M2, M3 (Section 3) and the experiments (Section 5) |
| e | Plot the coloured map for a given *n* and *k*                           | Block 1 (`plot_map`) and Block 4 (`demo_single_map`)   |

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

- **Cities:** n seeded random points in [0, 1] × [0, 1].
- **Roads:** Delaunay edges form a maximal straight, non-crossing network for distinct, non-collinear positions with a valid triangulation. Roads may meet at a shared city.
- **Road count:** for a nondegenerate triangulation, |E| = 3n − 3 − h, where h is the number of hull vertices. This is the maximum for the fixed city positions.
- **Validation:** `validate_map()` checks adjacency, crossings, roads through cities, omitted triangulation vertices and the expected road count. Its fallback branch has limitations, so acceptance is not an unconditional certificate for arbitrary coordinates.
- **Special cases:** one city has no roads; two distinct cities have one; distinct collinear cities form a consecutive path.
- **Known limits in the benchmark source:** duplicate coordinates are not always rejected, and a non-collinear fallback path may pass validation without being maximal. These limits are documented in the report; a separate geometry patch was not substituted into the source used for the CSVs.

### 2.2 The CSP

| **Component** | **Definition**                               |
| ------------- | -------------------------------------------- |
| Variables     | the cities 0 … n−1                           |
| Domain        | {R, G, B} for k = 3, {R, G, B, Y} for k = 4  |
| Constraint    | for every road (i, j): colour(i) ≠ colour(j) |

### 2.3 Result statuses

| **Status** | **Meaning**                                                    |
| ---------- | -------------------------------------------------------------- |
| `SAT`      | a colouring was found and verified by `verify_solution()`      |
| `UNSAT`    | a complete method **proved** that no colouring exists          |
| `TIMEOUT`  | the cooperative time guard interrupted the method. **This proves nothing**            |
| `FAILED`   | Min-Conflicts used up its step budget. **This proves nothing** |

---

## 3. Methods

| **Name** | **Code name** | **Method**                                           | **Type**                                              | **Category**                   |
| -------- | ------------- | ---------------------------------------------------- | ----------------------------------------------------- | ------------------------------ |
| Baseline | `A1`          | Naive backtracking                                   | Complete, systematic search                           | Reference point                |
| **M1**   | `A2`          | Backtracking + MRV + Degree + LCV + Forward Checking | Complete, systematic search with heuristics           | Established method             |
| **M2**   | `A3`          | Min-Conflicts                                        | Incomplete, stochastic local search                   | Method from a research article |
| **M3**   | `M3`          | Structure-Aware Solver                               | Structural inference with a complete fallback, on the supported maps | Proposed method                |

The three methods represent different approaches: **systematic search** (M1), **local search** (M2), and **exploitation of the mathematical structure of the map** (M3).

### Baseline — Naive backtracking (A1)

Cities are coloured in order 0, 1, 2, …, with colours tried in a fixed order and a step back on every conflict. No heuristics are used. The baseline shows how much the ideas in M1 and M3 contribute.

### M1 — Backtracking with heuristics (A2)

- **MRV:** the city with the fewest remaining legal colours is coloured first. When forward checking is disabled in the `BT+MRV` ablation, legal colours are counted against already-coloured neighbours rather than from unpruned domains.
- **Degree:** ties are broken by choosing the city with the most uncoloured neighbours.
- **LCV:** the colour that removes the fewest options from neighbours is tried first.
- **Forward Checking:** after each assignment the colour is removed from the neighbours, and the search steps back as soon as a neighbour has no colours left.

Source: Haralick & Elliott (1980) for forward checking. DSatur (Brélaz, 1979) is a related graph-colouring heuristic; this implementation is described as MRV with an unassigned-degree tie-break, rather than claimed to be identical to DSatur.

### M2 — Min-Conflicts (A3)

The method starts from a random full colouring, selects a conflicted city and gives it a colour with the fewest conflicts, breaking ties randomly. It maintains the conflicted-city set and updates only the changed city and its neighbours. It **cannot prove UNSAT** and may fail on a solvable map. The final restarted experiment permits 1,000 repairs per attempt and nine additional attempts, for at most 10,000 repairs per whole run. Results and success rates are reported in Section 5 rather than assuming it is always fast.

Source: Minton et al. (1992).

### M3 — Structure-Aware Solver (proposed method)

M3 is designed for the generated triangulations, with separate handling for the supported path special cases. It applies a different technique for each k:

| **k** | **Technique**                                                                                                                                                                                      | **Result**                                                                                |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 3     | **Triangle propagation:** one triangle is coloured R, G, B. In each neighbouring triangle the third city has only one colour left, so the colours spread through the whole map.                    | SAT with a verified colouring, or UNSAT from a propagation conflict on supported inputs. The implementation does not establish a linear runtime bound |
| 4     | **Smallest-last ordering + Kempe chains:** cities are coloured in smallest-last order. When all four colours are taken by neighbours, the two colours along a Kempe chain are swapped to free one. | SAT. If Kempe chains ever fail, the baseline (A1) runs as a complete fallback             |

Details:

- M3 only reads the road graph, so it follows the same interface as the other methods.
- M3 has checks for some unsupported inputs, but it does not fully validate every arbitrary graph. Its guarantees are stated for the supported map family. Smallest-last removal scans remaining vertices, giving O(n²) ordering work; triangle enumeration and Kempe searches add work, and the complete fallback may be exponential.
- **Fallback indicator:** for k = 4, `assignment_attempts > 0` means the fallback was used. The Kempe colouring itself never changes this counter.

Origin of each part of M3:

| **Part of M3**                                                  | **Origin**                                                                                                                                                                               |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Smallest-last ordering                                          | Matula & Beck (1983)                                                                                                                                                                     |
| Kempe chain recolouring                                         | Kempe (1879). Heawood (1890) showed that the argument can fail, so success is not guaranteed in theory                                                                                   |
| 3-colourable triangulation ⇔ every inner vertex has even degree | Known result (Heawood) for full triangulations                                                                                                                                           |
| **New in this project**                                         | Combining known structural techniques and a complete fallback in one solver, then evaluating it on the generated maps. The three-colour theorem is an existing result, not a new theorem |

---

## 4. Theory

### 4.1 k = 4

The generated maps are planar, so a 4-colouring **always exists** (Four Colour Theorem). Every k = 4 instance is solvable. A method that does not find a colouring has timed out or failed.

### 4.2 k = 3

Some generated maps cannot be coloured with three colours. For a valid triangulated disc, feasibility is characterised by the parity of interior degrees (Popescu, 2021). A proven UNSAT result reflects the instance, rather than a failure to find an existing colouring. The final-sample frequencies below are empirical observations, not a claim about every possible map of a given size.

**Setting.** An *inner city* is a city that is not on the outer boundary of the map. For a valid non-collinear triangulation, the roads divide the area inside the boundary into triangles. The argument here assumes that geometry; the validator limitations in Section 2.1 must not be used to extend it to arbitrary inputs. Around an inner city these triangles fit together like slices of a pie, so its neighbours form a **closed ring**: going around the city, each neighbour is joined by a road to the next one, and the last neighbour is joined to the first. In graph terms, the city and its ring form a *wheel*. (Maps with fewer than 3 cities, or with all cities on one line, are simple paths. They have no inner cities, and 2 colours already suffice.)

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

**Feasibility in the final CSV sample.** A single odd-degree interior city proves that three colours are impossible in a valid triangulated disc. The CSVs do not store interior-degree averages, so no such average is inferred from them.

The table below counts each `(n, k, map_seed)` once across the four CSVs. Repeated algorithms, Min-Conflicts run seeds and overlapping studies are not extra maps. All sizes have ten distinct maps, with seeds `1000*n + trial` for trial = 0,...,9. The n=15 rows come from the ablation study, and n=150/200 from the larger-map study.

| n | Distinct maps | 3-colourable maps | Rate |
| --- | --- | --- | --- |
| 5 | 10 | 10/10 | 100% |
| 10 | 10 | 2/10 | 20% |
| 15 | 10 | 0/10 | 0% |
| 20 | 10 | 0/10 | 0% |
| 30 | 10 | 0/10 | 0% |
| 50 | 10 | 0/10 | 0% |
| 75 | 10 | 0/10 | 0% |
| 100 | 10 | 0/10 | 0% |
| 150 | 10 | 0/10 | 0% |
| 200 | 10 | 0/10 | 0% |

Every recorded four-colour instance is feasible. Zero three-colour successes at a listed size do not prove that all possible maps of that size are impossible. These frequencies describe the final ten-map samples; they replace the earlier exploratory sample in the submission results.

**Evidence and limits.** The four CSVs contain 5,290 rows over 500 distinct seeded maps and 1,000 distinct map/palette instances. Their recorded instance and parity labels are consistent across studies, with no missing or duplicate run keys. The source runner verifies colourings before writing SAT. The CSVs omit the assignments, so checking their labels and summaries does not independently verify every original colouring. Separately, the supplied correctness suite contains 18 test methods and passes on the recorded source.

**Consequence for requirement (b).** The program colours the map with 3 colours whenever this is possible, which in practice means mostly small *n*. Otherwise it reports UNSAT, and every UNSAT answer is backed by a proof: an inner city with an odd number of neighbours (Theorem 1), or a propagation conflict (Lemma). Removing roads to make 3 colours sufficient is not considered, because the map would no longer be maximally connected. Together with Section 4.1, this shows that 4 is the smallest number of colours that works for every generated map.

---

## 5. Experiments and final results

### 5.1 Recorded studies

| File | Scope | Rows |
| --- | --- | ---: |
| `results.csv` | n=5,10,20,30,50,75,100; k=3/4; A1, A2, A3, M3 | 1,120 |
| `results_large.csv` | n=150,200; k=3/4; A3 and M3 | 240 |
| `results_a3_norestart.csv` | n=50,75,100,150,200; k=4; A3 without restarts | 250 |
| `results_ablation.csv` | Every integer n=5..50; k=3/4; A1, A2, BT+MRV, BT+FC | 3,680 |
| **Total** | The four final studies | **5,290** |

Each study uses ten maps per n. Complete methods run once per map and palette, using run seed 0. A3 runs five times with run seeds 0..4, so its 50 runs per size/palette are ten maps with five repeated local-search runs, not 50 independent maps. All methods in a study see the same maps.

The final runs use a nominal 30-second cooperative guard per whole run. Main and larger-map A3 runs use `max_steps=1000, max_restarts=9`. The no-restart comparison uses `max_steps=10000, max_restarts=0`. Both policies permit at most 10,000 repairs; they need not have equal runtime because restarts require initialisation.

The experiments ran on Windows with Python 3.12, NumPy [confirm 2.5.4], SciPy [confirm 1.18.1] and Matplotlib [confirm 3.11.2].

### 5.2 Metrics and interpretation

- Runtime measures the solver call, including guard and random-generator setup, and stops before solution verification. Map generation, validation, plotting and CSV writing are excluded.
- Constraint checks count calls to `csp.check()`. Sorting, domain copies, triangle enumeration and other operations can affect runtime without increasing this counter.
- Cost means and population standard deviations use SAT/UNSAT rows only. FAILED and TIMEOUT counts remain visible. A `*` or hollow marker means some runs are omitted; `none` means no answered run, and `n/a` means that method was not run at that size.
- These are conditional means. They do not show average cost over all attempts and are not automatically lower bounds on eventual solution cost.
- A3 success is calculated only on SOLVABLE instances. A3 never proves UNSAT.
- For M3 at k=4, `assignment_attempts > 0` indicates use of the backtracking fallback.

The guard checks occur cooperatively, so 30 seconds is not a hard operating-system cutoff. Keep unanswered-run counts beside costs when interpreting the results.

### 5.3 Main and larger-map results

Mean constraint checks over answered runs:

| n | A1 k=3 | M1 k=3 | M2 k=3 | M3 k=3 | A1 k=4 | M1 k=4 | M2 k=4 | M3 k=4 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 15 | 73 | 121 | 13 | 15 | 126 | 55 | 14 |
| 10 | 627 | 406 | 1,162* | 31 | 70 | 289 | 405 | 43 |
| 20 | 16,952 | 871 | none | 39 | 4,777 | 598 | 3,482 | 142 |
| 30 | 402,948 | 1,043 | none | 45 | 2,439,818 | 906 | 8,723 | 217 |
| 50 | 17,290,710* | 1,079 | none | 58 | 13,843,482* | 2,204 | 37,202 | 766 |
| 75 | 29,325,483* | 1,349 | none | 47 | none | 2,396 | 65,215 | 2,347 |
| 100 | none | 1,580 | none | 30 | none | 5,052 | 138,539 | 3,071 |
| 150 | n/a | n/a | none | 43 | n/a | n/a | 202,764* | 8,737 |
| 200 | n/a | n/a | none | 51 | n/a | n/a | 462,171* | 12,699 |

M1 and M3 answered all 140 main-study instances. A1 answered 97 and timed out on 43; it answered none at n=100. At n=50,75,100, A1 timed out on 4/20, 19/20 and 20/20 runs respectively. M2 returned SAT on all 60 main-study runs on solvable k=3 instances and FAILED on all 290 runs on impossible k=3 instances. Its four-colour success was 100% through n=100.

At n=100, k=4, mean runtime was 0.00095 s for M3, 0.00612 s for M1 and 0.02668 s for M2. At n=200, M3 averaged 0.00351 s, while M2's successful runs averaged 0.09752 s. M3 used no backtracking fallback across the 90 four-colour main/larger-map runs. These findings apply to the tested family and are not a universal ranking.

### 5.4 Restart comparison

Four-colour success over 50 whole runs per n, with matching map/run seeds and the same maximum repair budget:

| n | Up to 10 × 1,000 repairs | 1 × 10,000 repairs |
| --- | --- | --- |
| 50 | 100% | 72% |
| 75 | 100% | 66% |
| 100 | 100% | 42% |
| 150 | 94% | 30% |
| 200 | 30% | 0% |

Restarts improved success on these samples, but M2 still failed on 35/50 runs at n=200. A cheaper conditional mean without restarts can reflect that harder unsuccessful runs were omitted, rather than a better overall method.

### 5.5 M1 ablation

The complete study covers every integer n from 5 through 50, both palettes. Selected k=3 mean checks are:

| n | A1 | A2 | BT+MRV | BT+FC |
| --- | --- | --- | --- | --- |
| 10 | 627 | 406 | 757 | 393 |
| 20 | 16,952 | 871 | 1,874 | 3,195 |
| 30 | 402,948 | 1,043 | 2,477 | 15,180 |
| 40 | 831,832 | 1,058 | 2,418 | 54,674 |
| 50 | 17,290,710* | 1,079 | 2,656 | 719,128 |

At n=50, k=4, A2 used 2,204 checks, BT+MRV 8,552 and BT+FC 358,731. Across all 3,680 rows, A1 timed out 19 times and BT+FC once (n=49, k=4, map seed 49007). A2 and BT+MRV each answered all 920 runs. BT+MRV retains MRV and Degree; BT+FC retains forward checking with fixed ordering. The ablation compares bundles and does not isolate every individual heuristic.

### 5.6 Numerical source and reproducibility

The final data are the four CSV files in the `final_results` folder of the report's supporting files. The accompanying report evidence package contains `analyse_results.py`, which recomputes all summaries, the deduplicated feasibility table and three performance plots. It contains `test_current_code.py` and `probe_current_code.py` for correctness checks and the documented validation/deadline diagnostics. These are supporting scripts; the application remains `multi_city_lighting.py`.

The source file's LF-normalised SHA-256 is `ed01f3eb5993378f43ebe47acaaec8a5c48c091c766b764cd67a92bf5358c3bc`. This is the solver from commit `398f10c03914a89ee3ed11c0c6092ed5955e150e`, identical at `73d83a0`, the checkout recorded for these runs. Timing varies between machines, so a rerun is not expected to reproduce every runtime or timeout outcome exactly.

---

## 6. Code structure

The whole program is in **one file**, `multi_city_lighting.py`, divided into blocks.

| **Block**                   | **Responsible** | **Contents**                                                                       |
| --------------------------- | --------------- | ---------------------------------------------------------------------------------- |
| 0. Shared                   | All members     | colours, statuses, `MapColouringCSP`, `verify_solution`, `run_algorithm`           |
| 1. Map, baseline, M3, plots | Person 1        | map generation and validation, parity check, A1, M3, `plot_map`, `plot_comparison` |
| 2. M1                       | Person 2        | MRV/Degree, LCV, Forward Checking, `backtracking_generic`                          |
| 3. M2 and experiments       | Person 3        | Min-Conflicts, `determine_instance_status`, `run_experiment`, `summarise_results`  |
| Registry                    | All members     | `ALGORITHMS`: name → (function, is_complete)                                       |
| 4. Main                     | Person 1        | demonstration for one n, experiment calls                                          |

**Interface.** Every method has the same signature, so the blocks connect directly:

```
def method(csp, guard, rng) -> dict | None     # {city: colour}, or None
```

- A method is run with `run_algorithm("A2", adjacency, colours)`, which returns the status, runtime and counters, and verifies every SAT result.
- For a complete method, `None` means UNSAT. For Min-Conflicts, `None` means FAILED.

**Conventions**

1. Each block is edited only by its responsible member. Imports are kept in Block 0.
2. Colour constraints are checked through `csp.check()`, and `guard.check()` is called inside loops and recursion. A2 retains the consistency check before forward checking; these checks count toward `constraint_checks` even when forward checking has already removed conflicting values.
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
  - note that A2's consistency checks remain counted even when forward checking is enabled

### Person 3 — M2 and experiments

- Code: `min_conflicts` (step limit, optional restarts), `determine_instance_status`, `run_experiment`, `summarise_results`. All methods in `COMPARED_ALGORITHMS` are run on the same maps.
- Literature: Minton et al. (1992).
- Report:
  - M2, and why it cannot prove UNSAT
  - experimental setup
  - results and their analysis (Section 5)

All members should be able to explain every method and result. These role descriptions do not replace the report outline’s required Lead/Supporter contribution matrix or the overall contribution percentages; the group must complete both using its actual agreed contributions.

---

## 8. References

1. Minton, S., Johnston, M. D., Philips, A. B., & Laird, P. (1992). Minimizing conflicts: a heuristic repair method for constraint satisfaction and scheduling problems. *Artificial Intelligence*, 58(1–3), 161–205. [https://doi.org/10.1016/0004-3702(92)90007-K](https://doi.org/10.1016/0004-3702\(92\)90007-K)
2. Haralick, R. M., & Elliott, G. L. (1980). Increasing tree search efficiency for constraint satisfaction problems. *Artificial Intelligence*, 14(3), 263–313. [https://doi.org/10.1016/0004-3702(80)90051-X](https://doi.org/10.1016/0004-3702\(80\)90051-X)
3. Brélaz, D. (1979). New methods to color the vertices of a graph. *Communications of the ACM*, 22(4), 251–256.
4. Matula, D. W., & Beck, L. L. (1983). Smallest-last ordering and clustering and graph coloring algorithms. *Journal of the ACM*, 30(3), 417–427.
5. Kempe, A. B. (1879). On the geographical problem of the four colours. *American Journal of Mathematics*, 2(3), 193–200.
6. Heawood, P. J. (1890). Map-colour theorem. *Quarterly Journal of Pure and Applied Mathematics*, 24, 332–338.
7. Russell, S., & Norvig, P. (2021). *Artificial intelligence: A modern approach* (4th ed.). Pearson.
8. Popescu, C. (2021). On vertex 3-colourable disc triangulations. *Bulletin Mathématique de la Société des Sciences Mathématiques de Roumanie*, 64(112)(2), 133–145. https://rms.unibuc.ro/bulletin/pdf/64-2/articol_2.pdf

---

## 9. How to run

From the project folder, with the intended Python environment active:

```powershell
python -m pip install numpy scipy matplotlib
python multi_city_lighting.py
# Enter the number of cities n: 20
```

The demonstration prints each method's result for k=3 and k=4 and saves the maps as PNG files. Set `SHOW_PLOTS = True` to open plot windows. A proven UNSAT result for k=3 is an expected outcome on many maps, rather than a missing implementation.

### 9.1 Quick check

Use a separate filename so a quick check cannot replace final results. This shortened run is not final performance evidence:

```powershell
python -c "import multi_city_lighting as m; rows=m.run_experiment([5,10,20],trials=3,algorithms=('A1','A2','A3','M3'),timeout_seconds=0.5,a3_runs=1,max_steps=1000,max_restarts=9,csv_path='quick_check.csv'); m.summarise_results(rows)"
```

### 9.2 Reproduce the four final studies

These commands intentionally write the corresponding final files. Keep the submitted CSVs if the aim is only to inspect them. Runtime depends on the machine and many A1 runs use the full limit.

Create the output folder once in PowerShell:

```powershell
New-Item -ItemType Directory -Force final_results
```

Main comparison — expected 1,120 rows:

```powershell
python -c "import multi_city_lighting as m; rows=m.run_experiment([5,10,20,30,50,75,100],trials=10,algorithms=('A1','A2','A3','M3'),timeout_seconds=30,a3_runs=5,max_steps=1000,max_restarts=9,csv_path='final_results/results.csv'); m.summarise_results(rows)"
```

Larger maps — expected 240 rows:

```powershell
python -c "import multi_city_lighting as m; rows=m.run_experiment([150,200],trials=10,algorithms=('A3','M3'),timeout_seconds=30,a3_runs=5,max_steps=1000,max_restarts=9,csv_path='final_results/results_large.csv'); m.summarise_results(rows)"
```

No restarts — expected 250 rows:

```powershell
python -c "import multi_city_lighting as m; rows=m.run_experiment([50,75,100,150,200],k_values=(4,),trials=10,algorithms=('A3',),timeout_seconds=30,a3_runs=5,max_steps=10000,max_restarts=0,csv_path='final_results/results_a3_norestart.csv'); m.summarise_results(rows)"
```

Ablation — every integer n=5..50, expected 3,680 rows:

```powershell
python -c "import multi_city_lighting as m; rows=m.run_experiment(list(range(5,51)),trials=10,algorithms=('A1','A2','BT+MRV','BT+FC'),timeout_seconds=30,csv_path='final_results/results_ablation.csv'); m.summarise_results(rows)"
```

### 9.3 Inspect existing results without rerunning experiments

```powershell
python -c "import csv,multi_city_lighting as m; rows=list(csv.DictReader(open('final_results/results.csv',newline=''))); m.summarise_results(rows)"
```

From the extracted report evidence package, rebuild its summaries and report plots:

```powershell
python analyse_results.py
```

This writes `analysis/summary.csv`, `analysis/feasibility_instances.csv`, `analysis/feasibility_by_n.csv`, `analysis/compare_time.png`, `analysis/compare_checks.png` and `analysis/ablation_checks.png`, with audit details in `analysis/analysis.json`. It reads existing CSVs and does not run the solvers. `plot_comparison` in the main program can also plot a supplied row list, but the report's full main/larger-map figures are the outputs of the accompanying analysis script.

The experiment runner saves its growing CSV after each completed map. A file can therefore exist even when a run was stopped early; use the expected row counts and seed/method coverage, not file existence alone, to establish completion.
