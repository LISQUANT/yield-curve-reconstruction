"""Synthetic JSON-stat fixtures test source identity, units and dates."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from yieldcurves.sources import bportugal as bp
from yieldcurves.benchmarks import read_snapshot


def response_bytes(series=12099454, maturity=2):
    data = json.loads((Path(__file__).parent / "fixtures.json").read_text())["bportugal"]
    data["extension"]["series"][0]["id"] = series
    data["dimension"]["maturity"]["category"]["label"]["0"] = f"{maturity} years"
    return json.dumps(data).encode()


def test_percentage_units_are_preserved():
    row = bp.read_response(response_bytes(), 12099454, 2, "2026-10-02")
    assert row["yield_percent"] == 3.0 and row["observation_status"] == "F"


@pytest.mark.parametrize("field,value", [("source", "Other"), ("status", []),
                                         ("value", [None]), ("size", [2])])
def test_invalid_response_rejected(field, value):
    data = json.loads(response_bytes())
    data[field] = value
    with pytest.raises(ValueError):
        bp.read_response(json.dumps(data), 12099454, 2, "2026-10-02")


@pytest.mark.parametrize("series,maturity,date", [(12099455, 2, "2026-10-02"),
                                                  (12099454, 3, "2026-10-02"),
                                                  (12099454, 2, "2026-10-01")])
def test_series_maturity_and_exact_date_checked(series, maturity, date):
    with pytest.raises(ValueError):
        bp.read_response(response_bytes(), series, maturity, date)


@pytest.mark.parametrize("dimension,value", [("unit", "Decimal"), ("periodicity", "Monthly"),
                                            ("territory", "Germany"), ("indicator", "Bond price")])
def test_wrong_financial_quantity_rejected(dimension, value):
    data = json.loads(response_bytes())
    data["dimension"][dimension]["category"]["label"]["0"] = value
    with pytest.raises(ValueError):
        bp.read_response(json.dumps(data), 12099454, 2, "2026-10-02")


def test_failed_download_is_explicit(tmp_path, monkeypatch):
    def refused(*args, **kwargs):
        raise requests.HTTPError("403 Forbidden")
    monkeypatch.setattr(bp.requests, "get", refused)
    with pytest.raises(requests.HTTPError, match="403"):
        bp.download_snapshot(tmp_path / "failed", "2026-10-02")
    assert not (tmp_path / "failed/observations.csv").exists()


def test_download_uses_timeout_and_saves_usable_csv_without_manifest(tmp_path, monkeypatch):
    calls = []
    def reply(url, params, timeout):
        calls.append((url, params, timeout))
        maturity = next(t for t, sid in bp.SERIES.items() if sid == params["series_ids"])
        return SimpleNamespace(content=response_bytes(params["series_ids"], maturity),
                               url=url, raise_for_status=lambda: None)
    monkeypatch.setattr(bp.requests, "get", reply)
    folder = tmp_path / "pt"
    bp.download_snapshot(folder, "2026-10-02")
    frame = read_snapshot(folder, "2026-10-02")
    assert len(frame) == 6 and frame.yield_percent.eq(3).all()
    assert all(url == bp.API and params["obs_since"] == "2026-10-02" and timeout == 30
               for url, params, timeout in calls)
    assert not (folder / "provenance.json").exists()
