"""Rounding diagnostics must not change the strict validation result."""

from pathlib import Path

from yieldcurves.rounding import german_history
from yieldcurves.sources.bundesbank import load_snapshot


def test_preserved_history_reproduces_review_without_relaxing_validation():
    frame, _ = load_snapshot(Path(__file__).resolve().parents[1] / "data/example/DE")
    rows, stats = german_history(frame)
    assert stats["dates"] == 265 and stats["observations"] == 7950
    assert stats["direct_matches"] == 7544 and stats["double_matches"] == 7928
    assert stats["strict_failures"] == 108 and stats["dates_with_strict_failures"] == 87
    point = rows.loc[(rows.observation_date == "2026-10-02") & (rows.maturity_years == 1)].iloc[0]
    assert point.double_match and not point.within_tolerance
    assert point.nearest_2dp_percent == 2.90 and point.via_3dp_then_2dp_percent == 2.91
