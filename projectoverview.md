# Multi-City Lighting: Graph Colouring as a CSP

CSCI323 Modern AI, Group 17. Topic: Constraint Satisfaction Problems

This document explains what the project asks for, how the program works, the methods and the theory behind them, the final experiments, and who did what. All final numbers come from the four CSV files in [`final_results/`](final_results/) (5,290 runs), the same files the report uses. M3+, which we added after the presentation, has its own file there (Section 5.8).

---

## 1. Requirements

### 1.1 Project brief

*n* cities are placed at random on a 2D map and connected with the maximum number of straight, non-crossing roads. Every city must then be lit so that no two cities joined by a road share a colour.

|   | **Requirement**                                                         | **Where it is done**                                   |
| - | ----------------------------------------------------------------------- | ------------------------------------------------------ |
| a | Generate and plot a 2D map from a user input *n*                        | Block 1 (`make_map`, `plot_map`) and Block 4 (`main`)  |
| b | Colour all cities with 3 colours (Red, Green, Blue)                     | Every method, k = 3                                    |
| c | Colour all cities with 4 colours (Red, Green, Blue, Yellow)             | Every method, k = 4                                    |
| d | Use three distinct algorithms and compare their performance against *n* | M1, M2, M3 (Section 3) and the experiments (Section 5) |
| e | Plot the coloured map for a given *n* and *k*                           | Block 1 (`plot_map`) and Block 4 (`demo_single_map`)   |

"Each city assigned a unique colour" in the brief is read as: each city gets **one** colour. It does not mean all cities need different colours.

### 1.2 Method requirements

- At least **three meaningfully different methods**. Changing parameters alone does not count as a new method.
- At least **one research article with a DOI** that describes a method for this or a similar problem. Ours is Minton et al. (1992), the source of M2.
- The methods are compared systematically, and their differences are explained with **theoretical and mathematical reasoning**, not just by saying which one was fastest.

---

## 2. How the program works

### 2.1 The map

- **Cities:** n seeded random points in [0, 1] × [0, 1].
- **Roads:** the edges of a Delaunay triangulation. For cities with distinct positions that are not all on one line, this gives the maximum number of straight, non-crossing roads. Roads may meet at a shared city.
- **Road count:** for a triangulation, |E| = 3n − 3 − h, where h is the number of cities on the outer boundary (the convex hull). This is the maximum for those city positions.
- **Validation:** `validate_map()` checks adjacency, crossings, roads that pass through a city, cities left out of the triangulation, and the expected road count.
- **Special cases:** one city has no roads; two cities have one road; cities that all lie on one line are joined into a path.
- **Known limits:** duplicate coordinates are not always rejected, and the fallback for nearly collinear cities can pass validation without being maximal. Neither case comes up in the experiments: all 500 seeded maps are proper triangulations.

### 2.2 The CSP

| **Component** | **Definition**                               |
| ------------- | -------------------------------------------- |
| Variables     | the cities 0 … n−1                           |
| Domain        | {R, G, B} for k = 3, {R, G, B, Y} for k = 4  |
| Constraint    | for every road (i, j): colour(i) ≠ colour(j) |

### 2.3 Result statuses

| **Status** | **Meaning**                                                           |
| ---------- | --------------------------------------------------------------------- |
| `SAT`      | a colouring was found and checked by `verify_solution()`              |
| `UNSAT`    | a complete method **proved** that no colouring exists                 |
| `TIMEOUT`  | the run hit its time limit. This says nothing about the map           |
| `FAILED`   | Min-Conflicts used up its repair budget. This says nothing about the map |

---

## 3. Methods

| **Name** | **Code name** | **Method**                                           | **Type**                                     | **Category**                   |
| -------- | ------------- | ---------------------------------------------------- | -------------------------------------------- | ------------------------------ |
| Baseline | `A1`          | Naive backtracking                                   | Complete, systematic search                  | Reference point                |
| **M1**   | `A2`          | Backtracking + MRV + Degree + LCV + Forward Checking | Complete, systematic search with heuristics  | Established method             |
| **M2**   | `A3`          | Min-Conflicts                                        | Incomplete, stochastic local search          | Method from a research article |
| **M3**   | `M3`          | Structure-Aware Solver                               | Uses the map's structure, with a complete fallback | Proposed method          |

The three methods take different approaches: **systematic search** (M1), **local search** (M2), and **using the mathematical structure of the map** (M3).

