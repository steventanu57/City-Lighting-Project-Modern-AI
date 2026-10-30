# Results Verification Report

**Multi-City Lighting — Graph Colouring as a CSP** · Modern AI group project

| | |
|---|---|
| **Date** | 30 October 2026 |
| **Code checked** | `main` at commit `73d83a0` (identical on `person-3` and `person-3-experiments`) |
| **Prepared for** | Steven Tanuwidjaja (Person 3, experiments) and the group |
| **Files** | All paths are relative to the project folder `C:\Users\steve\Documents\VSCode files\Files\CSP\City-Lighting-Project-Modern-AI\`. In VS Code, press **Ctrl+Shift+V** to see the images. |

---

## Verdict

**Every output of the Section 9 commands is correct and matches what we expected, and every requirement of the brief, (a) to (e), is met.** Each claim below links to a file you can open.

| Check | Result |
|---|---|
| Correctness checks on all 4 result files (5,290 runs) | ✅ All pass |
| Same results as a separate earlier run (29 Oct) | ✅ 5,215 runs identical in status and every counter. The only differences are 4 A1 runs close to the 30 s time limit. |
| Independent re-check with SciPy, not the project's own checking code | ✅ 500 maps correct, 1,034 colourings valid, all 926 UNSAT answers backed by a proof |
| Demo images (n = 20) | ✅ All 9 byte-for-byte identical to a fresh run |
| Comparison plots | ✅ Legends, hollow points and missing points match `results.csv` exactly |

---

## 1. What we did

| Step | What | Commit |
|---|---|---|
| Checked the teammates' work | **jeannicels (Person 1):** parity check identical on 1,075 maps; odd cities ringed; timer stops before verification; input is asked again until valid. **Edric (Person 3):** faster Min-Conflicts makes identical choices on 954 runs with 80% fewer checks. **Hong Shen (Person 2):** A2 makes identical choices on 160 maps, now 29–34% faster, with 0 wrong answers out of 1,180; `BT+MRV` now really uses MRV. | `56336b6` `38b248a` `6d2026b` |
| A. Combined Person 3's work | Merged Edric's branch into ours, keeping both his restarts and our save-after-every-map | `793efd9` |
| | `summarise_results` leaves FAILED runs out of the averages, the same way the plots do | `6d6c700` |
| | Documented the restarts and the timed-out/failed rule (Sections 5 and 9) | `83efa1f` |
| B. Updated `main` | Fast-forwarded `main` and `person-3` | `83efa1f` |
| C. Added A2 | Merged Hong Shen's `person-2` into `main`; the code has no stubs left | `398f10c` |
| D. Final runs | Ran every experiment on the final code; Section 9 run times measured | `73d83a0` |
| Your runs (29–30 Oct) | You ran every Section 9 command. **This report checks those outputs.** | — |

---

## 2. How the outputs were checked

1. **Correctness checks** on every result file:
   - every run present, and all methods run on the same maps
   - no `NOT_IMPLEMENTED`
   - complete methods never disagree on a map
   - no colouring on a map the parity proof rules out
   - every k = 4 map actually coloured

   Every SAT colouring was also verified while the program ran; an invalid one would have stopped the run.
2. **Repeatability.** Your files are compared row by row with an earlier run of the same commands, kept in [`verification/reference_run/`](verification/reference_run/).
3. **Independent code.** Roads are recomputed with SciPy's Delaunay triangulation, and odd cities and colourings are checked by separate code, not the project's own functions.
4. **Images.**
   - Your demo images are compared pixel by pixel with a fresh run.
   - The plot legends and markers are recomputed from `results.csv`.
5. **Missing terminal output.** The terminal output you couldn't scroll back to is regenerated in [`verification/terminal_output/`](verification/terminal_output/).

---

## 3. Section 9, command by command

| Command | Your output | Expected | Found |
|---|---|---|---|
| Demo `python multi_city_lighting.py`, n = 20 | 9 files `map_n20*.png` | 50 roads; k = 3 impossible (9 odd cities ringed); A1 22,911, A2 654, M3 38 checks; k = 4 SAT for all four methods | ✅ Exactly. Images byte-for-byte identical to a fresh run ([output](verification/terminal_output/demo_n20.txt)) |
| Quick test | Overwritten by the full run, as Section 9 says | 144 runs, all correct, about 5 s | ✅ Re-run: 144 runs, all checks pass, 5.0 s ([output](verification/terminal_output/quick_test.txt)) |
| Full experiment | [`results.csv`](results.csv) (1,120 runs), [`compare_checks.png`](compare_checks.png), [`compare_time.png`](compare_time.png) | A2 and M3 answer every map; A1 times out from n = 50; A3 can't prove UNSAT | ✅ All checks pass. A2 and M3 answered 140/140; A1 timed out 45 times, all at n ≥ 50 ([tables](verification/terminal_output/tables_results.txt)) |
| Larger n | [`results_large.csv`](results_large.csv) (240 runs) | M3 answers all 40 instances | ✅ 20 SAT and 20 UNSAT; identical to the reference run ([tables](verification/terminal_output/tables_results_large.txt)) |
| A3 without restarts | [`results_a3_norestart.csv`](results_a3_norestart.csv) (250 runs) | Success 72%, 66%, 42%, 30%, 0% at n = 50, 75, 100, 150, 200 | ✅ Exactly ([tables](verification/terminal_output/tables_results_a3_norestart.txt)) |
| Ablation | [`results_ablation.csv`](results_ablation.csv) (3,680 runs) | A2 and `BT+MRV` never time out | ✅ A2 and `BT+MRV` 0 timeouts; `BT+FC` 1; A1 25 ([tables](verification/terminal_output/tables_results_ablation.txt)) |
| Print the tables again | Terminal | The three summary tables | ✅ Saved for all four files in [`verification/terminal_output/`](verification/terminal_output/) |

---

## 4. The brief, requirement by requirement

### (a) Generate and plot a map from a user input *n*

`python multi_city_lighting.py` asks for *n* and asks again until the input is a valid whole number. It then:
- places *n* random cities
- connects them with the **maximum number of straight roads that don't cross** (a Delaunay triangulation with 3n − 3 − h roads, where h is the number of cities on the outer boundary)
- saves the map as `map_n{n}.png`

**Proof:**
- n = 20 gives 50 roads.
- On 500 maps, the roads are identical to SciPy's own Delaunay triangulation, with the full 3n − 3 − h count ([check output](verification/checks/independent_check_output.txt)).

<img src="map_n20.png" width="48%" alt="Blank map, n = 20">

### (b) Colour all cities with 3 colours (Red, Green, Blue)

- **When 3 colours are possible, every method finds a colouring.** For n = 10, all four methods return SAT ([output](verification/terminal_output/demo_n10.txt)).
- **When it's impossible, the program proves it.** The n = 20 map has 9 inner cities with an odd number of neighbours (ringed in red). By Theorem 1 (projectoverview.md, Section 4.2), no 3-colouring can exist.
- **Larger maps are almost never 3-colourable** (Section 4.2: 0 of 200 maps from n = 15). The experiments agree:

  | n | 5 | 10 | 20 | 30 | 50 | 75 | 100 |
  |---|---|---|---|---|---|---|---|
  | 3-colourable maps | 10/10 | 2/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |

- **Independent check:** all 54 three-colourings are valid, and all 926 UNSAT answers are backed by an inner city with an odd number of neighbours.

<img src="verification/figures/map_n10_k3_M3.png" width="48%" alt="n = 10, k = 3: coloured with 3 colours"> <img src="map_n20_k3_M3.png" width="48%" alt="n = 20, k = 3: impossible, odd cities ringed">

*Left: n = 10, coloured with 3 colours. Right: n = 20, impossible; the ringed cities are the proof.*

### (c) Colour all cities with 4 colours (Red, Green, Blue, Yellow)

Every map is 4-colourable (Four Colour Theorem, Section 4.1), and **every k = 4 map in the experiments was coloured**:
- **Complete methods:** in every result file that includes one, every k = 4 map got a verified colouring.
- **Independent check:** M3 coloured all 500 maps and A2 all 480 it ran on, and every one of these colourings is valid.

<img src="map_n20_k4_M3.png" width="48%" alt="n = 20, k = 4, M3"> <img src="map_n20_k4_A2.png" width="48%" alt="n = 20, k = 4, A2">

### (d) Three distinct algorithms, performance compared against *n*

There are three methods plus a baseline, all run **on the same maps** with constraint checks counted the same way:
- **M1 (A2):** backtracking with MRV, Degree, LCV and forward checking
- **M2 (A3):** Min-Conflicts local search
- **M3:** the structure-aware solver
- **Baseline (A1):** naive backtracking

**Plots.** Log scale. A hollow point means some runs timed out or failed and are left out; no point means all of them were.

<img src="compare_checks.png" width="100%" alt="Constraint checks vs n">
<img src="compare_time.png" width="100%" alt="Runtime vs n">

The key numbers are in Section 5 below.

### (e) Plot the coloured map for a given *n* and *k*

Each demo run saves `map_n{n}_k{k}_{method}.png` for k = 3 and k = 4 and every method: 8 coloured maps per *n*, plus the blank map. Examples:
- **n = 20:** in the project folder (`map_n20_k3_A1.png` … `map_n20_k4_M3.png`).
- **n = 10:** in [`verification/figures/`](verification/figures/).

### Method requirements (projectoverview.md, Section 1.2)

| Requirement | Met by |
|---|---|
| At least three meaningfully different methods | Systematic search (M1), local search (M2), use of the map's structure (M3), plus a baseline |
| At least one research article with a DOI | Minton et al. (1992), doi:10.1016/0004-3702(92)90007-K (M2); Haralick & Elliott (1980), doi:10.1016/0004-3702(80)90051-X (M1) |
| Systematic comparison | Same maps for every method (fixed seeds), the same counting of checks and the same time limit, reproducible commands in Section 9 |
| Theoretical and mathematical reasoning | Section 4: the Four Colour Theorem for k = 4; Theorems 1–2 and the Lemma for k = 3. These are confirmed on every map in this report. |

---

## 5. Key numbers (from your result files)

**Mean constraint checks per run**, over runs that ended in SAT or UNSAT. A `*` means some runs timed out or failed and are left out (shown as left out / total), so the real cost is higher.

**k = 3**

| n | A1 (baseline) | A2 (M1) | A3 (M2) | M3 |
|---:|---:|---:|---:|---:|
| 5 | 15 | 73 | 121 | 13 |
| 10 | 627 | 406 | 1,162 * (40/50) | 31 |
| 20 | 16,952 | 871 | none answered | 39 |
| 30 | 402,948 | 1,043 | none answered | 45 |
| 50 | 12,598,670 * (3/10) | 1,079 | none answered | 58 |
| 75 | 29,325,483 * (9/10) | 1,349 | none answered | 47 |
| 100 | none answered | 1,580 | none answered | 30 |

**k = 4**

| n | A1 (baseline) | A2 (M1) | A3 (M2) | M3 |
|---:|---:|---:|---:|---:|
| 5 | 15 | 126 | 55 | 14 |
| 10 | 70 | 289 | 405 | 43 |
| 20 | 4,777 | 598 | 3,482 | 142 |
| 30 | 2,439,818 | 906 | 8,723 | 217 |
| 50 | 13,843,482 * (3/10) | 2,204 | 37,202 | 766 |
| 75 | none answered | 2,396 | 65,215 | 2,347 |
| 100 | none answered | 5,052 | 138,539 | 3,071 |
| 150 | — | — | 202,764 * (3/50) | 8,737 |
| 200 | — | — | 462,171 * (35/50) | 12,699 |

**Min-Conflicts restarts** (k = 4, success on solvable maps; same total budget of 10,000 steps)

| n | 50 | 75 | 100 | 150 | 200 |
|---|---|---|---|---|---|
| 10 attempts × 1,000 steps | 100% | 100% | 100% | 94% | 30% |
| 1 attempt × 10,000 steps | 72% | 66% | 42% | 30% | 0% |

**Ablation for M1** (mean constraint checks, k = 3). Each variant keeps only one technique: `BT+MRV` keeps MRV and Degree, `BT+FC` keeps forward checking.

| n | A1 | A2 (all techniques) | `BT+MRV` | `BT+FC` |
|---:|---:|---:|---:|---:|
| 10 | 627 | 406 | 757 | 393 |
| 20 | 16,952 | 871 | 1,874 | 3,195 |
| 30 | 402,948 | 1,043 | 2,477 | 15,180 |
| 40 | 831,832 | 1,058 | 2,418 | 54,674 |
| 50 | 17,290,710 * (1/10) | 1,079 | 2,656 | 719,128 |

<img src="verification/figures/ablation_checks.png" width="100%" alt="Ablation: constraint checks vs n">

**What the numbers show** (facts only; the explanations belong in the report, as projectoverview.md Section 7 says):
- **M3** answers k = 3 with at most about 60 checks at every *n*, up to n = 200. **A1** needs up to 29 million and times out from n = 50.
- **A2** answers every map up to n = 100 with at most about 5,000 checks on average.
- **A3** cannot prove UNSAT, so at k = 3 it answers only on the rare 3-colourable maps. At k = 4, restarts raise its success at n = 100 from 42% to 100%.
- **Ablation:** with only MRV, the checks stay in the thousands; with only forward checking, they grow to hundreds of thousands by n = 50.

---

## 6. Things to know

- **The 30 s time limit is real time,** so a run close to it can finish one time and time out the next. This happened to 4 A1 runs at n = 50 (finished in 18–29 s once, timed out once). The same maps also time out a different number of times in the full run and in the ablation. Map verdicts never change. Treat A1's averages from n = 50 as lower bounds; they're marked `*` and hollow.
- **The quick test writes `results.csv`.** Run it before the full experiment, never after.
- **The result files (`.csv`, `.png`) are ignored by git,** so they're only on this computer. Share them with the group separately for the report.
- **This report and the `verification/` folder are not committed.** They're local files.

---

## 7. Where the files are

| File | What it shows |
|---|---|
| [`results.csv`](results.csv), [`compare_checks.png`](compare_checks.png), [`compare_time.png`](compare_time.png) | Your full experiment (requirement d) |
| [`results_large.csv`](results_large.csv), [`results_a3_norestart.csv`](results_a3_norestart.csv), [`results_ablation.csv`](results_ablation.csv) | Your larger-n, no-restart and ablation runs |
| `map_n20.png`, `map_n20_k3_*.png`, `map_n20_k4_*.png` (project folder) | Your demo for n = 20 (requirements a, b, c, e) |
| [`verification/figures/`](verification/figures/) | Demo for n = 10 (3 colours possible), the ablation plots, and `all_n_checks.png` (n = 5–200) |
| [`verification/terminal_output/`](verification/terminal_output/) | The terminal output: demo n = 10 and 20, quick test, and the summary tables of all four result files |
| [`verification/checks/`](verification/checks/) | The three check scripts and their outputs |
| [`verification/reference_run/`](verification/reference_run/) | The earlier run (29 Oct) used for the repeatability check |

## 8. Re-run the checks yourself

From the project folder (each takes under 10 seconds):

```powershell
python verification/checks/verify_results.py .
python verification/checks/compare_runs.py . verification/reference_run
python verification/checks/independent_check.py .
```

Expected results:
1. `verify_results.py` ends with `ALL CHECKS PASSED`.
2. `compare_runs.py` shows every answered run identical, with only A1 runs near the time limit differing.
3. `independent_check.py` ends with `invalid: 0` and `without an odd inner city to back them: 0`.
