# Sovereign Yield Curve Reconstruction

Nelson-Siegel-Svensson reconstruction of US Treasury and German Federal-security
zero-coupon curves from published parameters. Portugal has a separate indicative
Nelson–Siegel fit to six verified daily BPstat benchmark yields. The original
bond-price calibration remains available; no verified price panel has been supplied.


The [research note (PDF)](docs/research_note.pdf) explains the method and results.
For a quick look at the figures: [US and Germany](docs/figures/us_germany.png),
[Portugal](docs/figures/portugal.png) and [validation](docs/figures/validation.png).

The model returns spot rates, discount factors and instantaneous forwards.
Betas are decimal rates and maturities and taus are years. US spots use continuous
compounding; German spots use effective annual compounding. Cross-country figures
convert evaluated rates to continuous units. They are not credit-spread charts.
See [methodology](docs/methodology.md) for the equations and rounding policy.

## Install

Python 3.10 or newer. In this project directory:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

On macOS/Linux use `.venv/bin/python` instead. The tested environment is recorded
in `docs/requirements-tested.txt`; the fresh-install check is recorded in
`docs/requirements-clean-tested.txt`. These are dependency snapshots, not universal lockfiles.

## Run

With the environment activated:

```console
python scripts/run_yield_curves.py
```

On Windows without activation:

```powershell
.venv\Scripts\python.exe scripts/run_yield_curves.py
```

One command loads the pinned source snapshots, selects the latest complete common
date up to today, reconstructs the curves, checks published rates, exports CSVs
and vector figures, and generates a six-page PDF. It uses an existing snapshot
without downloading again. If no snapshot is configured, it attempts acquisition.

Optional controls:

```console
python scripts/run_yield_curves.py --offline --date 2026-10-02 --output-dir outputs/historical_run
python scripts/run_yield_curves.py --refresh
```

`--offline` forbids network calls. `--refresh` attempts new official downloads and
reports any fallback to a saved snapshot. Output directories must be new. Without
`--output-dir`, a unique directory is created under `outputs/`.

Exit codes: 0 means all available curve comparisons pass; 1 means an input or
execution error; 2 means outputs were generated but a published-rate comparison
failed. A comparison failure is not silently removed or repaired.

## Saved empirical results

The reference results below are for **2 October 2026**. They can be regenerated with the command above; generated `outputs/` folders are not committed:

| Market | References within rounding tolerance | Maximum absolute error | RMSE |
|---|---:|---:|---:|
| United States | 30/30 | 0.004643 bp | 0.003199 bp |
| Germany | 29/30 | 0.527981 bp | 0.318513 bp |

Germany's one-year result lies outside its 0.504488 bp allowance. This exception
is unresolved and the run returns **exit code 2**. It is retained in the report.
Double rounding reproduces 7,928 of 7,950 German historical spots, but remains
an unconfirmed hypothesis; 22 observations are unexplained. See
[German investigation](docs/german_check.md). The date is not chosen for fit quality.
The German snapshot extends to 16 October. No synthetic data enter these results.

Portugal: 2Y 3.28%, 3Y 3.31%, 4Y 3.45%, 5Y 3.56%, 7Y 3.73%, 10Y 3.95%.
The NS smoothing RMSE is **1.308102 bp**, maximum residual **1.946545 bp**.
These are daily average coupon-bond yields, not spot rates. The line is drawn
only over 2–10 years and supplies no discount factors, forwards or spot spreads.

## Outputs

Each run contains:

- `research_note.pdf`: methodology, real results, validation and limitations.
- `curves.csv`, `validation.csv`, `selected_maturities.csv`: numerical results.
- `US/` and `DE/`: country parameters, references and source provenance.
- `PT_benchmarks/`: original BPstat responses, yields, NS residuals and separate figures.
- `DE/rounding_history.csv`: all 7,950 historical rounding comparisons.
- `figures/`: spot/forward comparison, native-rate validation and discount curves,
  each in PDF, SVG and PNG.
- `manifest.json`: dates, results, source coverage, software versions and hashes.

Numerical tables, figures and the PDF are reproducible from the same inputs and
software. Per-run creation timestamps in the legacy US manifest are not expected
to be byte-identical. Raw files remain unchanged and are never overwritten.

## Data

[Federal Reserve GSW](https://www.federalreserve.gov/data/nominal-yield-curve.htm)
supplies continuous zero rates and NSS parameters for off-the-run coupon Treasuries.
It is a staff research dataset, not a Board statistical release. Direct requests
currently return HTTP 403; the verified official browser download is preserved.

[Bundesbank BBSIS](https://www.bundesbank.de/en/statistics/money-and-capital-markets/interest-rates-and-yields/daily-term-structure-on-listed-federal-securities-651570)
supplies six parameters and 30 annual spot series. Automatic acquisition was
verified. Raw bytes, source URLs, retrieval times and SHA256 hashes are retained.

`data/snapshots.json` selects the small, redistributable `data/example/` bundle
(about 353 kB): a documented one-date Fed excerpt, unchanged German series files
and original BPstat replies. A fresh copy can reproduce the historical run
offline without the full local data archive. [Source instructions](docs/data_sources.md)
record reuse conditions, extraction details, hashes and optional fresh acquisition.
The source assessment, calibration method and import format are in
[Portugal](docs/portugal.md). Supply `--portugal-dir data/raw/portugal/DATE`
to the same command after preparing a verified panel. Portugal exports separate
price residuals and a curve measured from settlement; it is not included in the
published-spot validation or the common comparison figure.

## Code and tests

The [reading guide](docs/reading_guide.md) explains the calculation in order.
Start with `yieldcurves/svensson.py`, then `yieldcurves/reconstruction.py` and
`yieldcurves/workflow.py`. Readers are in `yieldcurves/sources/`; plotting and PDF
layout are in `plots.py` and `report.py`. The small launcher is in `scripts/`.
`make_report.py` retains the original US-only command for existing callers.

```console
python -m pytest -q
python -m ruff check .
```

The tests cover mathematical limits, units, forwards, strict joins, BPstat provenance, source
validation, offline execution, coupon-price calibration and official reference regressions. The latter
retain the German exception. Synthetic teaching examples remain in `examples/`.

The comparison validates reconstruction of fitted institutional curves, not an
independent fit to bond prices. Values below one year are extrapolation relative
to the validation grid. Currency, liquidity and methodological differences limit
cross-country interpretation. Portugal's benchmark fit is an indicative tenor
profile; a genuine zero-coupon calibration still requires bond prices and cash flows.

## Review status

This version is prepared for review on a feature branch. The previously
executed checks are recorded in `docs/verification.json`. Keep the generated
`outputs/` folder local; `docs/research_note.pdf` is the included example report.