### Baseline: naive backtracking (A1)

Cities are coloured in order 0, 1, 2, …, trying the colours in a fixed order and going back one step on every conflict. No heuristics. The baseline shows how much the ideas in M1 and M3 add.

### M1: backtracking with heuristics (A2)

- **MRV:** colour the city with the fewest legal colours left first. In the `BT+MRV` ablation, forward checking is off, so the legal colours are counted against the coloured neighbours instead.
- **Degree:** break ties by choosing the city with the most uncoloured neighbours.
- **LCV:** try first the colour that removes the fewest options from the neighbours.
- **Forward checking:** after each assignment, remove that colour from the neighbours, and go back as soon as a neighbour has no colours left.

Sources: Haralick & Elliott (1980) for forward checking, and Russell & Norvig (2021) for MRV, Degree and LCV.

### M2: Min-Conflicts (A3)

M2 starts from a random complete colouring. At each step it picks a conflicted city at random and gives it the colour with the fewest conflicts, breaking ties at random. After each repair only the changed city and its neighbours are rechecked. It **cannot prove UNSAT** and can fail on a solvable map. The final runs allow 1,000 repairs per attempt and up to nine restarts, so at most 10,000 repairs per run. The demo uses one attempt of 10,000 repairs instead.

Source: Minton et al. (1992).

### M3: Structure-Aware Solver (proposed method)

M3 is built for the generated maps (triangulations, plus the path special cases) and uses a different technique for each k:

| **k** | **Technique**                                                                                                                                                                       | **Result**                                                                                     |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| 3     | **Triangle propagation:** colour one triangle R, G, B. In each neighbouring triangle the third city has only one colour left, so the colours spread through the whole map.          | SAT with a verified colouring, or UNSAT when propagation hits a conflict                       |
| 4     | **Smallest-last ordering + Kempe chains:** colour the cities in smallest-last order. When the neighbours already use all four colours, swap two colours along a Kempe chain to free one. | SAT. If no swap frees a colour, A1 colours the map from scratch as a complete fallback   |

Details:

- M3 only reads the road graph, so it has the same interface as the other methods.
- On graphs that are not triangulations or paths it may stop with an error instead of answering.
- Costs that are not counted as constraint checks: smallest-last ordering scans the remaining cities at every step (O(n²)), and finding triangles and following Kempe chains add work. The fallback can take exponential time.
- **Fallback indicator:** for k = 4, `assignment_attempts > 0` means the fallback was used. Kempe colouring itself never changes this counter.

Where each part of M3 comes from:

| **Part of M3**                                                       | **Source**                                                                                                         |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Smallest-last ordering                                               | Matula & Beck (1983)                                                                                               |
| Kempe chain recolouring                                              | Kempe (1879). One swap does not always free a colour, which is why M3 keeps a fallback                             |
| A triangulated disc is 3-colourable ⇔ every inner city has even degree | Popescu (2021)                                                                                                   |
| **New in this project**                                              | Putting these known techniques together with a complete fallback in one solver, and testing it on the generated maps. The parity result itself is not new |

### M3+: improved M3 (added after the presentation)

At the presentation our tutor asked if M3 could be made better, so we measured where M3 actually spends its effort. With 4 colours, the Kempe swaps were 65% to 91% of its checks (n = 50 to 200), and working out the smallest-last order was about 40% of its time. With 3 colours, most of the time went into listing every triangle at the start, even though most maps hit a conflict within about 60 checks. The A1 fallback never ran, so adding more backtracking wouldn't have changed anything.

M3+ uses the same ideas as M3 but cuts out work that wasn't needed:

- Kempe swaps. Swapping colours a and b on a chain only frees a if all of the city's a-coloured neighbours are in the chain and none of its b-coloured ones are. So M3+ builds one chain per colour pair, stops as soon as the chain reaches a b-coloured neighbour, and only swaps when it will work. M3 swapped first, checked, and swapped back if it failed. M3+ tries the pairs in the same order, so it ends up with the same colouring as M3, just with fewer checks.
- Smallest-last order. Same order, but it uses a heap to find the next city instead of scanning all the remaining ones each time (O(m log n) instead of O(n²)).
- Triangle propagation (k = 3). Triangles are only found when propagation gets to them. The visiting order doesn't change the answer (the lemma in Section 4.2), but the check count can go up or down a little.
- Fallback. M1 instead of A1. It never ran in our tests either, but if it ever did, M1 can handle big maps where A1 times out. When we forced it at n = 200 it took 0.05 s.

