#!/usr/bin/env python3
"""
Breinbreker puzzle generator and solver.

A Breinbreker is a puzzle from Dutch newspaper De Telegraaf where each letter
represents a unique digit (0-9). Multi-letter strings form numbers (e.g. "FDJ"
with F=8, D=0, J=6 gives 806). The puzzle is a 3x3 grid with row and column
arithmetic equations.

Grid layout (default operators: rows use '-', columns use '+'):

  [r0c0]  -  [r0c1]  =  [r0c2]
     +           +           +
  [r1c0]  -  [r1c1]  =  [r1c2]
     =           =           =
  [r2c0]  -  [r2c1]  =  [r2c2]

Only 4 of the 6 equations are independent (rows 0,1 and cols 0,1).
Row 2 and col 2 are mathematically implied by the others.

Usage:
    python breinbreker.py               # Generate 1 puzzle with solution
    python breinbreker.py --count 5     # Generate 5 puzzles
    python breinbreker.py --no-solution # Print puzzle without revealing answer
    python breinbreker.py --seed 42     # Reproducible generation
"""

import argparse
import random
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

@dataclass
class Puzzle:
    """A Breinbreker puzzle.

    grid:     3x3 list of letter-strings. E.g. grid[0][0] = "FDJ" means the
              top-left number is constructed from letters F, D, J.
    row_ops:  3 operators ('+' or '-') for the 3 row equations.
              Row r: grid[r][0] row_ops[r] grid[r][1] = grid[r][2]
    col_ops:  3 operators for the 3 column equations.
              Col c: grid[0][c] col_ops[c] grid[1][c] = grid[2][c]
    """
    grid: list[list[str]]
    row_ops: list[str]
    col_ops: list[str]


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

def solve(puzzle: Puzzle, max_solutions: int = 2) -> list[dict[str, int]]:
    """Return all valid letter→digit assignments (up to max_solutions).

    Uses backtracking with early pruning: assigns letters one at a time
    (most-used first) and checks any equation that becomes fully determined.
    Stops as soon as max_solutions solutions are found.
    """
    g = puzzle.grid

    # Build all 6 equations as (left_cell, op, right_cell, result_cell)
    eqs: list[tuple[str, str, str, str]] = []
    for r in range(3):
        eqs.append((g[r][0], puzzle.row_ops[r], g[r][1], g[r][2]))
    for c in range(3):
        eqs.append((g[0][c], puzzle.col_ops[c], g[1][c], g[2][c]))

    # Precompute the set of letters involved in each equation
    eq_letter_sets: list[frozenset] = [
        frozenset(c1 + c2 + c3) for c1, _, c2, c3 in eqs
    ]

    # Order letters by frequency (most frequent first = tightest constraints first)
    freq: Counter = Counter()
    for row in g:
        for cell in row:
            freq.update(cell)

    all_letters: list[str] = sorted(freq.keys(), key=lambda l: (-freq[l], l))
    n = len(all_letters)

    # Precompute which equations become fully determined at each depth.
    # At depth d, letters all_letters[0..d] are assigned.
    assigned_at_depth: list[frozenset] = [
        frozenset(all_letters[: d + 1]) for d in range(n)
    ]
    # For each depth d, record which equations first become fully determined
    # at depth d (i.e. all their letters are in all_letters[:d+1]).
    checkable_at: list[list[int]] = [[] for _ in range(n)]
    for eq_idx, eq_ls in enumerate(eq_letter_sets):
        for d in range(n):
            if eq_ls <= assigned_at_depth[d]:
                checkable_at[d].append(eq_idx)
                break

    # Leading letters (first letter of any multi-char cell) cannot be digit 0
    leads: frozenset = frozenset(
        cell[0] for row in g for cell in row if len(cell) > 1
    )

    solutions: list[dict[str, int]] = []
    assignment: dict[str, int] = {}
    used: set[int] = set()

    def _val(cell: str) -> int:
        v = 0
        for ch in cell:
            v = v * 10 + assignment[ch]
        return v

    def backtrack(depth: int) -> None:
        if len(solutions) >= max_solutions:
            return
        if depth == n:
            solutions.append(dict(assignment))
            return

        letter = all_letters[depth]
        for digit in range(10):
            if digit in used:
                continue
            if digit == 0 and letter in leads:
                continue

            assignment[letter] = digit
            used.add(digit)

            ok = True
            for eq_idx in checkable_at[depth]:
                c1, op, c2, c3 = eqs[eq_idx]
                lhs = _val(c1) + _val(c2) if op == '+' else _val(c1) - _val(c2)
                if lhs != _val(c3) or lhs < 0:
                    ok = False
                    break

            if ok:
                backtrack(depth + 1)

            del assignment[letter]
            used.discard(digit)

    backtrack(0)
    return solutions


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

