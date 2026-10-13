# Fed reconstruction: 2 October 2026

Reverified in the canonical repository on 13 October 2026 using the original
12 October browser snapshot. The 13 October cutoff still selects 2 October. This is a reconstruction from an authentic
Federal Reserve CSV, separate from the synthetic model example.

## Source and acquisition

[Official landing page](https://www.federalreserve.gov/data/nominal-yield-curve.htm)
links to [the CSV](https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv).
Direct urllib requests returned HTTP 403 for CSV and HTML. The official CSV link
was successfully downloaded through the Codex in-app browser to Downloads and
copied byte-for-byte into data/raw/fed/browser_20261012/feds200628.csv.
No third-party dataset, CMT or par-yield substitute was used.

The original is 16,653,918 bytes with SHA256:
2ebdb0a0e94c586445ab9255c7c2d4809f2cdb3776493388453ebb9587ec4342.
Retrieval/capture time: 2026-10-12T18:04:52.394012+00:00, recorded just after
browser download. provenance.json preserves the URL, acquisition channel, hash,
units, convention and instrument universe. Raw data and run files are ignored by
Git and kept locally. No redistribution permission is inferred.

The Fed identifies this as a staff research product, not an official Board
statistical release. It estimates the off-the-run nominal Treasury coupon-security
curve, excluding bills, floating-rate notes and the newest/first prior issues.
These are institution-published fitted rates, not raw traded zero-coupon quotes.

## Observed format and date selection

The downloaded file has nine preamble lines before its Date header, including
SVENY continuous-compounding metadata. Dates are YYYY-MM-DD. There are 17,038 rows
from 1961-06-14 to 2026-10-02. Missing observations include NA; early rows have
BETA3=0 and TAU2=-999.99, consistent with the restricted pre-1980 model described
on the landing page. The reader does not repair these or forward-fill parameters.

The implementation requires all six finite parameters, positive taus, all 30
finite SVENY references and a post-1979 observation. It selects the latest complete
date on/before the cutoff. With a 2026-10-12 cutoff, actual date is 2026-10-02.
This is the latest in the saved snapshot, not a claim of market data for 12 October.

BETA0-BETA3 and SVENY percentage values are divided by 100; taus remain in years.
The file preamble and [GSW Table 1](https://www.federalreserve.gov/pubs/feds/2006/200628/index.html)
establish continuous zero-coupon SVENY versus coupon-equivalent par SVENPY.
Only SVENY01-SVENY30 are used for this comparison. Percentage normalization is
also corroborated by agreement across all reference maturities, rather than a
visual comparison with an unrelated quoted Treasury yield.

## Precision and acceptance rule

The observed SVENY export is quantized to four decimal places in percentage
units, with trailing zeros suppressed. Under nearest rounding, half the last
place is 0.00005 percentage points = 0.005 bp. This is a policy derived from the
observed export precision, not a published Fed accuracy guarantee. If publication
precision or rounding behaviour changes, revisit this assumption rather than
widening the tolerance until it passes.

Parameter-token rounding is bounded separately using half the last printed digit
(including scientific notation). Betas are converted before bounding. Since
L(x)=integral_0^1 exp(-ux)du, |L'|<=1/2. For C=L-exp(-x), |C'|<=3/2.
Thus tau contributions are bounded by T/tau_min**2 times the relevant beta
magnitudes and half-step uncertainties. Adding all beta uncertainties gives a
conservative bound over each parameter's rounding interval. For this row the
largest parameter bound is 6.432742e-11 bp. A 1e-9 bp numerical allowance is added.
Neither component is fitted to the observed residuals.

Total tolerance at each maturity is approximately 0.005000001 bp. Decimal model
minus decimal reference, multiplied by 10,000, is the signed error in bp.

## Results

All 30 maturities pass. Maximum absolute error: 0.004643039658 bp.
Mean absolute error: 0.002952522476 bp. RMSE: 0.003199358373 bp.
The full-precision CSV is outputs/runs/fed_integration_20261013/validation.csv.

| Years | Published SVENY (%) | Reconstructed (%) | Signed error (bp) |
|---|---|---|---|
| 1 | 4.5040 | 4.50403843 | +0.00384258 |
| 2 | 4.7962 | 4.79622129 | +0.00212854 |
| 3 | 4.9233 | 4.92328358 | -0.00164163 |
| 4 | 4.9822 | 4.98220381 | +0.00038053 |
| 5 | 5.0201 | 5.02006390 | -0.00360993 |
| 6 | 5.0577 | 5.05766242 | -0.00375819 |
| 7 | 5.1024 | 5.10244131 | +0.00413082 |
| 8 | 5.1554 | 5.15544204 | +0.00420392 |
| 9 | 5.2150 | 5.21495758 | -0.00424152 |
| 10 | 5.2784 | 5.27837923 | -0.00207709 |
| 11 | 5.3431 | 5.34307442 | -0.00255813 |
| 12 | 5.4068 | 5.40675758 | -0.00424170 |
| 13 | 5.4676 | 5.46760573 | +0.00057262 |
| 14 | 5.5243 | 5.52425357 | -0.00464304 |
| 15 | 5.5757 | 5.57573851 | +0.00385097 |
| 16 | 5.6214 | 5.62143058 | +0.00305785 |
| 17 | 5.6610 | 5.66096388 | -0.00361226 |
| 18 | 5.6942 | 5.69417624 | -0.00237616 |
| 19 | 5.7211 | 5.72105903 | -0.00409653 |
| 20 | 5.7417 | 5.74171682 | +0.00168189 |
| 21 | 5.7563 | 5.75633557 | +0.00355674 |
| 22 | 5.7652 | 5.76515807 | -0.00419286 |
| 23 | 5.7685 | 5.76846508 | -0.00349229 |
| 24 | 5.7666 | 5.76656096 | -0.00390372 |
| 25 | 5.7598 | 5.75976295 | -0.00370508 |
| 26 | 5.7484 | 5.74839304 | -0.00069585 |
| 27 | 5.7328 | 5.73277207 | -0.00279291 |
| 28 | 5.7132 | 5.71321534 | +0.00153441 |
| 29 | 5.6900 | 5.69002952 | +0.00295221 |
| 30 | 5.6635 | 5.66351044 | +0.00104372 |

The 301-point curve grid spans 0-30 years in steps of 0.1 years. Its portion below
one year is model extrapolation without SVENY validation; do not interpret it as
a bill or money-market observation. Discount factors and continuous instantaneous
forwards are derived from the same curve. The graph displays the actual date,
USD universe, source and signed residuals.

## Files and reproduction

- yieldcurves/sources/fed.py: preamble-aware parser, date selection,
  percentage normalization and precision-aware comparison.
- make_report.py: explicitly offline local import and run outputs.
- tests/test_fed.py: synthetic parser/unit fixtures, distinct from live validation.
- outputs/runs/fed_integration_20261013/: curve.csv, validation.csv, parameters.json,
  provenance.json, curve.png and manifest.json.
- outputs/runs/fed_integration_offline/: independently rerun outputs from the same file.
- docs/verification.json: execution evidence.

From the project folder with its tested .venv:

```powershell
.\.venv\Scripts\python.exe make_report.py --snapshot data/raw/fed/browser_20261012/feds200628.csv --provenance data/raw/fed/browser_20261012/provenance.json --date 2026-10-12 --output-dir outputs/runs/fed_reproduction
```

Use a fresh output directory; previous runs cannot be overwritten. A failed
comparison still writes diagnostics and causes a nonzero CLI exit. A bad hash,
wrong convention, malformed CSV or lack of complete dates raises an error before
results are written. This report command is offline and has no synthetic fallback. The acquisition
command in sources/fed.py now implements bounded direct downloading and verified
import. Its live smoke check still returns HTTP 403; use the official browser
fallback. A successful automated live retrieval is not claimed.

70 tests and Ruff pass. The actual offline rerun patched socket.socket to fail on network use; it succeeded. All five result
files were byte-identical across runs, with matching manifest hashes. Manifest
creation times differ by design. The chart was visually inspected and CSV counts,
summary metrics and dates reconciled. The numerical core was not changed.

Agreement validates reproduction of the Fed's fitted curve under its published
convention. It is not an independent bond-price calibration, a fair-value estimate,
a forecast, or validation of every historical date. The previous synthetic
outputs and prototype PDFs remain unchanged.

Next bounded stage: prompts/03_germany.md. Bundesbank is selected by Arnaud's
scaffold. Team integration is now implemented on a feature branch for review.
Germany, Portugal and the final PDF are not included in this Fed stage.