We didn't change M3 itself, so all the other results in this document are still about M3.

---

## 4. Theory

### 4.1 k = 4

The generated maps are planar, so a 4-colouring **always exists** (Four Colour Theorem; Thomas, n.d.). Every k = 4 instance is solvable, so a method that does not find a colouring has timed out or failed.

### 4.2 k = 3

Some generated maps cannot be coloured with three colours. For a triangulated disc, three colours work exactly when every inner city has an even number of neighbours (Popescu, 2021). The proofs below show why. So a proven UNSAT says something about the map, not about a weak solver.

**Setting.** An *inner city* is a city that is not on the outer boundary of the map. In a triangulation, the roads split the area inside the boundary into triangles. Around an inner city these triangles fit together like slices of a pie, so its neighbours form a **closed ring**: going around the city, each neighbour is joined by a road to the next one, and the last neighbour is joined to the first. In graph terms, the city and its ring form a *wheel*. (Maps with fewer than 3 cities, or with all cities on one line, are simple paths. They have no inner cities, and 2 colours are enough.)

**Theorem 1 (odd ring ⇒ no 3-colouring).** If some inner city has an odd number of neighbours, the map cannot be coloured with 3 colours.

*Proof.* Suppose the map has a 3-colouring, and let *v* be an inner city with *d* neighbours. Rename the colours so that *v* is Red. Every neighbour is joined to *v* by a road, so every neighbour is Green or Blue. Neighbours that are next to each other on the ring are also joined by a road, so they have different colours: going around the ring, the colour switches between Green and Blue at every step. The ring is closed, so after *d* steps we are back at the first neighbour, which still has its original colour. Each step flips the colour, so this is only possible if *d* is even. Hence in a 3-colourable map every inner city has an even number of neighbours, and a map with an odd one has no 3-colouring. ∎

*Example.* An inner city with 5 neighbours is Red. Going around its ring, the first four neighbours must be Green, Blue, Green, Blue. The 5th neighbour is joined to the city (Red), to the 4th neighbour (Blue) and to the 1st neighbour (Green), so no colour is left for it.

Theorem 1 does not depend on any algorithm, and applying it only takes counting neighbours. `check_3colour_parity()` does exactly this.

**Theorem 2 (converse).** If every inner city has an even number of neighbours, the map can be coloured with 3 colours.

*Proof sketch.* Colour one triangle R, G, B and spread the colours through neighbouring triangles, as M3 does: in each new triangle the third city has only one colour left. A conflict could only happen if two different chains of triangles forced different colours on the same city. Walking once around an inner city through its triangles, the city keeps its colour and its ring alternates between the other two colours, so the walk ends consistently exactly when the number of neighbours is even (the argument of Theorem 1). The triangles fill one region without holes, so every closed chain of triangles can be split into walks around single inner cities. If each of these walks is consistent, every chain gives the same colours, and propagation never reaches a conflict. ∎

Theorem 2 is not needed to trust the program's answers: every SAT colouring is checked by `verify_solution()`, and every UNSAT answer is backed by Theorem 1 or by the lemma below.

**Lemma (conflict ⇒ UNSAT).** If triangle propagation reaches a conflict, no 3-colouring exists.

*Proof sketch.* In any 3-colouring every triangle uses all three colours, because its cities are all joined to each other. Renaming colours keeps a colouring valid, so any 3-colouring can be renamed to match the colours of the first triangle. From then on every colour that propagation assigns is forced, so propagation would rebuild that colouring exactly and never reach a conflict. ∎

The lemma only needs every triangle to be three cities that are all joined to each other, which holds on every map that passes validation.

**How many sampled maps are 3-colourable.** Each `(n, map_seed)` is counted once across the four CSVs, so repeated methods and repeated M2 runs are not extra maps. Every size has ten maps, with seeds `1000*n + trial` for trial = 0 to 9. The n = 15 maps come from the ablation study, and n = 150 and 200 from the larger-map study.

| n | Maps | 3-colourable maps | Rate |
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

Every map could be coloured with four colours. These are ten-map samples, so they show what happened on our maps, not a rule for every map of that size.

**What the data covers.** The four CSVs hold 5,290 runs over 500 distinct maps (1,000 map and palette pairs). No run is missing or duplicated, and where two studies use the same map they give it the same labels. Every SAT result was verified before it was written, but the CSVs do not store the colourings themselves.