# Valid operator pairs (row_ops[0], row_ops[1], col_ops[0], col_ops[1]) satisfy
# the compatibility constraint: sign(r1)*sign(c2) == sign(c1)*sign(r2).
# The implied operators are: row_ops[2] = row_ops[0], col_ops[2] = col_ops[0].
_VALID_OP_COMBOS = [
    (('-', '-'), ('+', '+')),  # newspaper default
    (('+', '+'), ('+', '+')),
    (('+', '+'), ('-', '-')),
    (('+', '-'), ('+', '-')),
    (('+', '-'), ('-', '+')),
    (('-', '+'), ('+', '-')),
    (('-', '+'), ('-', '+')),
    (('-', '-'), ('-', '-')),
]


def _sign(op: str) -> int:
    return 1 if op == '+' else -1


# All 8 valid (row_ops, col_ops) combinations.
# Validity constraint: sign(r1)*sign(c2) == sign(c1)*sign(r2).
# Implied operators are always row3=row_ops[0], col3=col_ops[0].
_OP_COMBOS = [
    (('-', '-'), ('+', '+')),
    (('+', '+'), ('+', '+')),
    (('+', '+'), ('-', '-')),
    (('+', '-'), ('+', '-')),
    (('+', '-'), ('-', '+')),
    (('-', '+'), ('+', '-')),
    (('-', '+'), ('-', '+')),
    (('-', '-'), ('-', '-')),
]


