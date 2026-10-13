# LIS research working agreement

Read CODEX_ARNAUD_UPDATE.md, PROJECT_CONTEXT.md, docs/status.md,
docs/decisions.md and docs/handoff.md before changing code. Current user
instructions take precedence. Keep code and technical documentation in English.

## Repository workflow

Canonical repository: https://github.com/LISQUANT/yield-curve-reconstruction.
Preserve Arnaud's paths: yieldcurves/svensson.py, yieldcurves/sources/fed.py,
yieldcurves/sources/bundesbank.py, yieldcurves/plots.py and make_report.py.
Do not introduce a parallel src/lis_curves package. Inspect current status and
origin, work on a feature branch, preserve unrelated work, and never push to main.
The user authorizes verified feature-branch commits/pushes and a reviewable PR.
Do not merge automatically. Keep raw/licensed datasets, environments, credentials
and generated runs out of Git. Authentication failures require an honest blocker,
not passwords/tokens in chat. Avoid duplicate PRs for the same branch.

## Code and financial contract

Use small functions, intuitive snake_case names and short unit-aware docstrings.
Useful comments explain numerical or financial choices. Avoid decorative or
numbered banners, duplicate formulas and unnecessary frameworks. Keep mathematics
independent of downloads, file writes and plots. Use pathlib and main guards.

Beta values are decimal rates; tau and maturities are years. Convert percentage
betas, never taus. Require finite parameters, positive taus and nonnegative finite
maturities. Handle zero/tiny maturities stably; negative rates and D(T)>1 can be
valid. Preserve native compounding. Convert evaluated annual rates with log1p,
not coefficients. Derive continuous forwards from -d log D/dT.

Reconstruct US/Germany from published parameters; do not refit by default.
Fed SVENY is continuous spot; SVENPY is a different par-yield target. Fed GSW
is institution-hosted staff research, not an official Board statistical release.
Bundesbank is the specified German provider; ECB AAA is a separate euro-area
benchmark. Future US/DE comparisons use their latest common complete date.
Do not label coupon-bond YTM as spot. Portugal starts with a documented search for
published parameters or a suitable official zero curve; only then propose
estimation/alternatives from actual data. No final calibration method is approved.

## Evidence and stage boundaries

Retain raw bytes, source URL, retrieval/import time, checksum, date, units,
convention and universe. Do not fill missing parameters independently. Use bounded
network timeouts/retries; a 403 produces an import alternative, never fake data.
Offline reconstruction performs no network calls. Checksums verify integrity,
not institutional authenticity on their own.

Keep mathematical tests, synthetic parser fixtures, official-reference comparisons
and future price-fit diagnostics separate. Tolerances follow observed publication
precision/rounding assumptions; never widen them to hide a failure. A match to
smoothed published rates validates reconstruction, not economic fair value.
Label synthetic examples and model extrapolation. Record requested/actual dates.

Implement only the current bounded stage. Germany/Portugal and the final PDF are
not part of the Fed integration. Update state, handoff, sources, decisions and
prompts after each stage with actual commands/results and limitations. Final PDF
work must read one validated run's outputs; prototypes are not market reports.