**What this means for requirement (b).** The program colours the map with 3 colours whenever that is possible, which in practice means mostly small *n*. Otherwise it reports UNSAT, and every UNSAT answer is backed by a proof: an inner city with an odd number of neighbours (Theorem 1), or a propagation conflict (Lemma). Removing roads to make 3 colours enough is not an option, because the map would no longer be maximally connected. Together with Section 4.1, this shows that 4 is the smallest number of colours that works for every generated map.

---

## 5. Experiments and final results

### 5.1 Recorded studies

| File | Scope | Rows |
| --- | --- | ---: |
| `results.csv` | n = 5, 10, 20, 30, 50, 75, 100; k = 3 and 4; A1, A2, A3, M3 | 1,120 |
| `results_large.csv` | n = 150, 200; k = 3 and 4; A3 and M3 | 240 |
| `results_a3_norestart.csv` | n = 50, 75, 100, 150, 200; k = 4; A3 without restarts | 250 |
| `results_ablation.csv` | every integer n from 5 to 50; k = 3 and 4; A1, A2, BT+MRV, BT+FC | 3,680 |
| **Total** | | **5,290** |

There is also a fifth file, `results_m3plus.csv` (360 rows), that compares M3 with M3+. See Section 5.8.

Each study uses ten maps per n, and every method in a study sees the same maps. Complete methods run once per map and palette, with run seed 0. A3 runs five times with run seeds 0 to 4, so its 50 runs per size and palette are ten maps times five runs, not 50 different maps.

Every run has a 30-second time limit. The limit is checked inside the loops, so it is not a hard cutoff. Main and larger-map A3 runs use `max_steps=1000, max_restarts=9`; the no-restart study uses `max_steps=10000, max_restarts=0`. Both allow at most 10,000 repairs per run, but restarts take extra time to set up a new random colouring.

The experiments ran on Windows with Python 3.12. We reproduced them with Python 3.12.10, NumPy 2.2.6, SciPy 1.18.1 and Matplotlib 3.10.3, which gave the same constraint-check counts on every run that finished on both machines.

### 5.2 Metrics

- **Runtime** covers the solver call only, including creating the time guard and the random number generator. Map generation, validation, the final check of the colouring, plotting and CSV writing are not included.
- **Constraint checks** count calls to `csp.check()`. Other work, such as scanning cities for MRV, copying domains, finding triangles or following Kempe chains, takes time but adds no checks.
- **Means and standard deviations** (population) only use SAT and UNSAT runs. FAILED and TIMEOUT runs are counted separately. A `*` or a hollow marker means some runs were left out, so the mean only covers the runs that answered. `none` means no run answered, and `n/a` means the method was not run at that size.
- **A3 success rate** only counts SOLVABLE maps. A3 never proves UNSAT.
- **M3 fallback:** for k = 4, `assignment_attempts > 0` means the fallback was used.

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

M1 and M3 answered all 140 main-study instances. A1 answered 97 and timed out on 43, including every run at n = 100; at n = 50, 75 and 100 it timed out on 4/20, 19/20 and 20/20 runs. M2 found a colouring on all 60 runs on solvable three-colour maps, failed on all 290 runs on impossible ones, and solved every four-colour run up to n = 100.

At n = 100 with k = 4, mean runtime was 0.00095 s for M3, 0.00612 s for M1 and 0.02668 s for M2. At n = 200, M3 averaged 0.00351 s, and M2's successful runs averaged 0.09752 s. M3 never needed its fallback in the 90 four-colour main and larger-map runs.

### 5.4 Restart comparison

Four-colour success over 50 runs per n, on the same maps and run seeds and with the same maximum of 10,000 repairs:

| n | Up to 10 × 1,000 repairs | 1 × 10,000 repairs |
| --- | --- | --- |
| 50 | 100% | 72% |
| 75 | 100% | 66% |
| 100 | 100% | 42% |
| 150 | 94% | 30% |
| 200 | 30% | 0% |

Restarts helped at every size, but M2 still failed on 35 of 50 runs at n = 200. Without restarts the mean cost of the successful runs can look lower only because the hard runs failed and were left out.

### 5.5 M1 ablation

The ablation covers every integer n from 5 to 50, with both palettes. Selected k = 3 mean checks:

