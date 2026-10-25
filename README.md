# Sovereign Yield Curve Reconstruction

Reconstruct US and German zero-coupon curves from published Svensson parameters,
and fit a separate indicative Nelson-Siegel profile to Portuguese benchmark yields.
The outputs are CSV tables and figures.

## Install and run

Use Python 3.10 or newer. Create and activate a virtual environment, then run:

```console
pip install -r requirements.txt
python make_report.py --date 2026-10-02
```

Omit `--date` to use the latest complete common US/German observation available
on or before today. The command downloads official data into `data/` and creates
a new directory under `outputs/`. Both directories are excluded from Git.
The Fed supplies a full historical file; German requests use a date window and
Portuguese requests filter observations from the selected date.

Downloads use `requests`, a timeout and HTTP status checks. An HTTP failure is
reported explicitly. If the Fed blocks a request, download its official CSV in a
browser and pass `--fed-file PATH`. No hashes or manifests are required.
To reuse downloaded files without network access:

```console
python make_report.py --offline --date 2026-10-02
```

Use `--data-dir PATH` for another data directory and `--output-dir PATH` for a
new output directory. Existing output directories are not overwritten.
`--germany-dir PATH` accepts the original German series files;
`--portugal-benchmarks PATH` accepts a folder containing `observations.csv`.

## Outputs and interpretation

- `curves.csv`, `selected_maturities.csv`: US/German spots, discount factors and forwards.
- `validation.csv`, `summary.csv`: comparisons with published zero rates, in basis points.
- `US/`, `DE/`: parameters and country results, including German rounding checks.
- `PT_benchmarks/`: Portuguese observations, fitted yields and residuals.
- `figures/`: comparison charts in PNG, SVG and PDF. No research report is generated.

US native rates are continuously compounded; German native rates are effective
annual rates. Comparison plots convert evaluated rates to continuous compounding.
Model betas are decimal rates; maturities and taus are in years. Cross-country
comparisons are not credit-spread estimates. Values below one year extrapolate
beyond the published validation grid.

For 2 October 2026, US validation passes 30/30 points. Germany passes 29/30:
the one-year error is 0.527981 bp against a 0.504488 bp allowance. This unresolved
exception remains a failure. Double rounding is an unconfirmed explanation,
not a change to the validation tolerance. Exit codes are 0 for passing comparisons,
1 for input/download errors, and 2 for generated results with validation exceptions.

Portugal uses six daily average coupon-bond benchmark yields over 2–10 years.
Its indicative Nelson-Siegel fit is not a zero-coupon curve and supplies no
discount factors, forwards or spot spreads. The separate bond-price calibration
is retained via `--portugal-dir PATH`, but requires a verified price/cash-flow panel.
Its `bonds.csv` and `cashflows.csv` inputs are validated in
`yieldcurves/sources/portugal.py`, including dates, price basis and cash-flow conventions.

## Sources and tests

- [Federal Reserve GSW](https://www.federalreserve.gov/data/nominal-yield-curve.htm):
  staff research NSS parameters and continuous zero rates.
- [Bundesbank](https://www.bundesbank.de/en/statistics/money-and-capital-markets/interest-rates-and-yields/daily-term-structure-on-listed-federal-securities-651570):
  NSS parameters and annual zero rates.
- [Banco de Portugal BPstat](https://bpstat.bportugal.pt/serie/12099454):
  daily Portuguese benchmark yields, series 12099454–12099459 (underlying source LSEG).

Downloaded market data are not distributed with the code. Source readers check
series identity, units and dates. Deterministic tests use small synthetic fixtures:

```console
python -m pytest -q
```
