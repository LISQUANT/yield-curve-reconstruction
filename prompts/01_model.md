# Mathematical core

Read CODEX_ARNAUD_UPDATE.md, PROJECT_CONTEXT.md, AGENTS.md, docs/status.md,
docs/decisions.md and docs/handoff.md. Work in the canonical repository on a
feature branch. Preserve the team layout, current tests and unrelated work.
Code and technical documentation are English. Update status, handoff and decisions
with actual evidence. Commit/push coherent verified progress and open/update a PR
when reviewable; never commit to main or merge automatically.

Retain and review yieldcurves/svensson.py. Decimal beta values; positive taus and
nonnegative maturities in years. Handle zero/tiny maturity, negative rates, scalar
and vector inputs. Native annual conversion is log1p of evaluated spots; continuous
forwards derive from discount factors. Run numerical tests including independent
scalar arithmetic and derivative identities for both conventions. Reproduce the
synthetic example separately. No provider or calibration implementation here.