| n | A1 | A2 | BT+MRV | BT+FC |
| --- | --- | --- | --- | --- |
| 10 | 627 | 406 | 757 | 393 |
| 20 | 16,952 | 871 | 1,874 | 3,195 |
| 30 | 402,948 | 1,043 | 2,477 | 15,180 |
| 40 | 831,832 | 1,058 | 2,418 | 54,674 |
| 50 | 17,290,710* | 1,079 | 2,656 | 719,128 |

At n = 50 with k = 4, A2 used 2,204 checks, BT+MRV 8,552 and BT+FC 358,731. Across all 3,680 rows, A1 timed out 19 times and BT+FC once (n = 49, k = 4, map seed 49007). A2 and BT+MRV answered all 920 of their runs. BT+MRV keeps MRV and Degree; BT+FC keeps forward checking with a fixed order. Each variant removes several parts at once, so the ablation does not show the effect of every single heuristic on its own.

### 5.6 Data and source code

The four final CSVs are in [`final_results/`](final_results/); its README explains every column. They are our own runs, made with the solver in `multi_city_lighting.py` at commit `398f10c03914a89ee3ed11c0c6092ed5955e150e` (the file is the same at `73d83a0`, the checkout used for the runs). At that commit the file's SHA-256 is `ed01f3eb5993378f43ebe47acaaec8a5c48c091c766b764cd67a92bf5358c3bc` with LF line endings. Later commits rewrote comments and docstrings and added M3+ (Section 5.8). Every method used for the four final CSVs runs exactly the same code as before, so the current file has a different hash but gives the same results. Timing depends on the machine, so a rerun will not match every runtime or timeout (see Section 9.4).

### 5.7 Same-map comparison

The averages above do not show how often one method beats another on the same map. The table counts the maps where the first method used fewer checks, and the maps where it used less time. It covers the main and larger-map studies and only counts maps where both methods answered, so A1's timeouts are left out. M2 is averaged over its runs on each map.

| Comparison | k | Maps | Fewer checks | Less time |
| --- | --- | ---: | ---: | ---: |
| M3 vs M1 | 3 | 70 | 70 | 70 |
| M3 vs M1 | 4 | 70 | 59 | 70 |
| M3 vs M2 | 4 | 88 | 88 | 87 |
| M3 vs A1 | 3 | 50 | 48 (1 tie) | 48 |
| M3 vs A1 | 4 | 47 | 43 | 29 |
| M1 vs M2 | 4 | 70 | 59 | 56 |
| M1 vs A1 | 3 | 50 | 36 | 39 |
| M1 vs A1 | 4 | 47 | 24 | 23 |

Where the result changes with n:

- **M1 vs A1:** A1 wins on small maps. With 4 colours, M1 used fewer checks on 0/10 maps at n = 5 and n = 10, 7/10 at n = 20, and every answered map from n = 30. With 3 colours it was 0/10 at n = 5, 6/10 at n = 10, and every map from n = 20.
- **M3 vs M1 with 4 colours:** M3 used fewer checks on every map up to n = 30, but only on 8/10 at n = 50, 6/10 at n = 75 and 5/10 at n = 100. It was still faster on all 70 maps. So M3 uses the fewest checks **on average**, not on every map.
- **M3 vs A1 with 4 colours:** at n = 5, M3 used fewer checks on 8/10 maps but was slower on all 10. At n = 10 it was slower on 7/10.
- **M1 vs M2 with 4 colours:** M2 won all 10 maps at n = 5. From n = 20, M1 won every map on checks and all but one on time.

Time per check (mean runtime divided by mean checks, in microseconds) explains most of this:

| Method | k = 4, n = 10 | k = 4, n = 50 | k = 4, n = 100 | k = 3, n = 100 |
| --- | ---: | ---: | ---: | ---: |
| A1 | 0.60 | 0.38 | none | none |
| M1 | 0.34 | 0.74 | 1.21 | 1.95 |
| M2 | 0.25 | 0.19 | 0.19 | none |
| M3 | 0.99 | 0.48 | 0.31 | 7.81 |

