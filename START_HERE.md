# Start here

Use this checkout of LISQUANT/yield-curve-reconstruction. It follows the structure
Arnaud created on 13 October 2026. The older lis-yield-curves folder is a preserved
local source archive, not the canonical package or a repository to push wholesale.

Read README.md for installation, acquisition/import and offline reconstruction.
Then read CODEX_ARNAUD_UPDATE.md, PROJECT_CONTEXT.md, AGENTS.md, docs/status.md,
docs/decisions.md and docs/handoff.md. Verification records under docs/history
belong to the old checkout; docs/verification.json records the migrated checkout.

Continue one prompt at a time. Prompt 00 integration and prompt 01 model are
verified; prompt 02 Fed is complete within the documented download limitation.
Next is prompt 03 Bundesbank. Portugal research follows in prompt 04; calibration
requires a data/method decision. Pipeline and PDF follow verified source stages.

Work on a feature branch, test, commit and push coherent progress, then open/update
a PR for review. Do not modify main or merge the PR automatically. No credentials,
raw data, generated runs or environments belong in commits.
