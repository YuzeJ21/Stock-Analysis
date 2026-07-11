# Coverage Continuity Handoff

The active roadmap is ROADMAP.md. Use it for current priority, dependencies, and stop rules; this file intentionally does not duplicate readiness counts or prioritization.

Start from current, read-only repo truth:

```bash
make project-status-check
make readiness-ops-center
make price-history-proof-queue TOP_N=25
make price-history-batch-closeout TOP_N=25
```

Use `INCLUDE_REVIEWED=1 make price-history-proof-queue TOP_N=25` only for audit visibility of reviewed source-limited items. The default price queue is for unreviewed executable candidates, and the closeout command is read-only: it does not record proof rows, stage files, commit, or push.

Preserve the research-only boundary: data readiness first, analysis second, research decision last; no investment advice, broker trading or integration, order routing, auto-trading, direct buy/sell instructions, fabricated data, provider refreshes, or imports/applies without the roadmap's source-backed gate. Keep generated CSV/JSON/report churn excluded unless an exact artifact is intentionally reviewed, and do not push unless explicitly asked.
