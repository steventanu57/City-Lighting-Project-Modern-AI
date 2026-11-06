# Multi-City Lighting: Graph Colouring as a CSP

Group 17 project for CSCI323 Modern AI: Multi-City Lighting as a Constraint Satisfaction Problem.

## Description

*n* cities are placed at random on a 2D map and connected with the maximum number of
straight roads that do not cross. Every city is then lit with one colour so that no two
cities joined by a road share a colour, using k = 3 (Red, Green, Blue) and
k = 4 (Red, Green, Blue, Yellow).

The program generates and plots the map, colours it with three methods and a baseline,
and compares their performance as *n* grows:

| Method | Approach |
|---|---|
| Baseline (A1) | Naive backtracking |
| M1 (A2) | Backtracking with MRV, Degree, LCV and Forward Checking |
| M2 (A3) | Min-Conflicts local search |
| M3 | Structure-aware solver that uses the planar structure of the map |
| M3+ | A faster version of M3 we added after the presentation. It gives the same answers |

| File | Contents |
|---|---|
| `multi_city_lighting.py` | The whole program |
| `projectoverview.md` | Requirements, methods, theory, experiments, who did what, and how to run (Section 9) |
| `final_results/` | Our four final experiment CSVs (5,290 runs), used for every number in the report, plus the M3 vs M3+ comparison |

## Requirements

The experiments ran on Windows with Python 3.12. We reproduced them with Python 3.12.10,
NumPy 2.2.6, SciPy 1.18.1 and Matplotlib 3.10.3, which gave the same constraint-check
counts on every run that finished on both machines.

Install the packages with:

```bash
pip install numpy scipy matplotlib
```

Then run `python multi_city_lighting.py` and enter the number of cities. See
`projectoverview.md`, Section 9, for the experiments and how to compare a rerun with our results.
