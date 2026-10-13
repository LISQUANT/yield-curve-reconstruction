# Architecture

Preserve Arnaud's scaffold instead of maintaining a second starter package.

| File | Responsibility |
|---|---|
| yieldcurves/svensson.py | Pure NSS spot, conversion, discount and forward mathematics |
| yieldcurves/sources/fed.py | Bounded acquisition, verified local import, parser, complete dates, normalization and precision bounds |
| yieldcurves/sources/bundesbank.py | Team placeholder; next stage, unchanged |
| yieldcurves/validation.py | Strict matching and signed bp comparison |
| yieldcurves/plots.py | US curve and reference residual chart |
| make_report.py | Offline US reconstruction, CSV/JSON/chart exports and manifest |
| examples/first_curve.py | Explicitly synthetic teaching example |
| tests/ | Numerical, synthetic parser, acquisition failure and offline integration checks |

Raw data and outputs are ignored. Acquisition returns an immutable CSV and
provenance record; reconstruction checks their hash, source and convention.
Core beta units are decimal; tau and maturities are years. Native convention is
explicit. Each new run stores requested/actual dates, source hash, code hashes,
versions, output hashes and validation metrics. No formula is duplicated in plots.

make_report is currently US-only and records Germany as not implemented. Once
Bundesbank is validated it must intersect complete source dates, then use the
latest common US/DE date. Do not silently compare different dates. ECB AAA is a
separate universe. A later PDF reads these outputs rather than recalculating rates.
