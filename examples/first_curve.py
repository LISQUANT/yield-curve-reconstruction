"""Download the official Fed file and show one complete curve date."""

import argparse
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from yieldcurves.sources import fed  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    frame = fed.read_fed_csv(fed.download_csv())
    row = fed.select_complete_date(frame, args.date)
    print(fed.validate_reconstruction(row).to_string(index=False))


if __name__ == "__main__":
    main()
