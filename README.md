# LIS yield curve reconstruction

Reconstruct US, German and Portuguese yield curves for LIS Quant Research.
The current implementation covers **US Federal Reserve reconstruction only**.
Germany (Bundesbank), Portugal and the final Macro PDF are later stages.

## Setup

Use Python 3.10 or newer. From this repository:

```console
python -m venv .venv
```

Activate `.venv` (`.venv\Scripts\Activate.ps1` on Windows or
`source .venv/bin/activate` on macOS/Linux), then:

```console
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
```

If PowerShell activation is unavailable, use `.venv\Scripts\python.exe` in place
of `python`. `docs/requirements-tested.txt` records the verified Python 3.12 Windows
environment, not a cross-platform lockfile.

## Acquire the official Fed CSV

```console
python -m yieldcurves.sources.fed --download --output-dir data/raw/fed/new_snapshot
```

The command validates the CSV before saving raw bytes and `provenance.json`.
It uses 30-second timeouts, at most three transient-error attempts, and never
retries forbidden access. Direct downloading returned HTTP 403 in the tested
environment; the real CSV was successfully downloaded from the
[official page](https://www.federalreserve.gov/data/nominal-yield-curve.htm)
in a browser. Do not substitute another vendor's yield series.

For that fallback, select the official CSV link, calculate its SHA256, then import:

```powershell
(Get-FileHash -Algorithm SHA256 -LiteralPath '<downloaded-file>').Hash
python -m yieldcurves.sources.fed --import-file '<downloaded-file>' --expected-sha256 '<hash>' --output-dir data/raw/fed/imported_snapshot
```

Import checks file integrity and format. The hash does not independently prove
Fed authenticity: preserve the official download origin. Unknown download time
is recorded as null, separately from the known local save time. An existing
provenance record from a verified snapshot can instead be reused directly.

## Reconstruct and validate offline

```console
python make_report.py --snapshot data/raw/fed/new_snapshot/feds200628.csv --provenance data/raw/fed/new_snapshot/provenance.json --date 2026-10-13 --output-dir outputs/runs/us_review
```

For a browser import, replace `new_snapshot` with `imported_snapshot`. `--date` is
the latest permissible observation date, not a request to fabricate missing data.
The program chooses the latest complete NSS row on/before it and compares all
30 SVENY maturities. It never makes a network request or silently substitutes
synthetic values. Each output directory must be new.

Outputs: `curve.csv` (301 points from 0 to 30 years), `validation.csv` (all signed
errors in bp and tolerances), `parameters.json`, `provenance.json`, `curve.png`
and `manifest.json`. Rates are decimal continuous annualised rates; the chart
shows percentages. Discount factors are dimensionless. Below-one-year values
are model extrapolation, not validated SVENY observations. Validation failure
writes diagnostics and exits nonzero. Bad input fails with an explanatory error.
Germany is explicitly pending; no second curve is fabricated.

## Verified result

The saved authentic snapshot contains observations through **2026-10-02**, not
13 October. All 30 same-date SVENY references pass. Maximum absolute error:
**0.00464304 bp**; RMSE: **0.00319936 bp**. The precision-derived tolerance is
approximately **0.005 bp**. The migrated suite passes **70 tests**. A guarded
no-network rerun produced identical tables and plots.

See [Fed validation](docs/fed_validation.md) for evidence, rounding assumptions,
source hash and limitations. Fed GSW is staff research hosted by the institution,
not an official Board statistical release. Agreement validates reconstruction of
its fitted curve, not an independent assessment of bond prices or fair value.
Raw snapshots and generated runs remain local and are not included in this repo.

## Learning example and project structure

```console
python examples/first_curve.py --output-dir outputs/synthetic_demo
```

This example uses explicitly synthetic parameters and imports the same model.
The mathematical core is `yieldcurves/svensson.py`; Fed acquisition/parsing lives
in `yieldcurves/sources/fed.py`; reference joins in `yieldcurves/validation.py`;
plots in `yieldcurves/plots.py`; orchestration in `make_report.py`.

Read [START_HERE.md](START_HERE.md) for continuation and branch workflow.
