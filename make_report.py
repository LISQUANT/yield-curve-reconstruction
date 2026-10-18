"""Reconstruct one saved US curve (legacy command)."""

import argparse
import json
from pathlib import Path

from yieldcurves.reconstruction import reconstruct


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", choices=["US"], default="US",
                        help="US only; use scripts/run_yield_curves.py for joint US/Germany results.")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--date", required=True, help="Latest permissible date (YYYY-MM-DD).")
    parser.add_argument("--output-dir", type=Path, required=True, help="New run directory.")
    args = parser.parse_args()
    try:
        result = reconstruct(args.snapshot, args.provenance, args.date, args.output_dir)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Fed reconstruction failed: {exc}\n")
    print(json.dumps(result, indent=2))
    if not result["validation_passed"]:
        raise SystemExit("Fed reconstruction failed its precision-derived tolerance.")


if __name__ == "__main__":
    main()