def generate(
    n: int = 1,
    row_ops: Optional[tuple[str, str]] = None,
    col_ops: Optional[tuple[str, str]] = None,
    seed: Optional[int] = None,
    max_attempts: int = 500_000,
) -> list[tuple[Puzzle, dict[str, int]]]:
    """Generate n uniquely-solvable Breinbreker puzzles.

    Returns a list of (puzzle, solution) pairs where solution is a dict
    mapping each letter to its unique digit.

    Args:
        n:            Number of puzzles to generate.
        row_ops:      Operators for row equations (rows 0 and 1). If None,
                      chosen randomly from the 8 valid combinations each puzzle.
        col_ops:      Operators for column equations (cols 0 and 1). Must be
                      provided together with row_ops or left as None.
        seed:         Optional random seed for reproducibility.
        max_attempts: Abort if this many attempts are made without finding n puzzles.

    Raises:
        RuntimeError: If max_attempts is reached before finding n puzzles.
    """
    if seed is not None:
        random.seed(seed)

    fixed_ops = row_ops is not None  # caller specified operators explicitly

    # Cell-size layouts. Index order: [r0c0, r0c1, r0c2, r1c0, r1c1, r1c2, r2c0, r2c1, r2c2]
    # For the default ops (rows=-, cols=+):
    #   v2=v0-v1, v5=v3-v4, v6=v0+v3, v7=v1+v4, v8=v2+v5
    # Row-2 cells (v6,v7,v8) are sums, so typically larger than row-0/1 cells.
    SIZE_PATTERNS = [
        (3, 3, 3, 3, 3, 3, 3, 3, 3),  # all 3-digit (standard)
        (3, 3, 3, 3, 3, 3, 3, 3, 3),  # repeated to weight towards all-3-digit
        (3, 3, 3, 3, 3, 3, 3, 3, 3),
        (2, 2, 2, 3, 2, 2, 3, 3, 3),  # balanced
        (2, 1, 2, 3, 2, 2, 3, 3, 3),  # newspaper style
        (3, 2, 2, 3, 2, 2, 3, 3, 3),  # wider col-0
        (3, 2, 1, 3, 2, 2, 3, 3, 3),  # mixed
    ]

    # Letters (avoid I and O to prevent confusion with 1 and 0)
    LETTERS = list('ABCDEFGHJK')

    results: list[tuple[Puzzle, dict[str, int]]] = []
    attempts = 0

    while len(results) < n:
        if attempts >= max_attempts:
            raise RuntimeError(
                f"Could not generate {n} puzzle(s) within {max_attempts} attempts. "
                "Try different operators or increase max_attempts."
            )
        attempts += 1

        # Pick operators (fixed by caller, or random each attempt)
        if fixed_ops:
            cur_row_ops, cur_col_ops = row_ops, col_ops
        else:
            cur_row_ops, cur_col_ops = random.choice(_OP_COMBOS)

        r1, r2 = _sign(cur_row_ops[0]), _sign(cur_row_ops[1])
        c1, c2 = _sign(cur_col_ops[0]), _sign(cur_col_ops[1])
        row3_op = cur_row_ops[0]
        col3_op = cur_col_ops[0]
        c3 = c1

        sz = random.choice(SIZE_PATTERNS)
        lo = [10 ** (sz[i] - 1) if sz[i] > 1 else 0 for i in range(9)]
        hi = [10 ** sz[i] - 1 for i in range(9)]

        # Use conditional sampling to avoid wasting iterations on bad arithmetic.
        # Free variables: v1 (row0-col1) and v4 (row1-col1).
        # Derive v3, v0 conditioned on satisfying all range constraints.

        # v1: free
        v1 = random.randint(lo[1], hi[1])

        # v4: constrained by v7 = v1 + c2*v4 ∈ [lo7, hi7]
        #   → v4 ∈ [(lo7-v1)/c2, (hi7-v1)/c2]  (adjusting for sign of c2)
        if c2 == 1:
            v4_lo, v4_hi = lo[7] - v1, hi[7] - v1
        else:
            v4_lo, v4_hi = v1 - hi[7], v1 - lo[7]
        v4_lo, v4_hi = max(v4_lo, lo[4]), min(v4_hi, hi[4])
        if v4_lo > v4_hi:
            continue
        v4 = random.randint(v4_lo, v4_hi)
        v7 = v1 + c2 * v4

        # v3: constrained by v5 = v3 + r2*v4 ∈ [lo5, hi5]
        #   → for r2=-1: v3 = v5+v4 ∈ [lo5+v4, hi5+v4]
        #   → for r2=+1: v3 = v5-v4 ∈ [lo5-v4, hi5-v4]
        if r2 == -1:
            v3_lo, v3_hi = lo[5] + v4, hi[5] + v4
        else:
            v3_lo, v3_hi = lo[5] - v4, hi[5] - v4
        v3_lo, v3_hi = max(v3_lo, lo[3]), min(v3_hi, hi[3])
        if v3_lo > v3_hi:
            continue
        v3 = random.randint(v3_lo, v3_hi)
        v5 = v3 + r2 * v4

        # v0: constrained by both v2 and v6
        #   v2 = v0 + r1*v1 ∈ [lo2, hi2] → v0 ∈ [lo2-r1*v1, hi2-r1*v1]
        #   v6 = v0 + c1*v3 ∈ [lo6, hi6] → v0 ∈ [lo6-c1*v3, hi6-c1*v3]
        v0_lo = max(lo[2] - r1 * v1, lo[6] - c1 * v3, lo[0])
        v0_hi = min(hi[2] - r1 * v1, hi[6] - c1 * v3, hi[0])
        if v0_lo > v0_hi:
            continue
        v0 = random.randint(v0_lo, v0_hi)
        v2 = v0 + r1 * v1
        v6 = v0 + c1 * v3

        # v8 is fully implied; just check its range
        v8 = v2 + c3 * v5
        if not (lo[8] <= v8 <= hi[8]):
            continue

        vals = [v0, v1, v2, v3, v4, v5, v6, v7, v8]

        # All values positive, no leading zeros
        if any(v <= 0 for v in vals):
            continue
        if any(sz[i] > 1 and v < lo[i] for i, v in enumerate(vals)):
            continue

        # Extract digit sequences for each value
        seqs = [[int(d) for d in str(v).zfill(sz[i])] for i, v in enumerate(vals)]

        # No repeated digits within a single cell (keeps letter-strings readable)
        if any(len(set(seq)) < len(seq) for seq in seqs):
            continue

        # All 10 digits must appear across all cells (puzzle uses all 10 letters)
        all_digits_used = [d for seq in seqs for d in seq]
        if set(all_digits_used) != set(range(10)):
            continue

        # Map digits to letters: assign a random letter to each digit
        letter_shuffle = list(LETTERS)
        random.shuffle(letter_shuffle)
        d2l = {d: letter_shuffle[d] for d in range(10)}

        cells = [''.join(d2l[d] for d in seq) for seq in seqs]
        grid = [cells[0:3], cells[3:6], cells[6:9]]

        puzzle = Puzzle(
            grid=grid,
            row_ops=[cur_row_ops[0], cur_row_ops[1], row3_op],
            col_ops=[cur_col_ops[0], cur_col_ops[1], col3_op],
        )

        solutions = solve(puzzle, max_solutions=2)
        if len(solutions) == 1:
            results.append((puzzle, solutions[0]))

    return results


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def display(puzzle: Puzzle, solution: Optional[dict[str, int]] = None) -> None:
    """Print the puzzle in newspaper-style grid format.

    If solution is provided, also prints the letter→digit mapping and the
    grid with numeric values filled in.
    """
    g = puzzle.grid

    # Column widths for the letter grid
    col_w = [max(len(g[r][c]) for r in range(3)) for c in range(3)]

    def _row_line(cells: list[str], ops: list[str], r: int, widths: list[int]) -> str:
        c0 = cells[0].rjust(widths[0])
        c1 = cells[1].rjust(widths[1])
        c2 = cells[2].rjust(widths[2])
        return f"  {c0}  {ops[r]}  {c1}  =  {c2}"

    def _op_line(op: str, widths: list[int]) -> str:
        parts = [op.center(widths[c]) for c in range(3)]
        return f"  {parts[0]}     {parts[1]}     {parts[2]}"

    def _eq_line(widths: list[int]) -> str:
        parts = ['='.center(widths[c]) for c in range(3)]
        return f"  {parts[0]}     {parts[1]}     {parts[2]}"

    print("BREINBREKER")
    print("Gelijke letters zijn gelijke cijfers.")
    print()
    for r in range(3):
        row_cells = [g[r][c] for c in range(3)]
        print(_row_line(row_cells, puzzle.row_ops, r, col_w))
        if r == 0:
            print(_op_line(puzzle.col_ops[0], col_w))
        elif r == 1:
            print(_eq_line(col_w))

    if solution:
        sol_str = "  ".join(f"{l}={solution[l]}" for l in sorted(solution))
        print(f"\nOplossing: {sol_str}\n")

        # Build numeric cells (digit strings in the correct order)
        num_cells = [
            [''.join(str(solution[ch]) for ch in g[r][c]) for c in range(3)]
            for r in range(3)
        ]
        # Column widths: max of letter and numeric representation widths
        num_w = [
            max(col_w[c], max(len(num_cells[r][c]) for r in range(3)))
            for c in range(3)
        ]
        for r in range(3):
            print(_row_line(num_cells[r], puzzle.row_ops, r, num_w))
            if r == 0:
                print(_op_line(puzzle.col_ops[0], num_w))
            elif r == 1:
                print(_eq_line(num_w))


