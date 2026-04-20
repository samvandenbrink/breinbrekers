#!/usr/bin/env python3
"""Generate a pool of Breinbreker puzzles and write them to JSON.

Used by the website to pick a random puzzle on demand.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from breinbreker import generate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--out", default="docs/puzzles.json")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    print(f"Generating {args.count} puzzles...", file=sys.stderr)
    puzzles = generate(n=args.count, seed=args.seed)

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "puzzles": [
            {
                "grid": puzzle.grid,
                "row_ops": puzzle.row_ops,
                "col_ops": puzzle.col_ops,
                "solution": solution,
            }
            for puzzle, solution in puzzles
        ],
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=True, indent=2)
        f.write("\n")

    print(f"Wrote {len(puzzles)} puzzles to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
