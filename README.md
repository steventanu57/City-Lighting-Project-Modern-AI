# Multi-City Lighting — Graph Colouring as a CSP

Modern AI Group Assignment · Topic: Constraint Satisfaction Problems

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

| File | Contents |
|---|---|
| `multi_city_lighting.py` | The whole program |
| `projectoverview.md` | Requirements, methods, theory, experiments, responsibilities, and how to run (Section 9) |

## Requirements

Tested on Windows 11 with:
- Python 3.12.10
- numpy 2.2.6
- scipy 1.18.1
- matplotlib 3.10.3

Install the packages with:

```bash
pip install numpy scipy matplotlib
```
