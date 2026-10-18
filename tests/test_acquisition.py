"""Acquisition failure paths use synthetic fixtures and mocked network responses."""

from hashlib import sha256
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from test_fed import synthetic_csv
from yieldcurves.sources import fed


def test_download_success_and_timeout(monkeypatch):
    raw = synthetic_csv()
    calls = []

    def fetch(url, timeout):
        calls.append((url, timeout))
        return BytesIO(raw)

    monkeypatch.setattr(fed, "urlopen", fetch)
    assert fed.download_csv() == raw
    assert calls == [(fed.SOURCE_URL, 30)]


def test_forbidden_is_not_retried(monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(1)
        raise HTTPError(fed.SOURCE_URL, 403, "Forbidden", {}, None)

    monkeypatch.setattr(fed, "urlopen", forbidden)
    with pytest.raises(RuntimeError, match="--import-file"):
        fed.download_csv()
    assert len(calls) == 1


@pytest.mark.parametrize("failure", [
    HTTPError(fed.SOURCE_URL, 503, "Unavailable", {}, None),
    URLError("offline"), TimeoutError("timeout"),
])
def test_transient_retries_are_bounded(monkeypatch, failure):
    calls, delays = [], []

    def unavailable(*args, **kwargs):
        calls.append(1)
        raise failure

    monkeypatch.setattr(fed, "urlopen", unavailable)
    monkeypatch.setattr(fed.time, "sleep", delays.append)
    with pytest.raises(RuntimeError, match="after 3 attempts"):
        fed.download_csv()
    assert len(calls) == 3 and delays == [1, 2]


def test_html_success_response_is_not_data(monkeypatch):
    monkeypatch.setattr(fed, "urlopen", lambda *a, **k: BytesIO(b"<html>blocked</html>"))
    with pytest.raises(ValueError, match="Date header"):
        fed.download_csv()


def test_import_checks_hash_and_preserves_bytes(tmp_path):
    source = tmp_path / "input.csv"
    raw = synthetic_csv()
    source.write_bytes(raw)
    output = tmp_path / "snapshot"
    with pytest.raises(ValueError, match="SHA256"):
        fed.import_snapshot(source, "0" * 64, output)
    assert not output.exists()
    meta = fed.import_snapshot(source, sha256(raw).hexdigest(), output)
    assert (output / "feds200628.csv").read_bytes() == raw
    assert meta["retrieved_at_utc"] is None
    with pytest.raises(FileExistsError):
        fed.import_snapshot(source, sha256(raw).hexdigest(), output)
