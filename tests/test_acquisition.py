"""Network failures use synthetic responses, never live downloads."""

from types import SimpleNamespace

import pytest
import requests

from test_fed import synthetic_csv
from yieldcurves.sources import fed


def test_download_success_and_timeout(monkeypatch):
    raw = synthetic_csv()
    calls = []
    def fetch(url, timeout):
        calls.append((url, timeout))
        return SimpleNamespace(content=raw, raise_for_status=lambda: None)
    monkeypatch.setattr(fed.requests, "get", fetch)
    assert fed.download_csv() == raw
    assert calls == [(fed.SOURCE_URL, 30)]


@pytest.mark.parametrize("failure", [requests.HTTPError("403 Forbidden"),
    requests.HTTPError("503 Unavailable"), requests.ConnectionError("offline"),
    requests.Timeout("timeout")])
def test_download_errors_are_not_hidden_or_retried(monkeypatch, failure):
    calls = []
    def unavailable(*args, **kwargs):
        calls.append(1)
        raise failure
    monkeypatch.setattr(fed.requests, "get", unavailable)
    with pytest.raises(type(failure), match=str(failure)):
        fed.download_csv()
    assert len(calls) == 1


def test_status_checked_before_parsing(monkeypatch):
    def forbidden():
        raise requests.HTTPError("403 Forbidden")
    monkeypatch.setattr(fed.requests, "get", lambda *a, **k:
                        SimpleNamespace(content=b"not csv", raise_for_status=forbidden))
    with pytest.raises(requests.HTTPError, match="403"):
        fed.download_csv()


def test_html_success_response_is_not_data(monkeypatch):
    monkeypatch.setattr(fed.requests, "get", lambda *a, **k:
                        SimpleNamespace(content=b"<html>blocked</html>", raise_for_status=lambda: None))
    with pytest.raises(ValueError, match="Date header"):
        fed.download_csv()


def test_import_needs_no_manifest_and_preserves_bytes(tmp_path):
    source = tmp_path / "input.csv"
    raw = synthetic_csv()
    source.write_bytes(raw)
    output = tmp_path / "snapshot"
    frame = fed.import_snapshot(source, output)
    assert len(frame) == 1
    assert (output / "feds200628.csv").read_bytes() == raw
    assert not (output / "provenance.json").exists()
    with pytest.raises(FileExistsError):
        fed.import_snapshot(source, output)
