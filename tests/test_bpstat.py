"""Official snapshot checks and deliberately corrupted response rejection."""

from hashlib import sha256
import json
from pathlib import Path
import shutil
from urllib.error import HTTPError

import numpy as np
import pytest

from yieldcurves import benchmarks
from yieldcurves.sources import bpstat

SNAPSHOT = Path(__file__).resolve().parents[1] / "data/example/PT"


def test_official_observations_and_indicative_fit():
    frame, _ = benchmarks.read_snapshot(SNAPSHOT, "2026-10-02")
    np.testing.assert_array_equal(frame.maturity_years, [2, 3, 4, 5, 7, 10])
    np.testing.assert_allclose(frame.yield_percent, [3.28, 3.31, 3.45, 3.56, 3.73, 3.95], rtol=0, atol=1e-12)
    curve, residuals, stats = benchmarks.fit_benchmarks(frame)
    assert stats["method"] == "NS"
    assert stats["display_rmse_bp"] == pytest.approx(1.308102433, abs=1e-6)
    assert curve.maturity_years.min() == 2 and curve.maturity_years.max() == 10
    assert not any("spot" in c or "discount" in c or "forward" in c for c in curve.columns)
    assert residuals.display_minus_observed_bp.abs().max() < 2
    assert not stats["diagnostic_fits"][1]["eligible"]


@pytest.mark.parametrize("field,value", [("source", "Other"), ("status", []),
                                         ("value", [None]), ("size", [2])])
def test_invalid_response_rejected(field, value):
    data = json.loads((SNAPSHOT / "12099454.json").read_bytes())
    data[field] = value
    with pytest.raises(ValueError):
        bpstat.read_response(json.dumps(data), 12099454, 2, "2026-10-02")


@pytest.mark.parametrize("series,maturity,date", [(12099455, 2, "2026-10-02"),
                                                  (12099454, 3, "2026-10-02"),
                                                  (12099454, 2, "2026-10-01")])
def test_series_maturity_and_exact_date_checked(series, maturity, date):
    with pytest.raises(ValueError):
        bpstat.read_response((SNAPSHOT / "12099454.json").read_bytes(), series, maturity, date)


def test_original_response_detects_changed_csv_even_after_rehash(tmp_path):
    shutil.copytree(SNAPSHOT, tmp_path / "pt")
    folder = tmp_path / "pt"
    frame, meta = benchmarks.read_snapshot(folder, "2026-10-02")
    frame.loc[0, "yield_percent"] = 3.29
    frame.to_csv(folder / "observations.csv", index=False)
    meta["sha256"] = sha256((folder / "observations.csv").read_bytes()).hexdigest()
    (folder / "provenance.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="transcription"):
        benchmarks.read_snapshot(folder, "2026-10-02")


def test_failed_download_does_not_create_valid_manifest(tmp_path, monkeypatch):
    def refused(*args, **kwargs):
        raise HTTPError(bpstat.API, 403, "Forbidden", {}, None)
    monkeypatch.setattr(bpstat, "urlopen", refused)
    with pytest.raises(HTTPError):
        bpstat.download_snapshot(tmp_path / "failed", "2026-10-02")
    assert not (tmp_path / "failed/provenance.json").exists()


def test_download_preserves_original_bytes(tmp_path, monkeypatch):
    from io import BytesIO
    from urllib.parse import parse_qs, urlparse
    def saved_reply(request, timeout):
        sid = parse_qs(urlparse(request.full_url).query)["series_ids"][0]
        return BytesIO((SNAPSHOT / f"{sid}.json").read_bytes())
    monkeypatch.setattr(bpstat, "urlopen", saved_reply)
    folder = tmp_path / "new"
    bpstat.download_snapshot(folder, "2026-10-02")
    frame, _ = benchmarks.read_snapshot(folder, "2026-10-02")
    assert len(frame) == 6
    for sid in bpstat.SERIES.values():
        assert (folder / f"{sid}.json").read_bytes() == (SNAPSHOT / f"{sid}.json").read_bytes()