- **M1** scans every unassigned city at each step to apply MRV and Degree, and that scan is not counted as checks. Its time per check grows with n, which is why M3 is faster even on maps where it uses more checks. At n = 100 with 4 colours, M3 used 1.6 times fewer checks but was 6.4 times faster.
- **M3 at k = 3** makes only 13 to 58 checks on average, but it first finds every triangle, which is not counted. So it has the highest time per check of any method and still the lowest total time.
- **M2** makes the cheapest checks, about 0.2 microseconds each, but needs far more of them: 138,539 at n = 100 with 4 colours, against 5,052 for M1. Repairs often undo each other, and bigger maps need more attempts (on successful runs, 1.34 attempts on average at n = 50, 2.40 at n = 100 and 6.53 at n = 200).
- **A1** has no ordering cost, so it wins on tiny maps. On bigger maps it only finds out that an early choice was wrong after trying everything below it: at n = 50 with 3 colours it averaged about 3.3 million backtracks on the maps it answered, against 44 for M1. Its cost also depends heavily on the map. With 4 colours at n = 30 it used between 1,451 and 19,684,760 checks.

The check counts are the same on any machine; the times are from one machine.

### 5.8 M3+ against M3

`final_results/results_m3plus.csv` has M3 and M3+ on the same 90 study maps (n = 5 to 200, ten maps per size), with k = 3 and 4. That's 360 rows, and each run is timed once like in the main study. We ran it on a different machine from the four final CSVs, so don't compare its times with Section 5.3. As a check, its 180 M3 rows have the same status and counters as the final CSVs.

| n | k = 4 checks: M3 → M3+ | k = 4 time (ms): M3 → M3+ | k = 3 time (ms): M3 → M3+ |
| --- | --- | --- | --- |
| 20 | 142 → 124 | 0.145 → 0.144 | 0.124 → 0.057 |
| 50 | 766 → 455 | 0.736 → 0.806 | 0.268 → 0.077 |
| 100 | 3,071 → 1,122 | 1.481 → 0.756 | 0.315 → 0.039 |
| 150 | 8,737 → 2,746 | 3.424 → 1.459 | 0.499 → 0.049 |
| 200 | 12,699 → 3,538 | 5.274 → 1.760 | 0.817 → 0.061 |

With 4 colours, M3+ gave the same colouring as M3 on every map and never used more checks. From n = 50 it used 41% to 72% fewer checks on average, and from n = 75 it was faster on every map. Below that the runs take less than a millisecond, so one timing is noisy. At n = 50 it was only faster on 7 of the 10 maps.

With 3 colours it gave the same answer on every map and was about 2 to 13 times faster from n = 20 (faster on 89 of the 90 maps). On average the check count stayed within 3 of M3's.

Neither method ever used its fallback. We also ran both on 9,256 extra random maps (n = 1 to 250): M3+ always agreed with M3, gave the same 4-colour colouring, and never used more checks with 4 colours.

---

## 6. Code structure

The whole program is in **one file**, `multi_city_lighting.py`, split into blocks. The authors are taken from the commit history.

| **Block**                   | **Written by**  | **Contents**                                                                       |
| --------------------------- | --------------- | ---------------------------------------------------------------------------------- |
| 0. Shared                   | Jeannice        | colours, statuses, `MapColouringCSP`, `verify_solution`, `run_algorithm`           |
| 1. Map, baseline, M3, plots | Jeannice        | map generation and validation, parity check, A1, M3, `plot_map`, `plot_comparison` |
| 1.5b M3+                    | Steven          | `structure_aware_solver_plus` and its helpers (`_m3plus_*`)                         |
| 2. M1                       | Hong Shen       | MRV/Degree, LCV, forward checking, `backtracking_generic`, `BT+MRV`, `BT+FC`       |
| 3. M2 and experiments       | Edric, Steven   | `min_conflicts`, `determine_instance_status` (Edric); `run_experiment`, `summarise_results` (Steven) |
| Registry                    | Everyone        | `ALGORITHMS`: name → (function, is_complete)                                       |
| 4. Main                     | Jeannice        | the demo for one n                                                                 |

**Interface.** Every method has the same signature, so the blocks connect directly:

```
def method(csp, guard, rng) -> dict | None     # {city: colour}, or None
```

- A method is run with `run_algorithm("A2", adjacency, colours)`, which returns the status, runtime and counters, and verifies every SAT result.
- For a complete method, `None` means UNSAT. For Min-Conflicts, `None` means FAILED.

**How the parts fit together**

1. Every method compares colours only through `csp.check()`, so the constraint-check counts can be compared.
2. Every loop and recursion calls `guard.check()`, so the time limit works the same way for every method.
3. A2 keeps its consistency check before forward checking. Those checks are counted, even when forward checking has already removed the clashing colours.

---

## 7. Who did what

From the commit history:

