# Next Stage Handoff

The active roadmap is ROADMAP.md. It is the sole current prioritization and contains the active Now/Next/Later plan, dependencies, and stop rules.

This handoff is research-only and read-only: do not refresh providers, apply imports, stage files, commit, push, deploy, expose keys, or treat screenshots as data-freshness proof.

Use current command output instead of static readiness counts:

```bash
make project-status-check
make readiness-ops-center
make price-history-proof-queue TOP_N=25
make price-history-batch-closeout TOP_N=25
```

Use `INCLUDE_REVIEWED=1 make price-history-proof-queue TOP_N=25` only to audit reviewed source-limited items. The default queue shows executable unreviewed candidates; the batch closeout is read-only and does not record proof rows, stage, commit, or push.

Preserve the product boundary: data readiness first, analysis second, research decision last; no investment advice, broker integration, order routing, auto-trading, direct buy/sell instructions, or fabricated data.
