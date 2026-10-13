# Federal Reserve integration

Read CODEX_ARNAUD_UPDATE.md, PROJECT_CONTEXT.md, AGENTS.md, docs/status.md,
docs/decisions.md and docs/handoff.md. Work in the canonical repository on a
feature branch. Preserve the team layout, current tests and unrelated work.
Code and technical documentation are English. Update status, handoff and decisions
with actual evidence. Commit/push coherent verified progress and open/update a PR
when reviewable; never commit to main or merge automatically.

Use yieldcurves/sources/fed.py for official download/import, parsing and units;
reuse svensson.py. The existing stage is implemented: verify current state before
reworking it. Locate CSV from the official nominal-yield-curve page; keep raw bytes,
source URL, checksum, retrieval/import time, units, universe and convention.
Use finite timeouts and bounded transient retries. A 403 fails with explicit
verified-import instructions, never third-party/synthetic substitution. Offline
reconstruction must make zero network calls. A checksum is integrity evidence,
not source-authenticity proof on its own.

Select one complete post-1979 date on/before the requested cutoff with all six
parameters and 30 SVENY references. Do not fill early restricted-model parameters.
Convert percentage betas and SVENY to decimals, never taus. Compare same-date
continuous spots; SVENPY is not the target. Derive bp tolerances from observed
publication precision and parameter rounding, recording assumptions explicitly.

Use plots.py for charting and make_report.py for offline US-only CSV/JSON/chart
outputs. Show Germany pending. Save 301-point curve, 30 reference comparisons,
parameter/source records and manifest. Check hashes, units, metadata, errors and
a guarded offline rerun. Separate synthetic parser/unit tests from real source
reconstruction. Report Fed staff-research status, actual date and extrapolation.
No Germany, Portugal or final PDF implementation in this bounded stage.
