# Product Direction Decision

Current decision: provisional. The repository has a passing local performance release gate and a controlled GitHub/LinkedIn demo package, but hosted delivery and external pilot evidence are not yet available.

This document prevents the interface from drifting toward a operated SaaS claim before the operating model, demand, licensing, and support evidence exist.

## Candidate Paths

### Portfolio-quality research prototype

Choose this when the primary value is demonstrating readiness-first product thinking, transparent methodology, research UX, and data-governance boundaries.

Evidence expected:

- A stable local demo and curated screenshots.
- Reproducible public checks and performance evidence.
- Selected high-quality company, ETF/exclusion, blocked-data, and proof-history examples.
- Clear methodology, controlled-demo license, and lightweight maintenance expectations.

### Maintained research tool

Choose this when a small group repeatedly uses the product for readiness triage and single-company research review, but broad multi-user operations are not justified.

Evidence expected:

- Repeat-use cases from external reviewers.
- A dependable controlled preview or installation path.
- Documented refresh ownership, freshness expectations, provider boundaries, and a manageable support load.
- Selected trusted-peer and source-backed data workflows that can be maintained without full-universe promises.

### Operated research platform

Choose this only when repeated user demand and operating economics justify production ownership.

Evidence expected:

- Authentication and access controls.
- Licensed dependable providers, scheduler/retry behavior, monitoring, alerting, input versioning, and provenance enforcement.
- Usage analytics, support process, incident handling, data-quality operations, and clear legal/data-licensing boundaries.
- A demonstrated workflow valuable enough to justify ongoing provider and maintenance cost.

## Decision Criteria

| Criterion | Evidence required | Current state |
| --- | --- | --- |
| Reviewer demand | Observed task completion, repeat-use case, and return intent from 10-20 controlled reviewers. | `awaiting_external_review` |
| Operating burden | Measured deployment, refresh, review, incident, and support work. | Local gates known; hosted burden unknown. |
| Data licensing | Written rights and attribution boundaries for every operated provider/source. | Controlled repo license exists; operated data rights are not established. |
| Provider reliability | Repeated source availability, deterministic limits, rejection handling, and provenance. | Optional keyed providers remain unconfigured; source-proof queues are exhausted. |
| Monitoring and support | Health checks, logs, alerting, ownership, response expectations, and user support process. | Repo-side guidance exists; hosted operations are `external_account_required`. |
| Analytical depth | Trusted-peer pilot and methodology evidence show repeatable value beyond standalone DCF. | Trusted-peer source rows are `awaiting_reviewed_source`. |
| Misuse risk | Reviewers understand research-only, withheld, blocked, and excluded states without interpreting the product as advice or a live terminal. | Awaiting controlled pilot evidence. |

## Current Evidence

- Local five-route desktop/mobile performance gate: passed on the fixed demo snapshot.
- Public package: pilot-ready with manual gates.
- Independent-beta protocol: locally ready for the current four-route Commercial Research Beta workflow, with a complete privacy-safe scorecard; no independent sessions are on record.
- Hosted URL and enforced private access: `external_account_required`.
- Controlled reviewer findings: `awaiting_external_review`.
- Trusted-peer expansion and any commercial-use peer rights: `awaiting_reviewed_source`.
- Optional earnings and estimates: intentionally locked until trusted rows exist.

## Decision Rule

Do not infer demand from repository activity, screenshots, test counts, or the creator's own use. Do not choose the operated-platform path merely because the interface can resemble a hosted product.

Revisit the decision only after:

1. A hosted or otherwise reproducible external delivery path is verified.
2. Ten to twenty reviewers complete the task-based pilot.
3. Critical trust, comprehension, performance, and methodology findings are closed or intentionally deferred.
4. A 25-50 company trusted-peer pilot has actual reviewed source relationships, or is explicitly rejected as uneconomic.

Until then, the truthful label is **local Commercial Research Beta foundation, preparing for controlled external validation**.
