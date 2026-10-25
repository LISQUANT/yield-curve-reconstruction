"""Compatibility launcher; use make_report.py for the main workflow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from yieldcurves.workflow import main  # noqa: E402


if __name__ == "__main__":
    main()