- **Jeannice Laurensia Santoso:** the first version of the program, map generation and validation, the parity check, A1, M3, the plots and the demo.
- **Huang Hong Shen:** M1 (A2) and the BT+MRV and BT+FC ablation variants.
- **Edric Andrze Joey:** M2 (Min-Conflicts), the instance status rules, passing the restart budget through the experiment runner, and the final experiment runs in `final_results/`.
- **Steven Tanuwidjaja:** `run_experiment` and `summarise_results`, saving results after every map, merging the branches, the reproduction run on a second machine, and M3+.
- **Brandon Lie and Seyu Wen Bin** worked on the parts outside the code.

Section 5 of the report gives each member's full contribution and percentage.

---

## 8. References

The same list as the report.

Constraint satisfaction problems (Lecture slides 6). (n.d.). CSCI323 Modern Artificial Intelligence, University of Wollongong.

Hale, W. K. (1980). Frequency assignment: Theory and applications. *Proceedings of the IEEE, 68*(12), 1497–1514. https://doi.org/10.1109/PROC.1980.11899

Haralick, R. M., & Elliott, G. L. (1980). Increasing tree search efficiency for constraint satisfaction problems. *Artificial Intelligence, 14*(3), 263–313. https://doi.org/10.1016/0004-3702(80)90051-X

Kempe, A. B. (1879). On the geographical problem of the four colours. *American Journal of Mathematics, 2*(3), 193–200. https://doi.org/10.2307/2369235

Matplotlib Development Team. (n.d.). *Quick start guide*. Matplotlib documentation. Retrieved November 1, 2026, from https://matplotlib.org/stable/users/explain/quick_start.html

Matula, D. W., & Beck, L. L. (1983). Smallest-last ordering and clustering and graph coloring algorithms. *Journal of the ACM, 30*(3), 417–427. https://doi.org/10.1145/2402.322385

Minton, S., Johnston, M. D., Philips, A. B., & Laird, P. (1992). Minimizing conflicts: A heuristic repair method for constraint satisfaction and scheduling problems. *Artificial Intelligence, 58*(1–3), 161–205. https://doi.org/10.1016/0004-3702(92)90007-K

Mount, D. (2021). *CMSC 754 lecture 11: Delaunay triangulations: General properties* [Lecture notes]. University of Maryland. https://www.cs.umd.edu/class/fall2021/cmsc754/Lects/lect11-delaun-prop.pdf

NumPy Developers. (n.d.). *Random generator*. NumPy documentation. Retrieved November 1, 2026, from https://numpy.org/doc/stable/reference/random/generator.html

Popescu, C. (2021). On vertex 3-colourable disc triangulations. *Bulletin Mathématique de la Société des Sciences Mathématiques de Roumanie, 64(112)*(2), 133–145. https://rms.unibuc.ro/bulletin/pdf/64-2/articol_2.pdf

Python Software Foundation. (n.d.). *random — Generate pseudo-random numbers*. Python documentation. Retrieved November 1, 2026, from https://docs.python.org/3/library/random.html

Russell, S., & Norvig, P. (2021). *Artificial intelligence: A modern approach* (4th ed.). Pearson.

SciPy Developers. (n.d.). *Delaunay*. SciPy documentation. Retrieved November 1, 2026, from https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.Delaunay.html

Thomas, R. (n.d.). *The four color theorem*. Georgia Institute of Technology. Retrieved November 1, 2026, from https://thomas.math.gatech.edu/FC/fourcolor.html

Welsh, D. J. A., & Powell, M. B. (1967). An upper bound for the chromatic number of a graph and its application to timetabling problems. *The Computer Journal, 10*(1), 85–86. https://doi.org/10.1093/comjnl/10.1.85

---

## 9. How to run

From the project folder:

```powershell
python -m pip install numpy scipy matplotlib
python multi_city_lighting.py
# Enter the number of cities n: 20
```

The demo uses map seed 42 and runs A1, M1, M2, M3 and M3+ with k = 3 and k = 4. M2 uses its default of one attempt of 10,000 repairs, not the restart settings of the final experiments. The program prints each method's result and saves the maps as PNG files in the current folder. On k = 3 maps that cannot be coloured with three colours, the inner cities with an odd number of neighbours are ringed in red. Set `SHOW_PLOTS = True` to open the plots in windows. UNSAT for k = 3 is the expected answer on most maps.

### 9.1 Quick check

