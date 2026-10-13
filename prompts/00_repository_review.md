# Repository integration

Read CODEX_ARNAUD_UPDATE.md, PROJECT_CONTEXT.md, AGENTS.md, docs/status.md,
docs/decisions.md and docs/handoff.md. Work in the canonical repository on a
feature branch. Preserve the team layout, current tests and unrelated work.
Code and technical documentation are English. Update status, handoff and decisions
with actual evidence. Commit/push coherent verified progress and open/update a PR
when reviewable; never commit to main or merge automatically.

Inspect current README, guidance and code before changing anything. The current
canonical layout is yieldcurves/svensson.py, sources/fed.py, sources/bundesbank.py,
plots.py and make_report.py. Current integration already migrated the latest local
core and 57 existing tests, then added acquisition/integration tests. Do not replace
these with the original ZIP. Record actual reuse paths and validation, not inferred
team conventions. Preserve original local work outside the checkout.
