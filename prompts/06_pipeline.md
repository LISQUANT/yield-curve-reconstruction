# Reproducible multi-country run

Read CODEX_ARNAUD_UPDATE.md, PROJECT_CONTEXT.md, AGENTS.md, docs/status.md,
docs/decisions.md and docs/handoff.md. Work in the canonical repository on a
feature branch. Preserve the team layout, current tests and unrelated work.
Code and technical documentation are English. Update status, handoff and decisions
with actual evidence. Commit/push coherent verified progress and open/update a PR
when reviewable; never commit to main or merge automatically.

Build on make_report.py, sources/, svensson.py and plots.py. Avoid a duplicate
pipeline framework. Implement explicit countries/date policy and immutable run
folders. US/DE use latest common complete date; Portugal missing is visible.
Offline mode makes zero network calls; missing files/providers never fabricate
curves. Preserve raw/native units, provenance, versions, hashes and validation.
Test complete/missing dates, malformed sources, partial coverage and manifest
reconciliation. Keep a small synchronous pipeline. Document exit behaviour.