A short run that takes a few seconds. It writes its own file, so it cannot replace any results, and it is not used as evidence:

```powershell
python -c "import multi_city_lighting as m; rows=m.run_experiment([5,10,20],trials=3,algorithms=('A1','A2','A3','M3'),timeout_seconds=0.5,a3_runs=1,max_steps=1000,max_restarts=9,csv_path='quick_check.csv'); m.summarise_results(rows)"
```

### 9.2 Rerun the four final studies

These commands write to `my_results/`, so they never overwrite our files in `final_results/`. On our machines the main study and the ablation each took about half an hour, mostly A1 runs using the full 30 seconds; the other two took a few minutes.

Create the output folder once:

```powershell
New-Item -ItemType Directory -Force my_results
```

Main comparison, 1,120 rows:

```powershell
python -c "import multi_city_lighting as m; rows=m.run_experiment([5,10,20,30,50,75,100],trials=10,algorithms=('A1','A2','A3','M3'),timeout_seconds=30,a3_runs=5,max_steps=1000,max_restarts=9,csv_path='my_results/results.csv'); m.summarise_results(rows)"
```

Larger maps, 240 rows:

```powershell
python -c "import multi_city_lighting as m; rows=m.run_experiment([150,200],trials=10,algorithms=('A3','M3'),timeout_seconds=30,a3_runs=5,max_steps=1000,max_restarts=9,csv_path='my_results/results_large.csv'); m.summarise_results(rows)"
```

No restarts, 250 rows:

```powershell
python -c "import multi_city_lighting as m; rows=m.run_experiment([50,75,100,150,200],k_values=(4,),trials=10,algorithms=('A3',),timeout_seconds=30,a3_runs=5,max_steps=10000,max_restarts=0,csv_path='my_results/results_a3_norestart.csv'); m.summarise_results(rows)"
```

Ablation, every integer n from 5 to 50, 3,680 rows:

```powershell
python -c "import multi_city_lighting as m; rows=m.run_experiment(list(range(5,51)),trials=10,algorithms=('A1','A2','BT+MRV','BT+FC'),timeout_seconds=30,csv_path='my_results/results_ablation.csv'); m.summarise_results(rows)"
```

M3 against M3+, 360 rows, under a minute:

```powershell
python -c "import multi_city_lighting as m; rows=m.run_experiment([5,10,20,30,50,75,100,150,200],trials=10,algorithms=('M3','M3+'),timeout_seconds=30,csv_path='my_results/results_m3plus.csv'); m.summarise_results(rows)"
```

The runner saves the CSV after every map, so a file can exist even if a run was stopped early. Check the row counts above to see whether a study finished.

### 9.3 Look at our results without rerunning

Print the summary tables for one of our files (change the file name for the others):

```powershell
python -c "import csv,multi_city_lighting as m; rows=list(csv.DictReader(open('final_results/results.csv',newline=''))); m.summarise_results(rows)"
```

Plot runtime and constraint checks against n:

```powershell
python -c "import csv,multi_city_lighting as m; rows=list(csv.DictReader(open('final_results/results.csv',newline=''))); m.plot_comparison(rows,'runtime_seconds','compare_time.png'); m.plot_comparison(rows,'constraint_checks','compare_checks.png')"
```

### 9.4 Compare a rerun with our results

The maps and run seeds are fixed, so a rerun should give the same status and the same counters (checks, attempts, backtracks, repairs, restarts) on every run that finishes. Runtimes will differ, and so may a few A1 runs that are close to the 30-second limit. When we reran everything on a second machine, 8 of the 5,290 runs differed: all were A1, and all finished on one machine but timed out on the other. Every counter matched on the 5,219 runs that finished on both.

This command compares one file and prints how many runs finished on both and how many of those differ. Change both file names to compare the others:

```powershell
python -c "import csv; key=lambda r:(r['algorithm'],r['n'],r['k'],r['map_seed'],r['run_seed']); cols=('status','constraint_checks','assignment_attempts','backtracks','repair_iterations','restarts'); load=lambda p:{key(r):r for r in csv.DictReader(open(p,newline=''))}; ours,yours=load('final_results/results.csv'),load('my_results/results.csv'); both=[k for k in ours if k in yours and 'TIMEOUT' not in (ours[k]['status'],yours[k]['status'])]; print(len(both),'runs finished on both,',sum(any(ours[k][c]!=yours[k][c] for c in cols) for k in both),'differ')"
```
