# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Python generator and solver for "Breinbreker" — a cryptarithmetic grid puzzle from Dutch newspaper De Telegraaf. Each letter maps to a unique digit (0–9); multi-letter strings form numbers. The goal is to deduce the mapping so all equations hold.

## Running

```bash
python breinbreker.py                 # generate 1 puzzle with solution
python breinbreker.py --count 5       # generate 5 puzzles
python breinbreker.py --no-solution   # puzzle only, no answer
python breinbreker.py --seed 42       # reproducible output
python breinbreker.py --verify        # self-test: generate + verify 10 puzzles
```

## Architecture (`breinbreker.py`)

Single self-contained file, no dependencies beyond stdlib.

### Puzzle structure

3×3 grid. Default operators: rows use `−`, columns use `+`.

```
[r0c0]  -  [r0c1]  =  [r0c2]
  +            +           +
[r1c0]  -  [r1c1]  =  [r1c2]
  =            =           =
[r2c0]  -  [r2c1]  =  [r2c2]
```

**Key invariant**: only 4 of the 6 equations are independent (rows 0,1 and cols 0,1). Row 2 and col 2 are algebraically implied by the other four. This means the generator only needs to satisfy 4 equations; the remaining two follow automatically.

**Operator compatibility**: For other operator combinations (rows/cols can each be `+` or `−`), the system is self-consistent only when `sign(r1)×sign(c2) = sign(c1)×sign(r2)`. The implied operators are always `row3_op = row_ops[0]` and `col3_op = col_ops[0]`.

### Key functions

- `solve(puzzle, max_solutions=2)` — backtracking solver. Letters sorted by frequency (most-used first for tightest early pruning). Precomputes `checkable_at[depth]`: which equations first become fully determined at each assignment depth. Stops at `max_solutions` to quickly detect non-uniqueness.

- `generate(n, row_ops, col_ops, seed, max_attempts)` — constructive generator. Uses conditional sampling: picks the 4 free variables (`v1`, `v4`, `v3`, `v0`) in an order that enforces all range constraints analytically, avoiding wasted iterations. The remaining 5 values are fully derived. Filters on digit-within-cell uniqueness and all-10-digits coverage, then calls `solve` to check uniqueness.

- `verify(puzzle, solution)` — checks all 6 equations hold for a given assignment.

- `display(puzzle, solution=None)` — prints the letter grid (and optionally the numeric grid) in newspaper style.

### Generation approach

The 4 free arithmetic values are picked in dependency order:
1. `v1` freely
2. `v4` conditioned on `v7 = v1 + c2·v4` landing in range
3. `v3` conditioned on `v5 = v3 + r2·v4` landing in range
4. `v0` conditioned on both `v2 = v0 + r1·v1` and `v6 = v0 + c1·v3` landing in range

Then `v8 = v2 + c3·v5` is computed and range-checked. Each digit must appear without repetition within its cell, and all 10 digits must collectively appear. Digit→letter assignment is random. Uniqueness is verified by the solver.

Typical performance: ~300–400 ms per puzzle (dominated by the uniqueness-check solver call).
