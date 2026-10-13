# Bundesbank reconstruction

Read CODEX_ARNAUD_UPDATE.md, PROJECT_CONTEXT.md, AGENTS.md, docs/status.md,
docs/decisions.md and docs/handoff.md. Work in the canonical repository on a
feature branch. Preserve the team layout, current tests and unrelated work.
Code and technical documentation are English. Update status, handoff and decisions
with actual evidence. Commit/push coherent verified progress and open/update a PR
when reviewable; never commit to main or merge automatically.

Implement yieldcurves/sources/bundesbank.py using current official metadata and
published Svensson parameters. The team scaffold selects Bundesbank: do not block
on the old ECB question or label ECB euro-area AAA as Germany. Verify daily series,
units, native compounding and same-date spot references; keep ZST and coupon-yield
ZAR distinct. Preserve six complete parameters without independent fills.

Use the existing numerical core and justified precision tolerances. Add source,
parser and offline tests, retaining the Fed checks. Extend plots.py and make_report
to the latest common complete US/DE date, displaying both sources/currencies.
Do not silently compare latest-by-country dates. Explain cross-currency limits.
No Portugal calibration or final PDF in this stage.