# ---------------------------------------------------------------------------
# Verification helper
# ---------------------------------------------------------------------------

def verify(puzzle: Puzzle, solution: dict[str, int]) -> bool:
    """Check that a solution satisfies all 6 equations."""
    def val(cell: str) -> int:
        v = 0
        for ch in cell:
            v = v * 10 + solution[ch]
        return v

    for r in range(3):
        a, b, c = val(puzzle.grid[r][0]), val(puzzle.grid[r][1]), val(puzzle.grid[r][2])
        expected = a + b if puzzle.row_ops[r] == '+' else a - b
        if expected != c:
            return False

    for col in range(3):
        a = val(puzzle.grid[0][col])
        b = val(puzzle.grid[1][col])
        c = val(puzzle.grid[2][col])
        expected = a + b if puzzle.col_ops[col] == '+' else a - b
        if expected != c:
            return False

    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Breinbreker puzzles (cryptarithmetic grid puzzles).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--count', '-n', type=int, default=1,
        help='Number of puzzles to generate (default: 1)'
    )
    parser.add_argument(
        '--no-solution', action='store_true',
        help='Print the puzzle without revealing the solution'
    )
    parser.add_argument(
        '--seed', type=int, default=None,
        help='Random seed for reproducible generation'
    )
    parser.add_argument(
        '--verify', action='store_true',
        help='Run a self-test: generate puzzles and verify all equations hold'
    )
    args = parser.parse_args()

    if args.verify:
        _self_test()
        return

    puzzles = generate(n=args.count, seed=args.seed)
    for i, (puzzle, solution) in enumerate(puzzles):
        if args.count > 1:
            sep = '=' * 44
            print(f"\n{sep}")
            print(f"  Puzzle {i + 1} / {args.count}")
            print(sep)
        sol = None if args.no_solution else solution
        display(puzzle, sol)
        if i < len(puzzles) - 1:
            print()


def _self_test() -> None:
    """Generate a batch of puzzles and verify correctness."""
    print("Self-test: generating 10 puzzles and verifying solutions...")
    puzzles = generate(n=10, seed=0)
    for i, (puzzle, solution) in enumerate(puzzles):
        # Verify all 6 equations hold
        assert verify(puzzle, solution), f"Puzzle {i+1}: solution fails equation check!"
        # Verify uniqueness
        sols = solve(puzzle, max_solutions=2)
        assert len(sols) == 1, f"Puzzle {i+1}: expected 1 solution, got {len(sols)}!"
        # Verify no leading zeros
        for row in puzzle.grid:
            for cell in row:
                if len(cell) > 1:
                    assert solution[cell[0]] != 0, \
                        f"Puzzle {i+1}: leading zero in cell '{cell}'!"
    print(f"All {len(puzzles)} puzzles passed verification.")


if __name__ == '__main__':
    main()
