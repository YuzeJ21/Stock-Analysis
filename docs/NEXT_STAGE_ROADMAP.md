# Next Stage Roadmap

This roadmap is the current operator handoff for the Stock Research Command Center. It is research-only, readiness-first, and does not refresh data, apply imports, stage files, deploy hosting, or expose provider keys.

## Current Product State

The project is ready for a controlled GitHub/LinkedIn portfolio demo with manual gates. It is not yet a fully hosted public data platform.

Use the public workflow first:

```text
Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History
```

Current local evidence from `make project-status` and `make pilot-readiness-check TOP_N=10`:

| Area | Current state | What it means |
| --- | --- | --- |
| GitHub / public share | Ready for manual share when branch is synced | Use the GitHub link and curated screenshot; do not claim a hosted app. |
| Public workflow | Pilot-ready with manual gates | The public pages, screenshots, wording gates, and browser evidence are the share package. |
| Price rows | `3541 / 3541` | Price rows exist for the tracked universe. |
| Momentum-ready | `3538 / 3541` | A few names remain source-limited on short history depth. |
| Fundamentals / inputs | `2810 / 3541` | Strong but not complete; missing trusted source rows remain visible. |
| DCF-ready operating companies | `2693 / 3541` | Standalone DCF review is strong where required inputs exist. |
| Share-count ready | `3450 / 3541` | Most share-count blockers are resolved; remaining blockers are source-gated. |
| Peer-ready | `29 / 3541` | This is the largest analysis-depth gap. |
| Earnings / estimates | Locked by design | Keep locked until trusted provider or reviewed manual rows exist. |

Screenshots are product evidence only. They are not data freshness proof and do not unlock blocked inputs.

## Priority Order

1. **Keep GitHub synced**
   - Run `git status --short --branch --untracked-files=no`.
   - Push only reviewed commits.
   - Keep generated CSV/report/sample-report churn excluded unless an exact artifact is reviewed evidence.

2. **Run a controlled reviewer pilot**
   - Use `make pilot-review-feedback`.
   - Use `docs/PILOT_REVIEW_FEEDBACK_TEMPLATE.md`.
   - Keep the working feedback log outside Git until it is anonymized and intentionally reviewed.
   - Measure workflow clarity only: where reviewers start, what they think is usable, what is blocked, and what they expect next.

3. **Deploy a hosted demo only after external setup**
   - Run `make hosted-demo-readiness`.
   - Follow `docs/HOSTED_DEMO_DEPLOYMENT.md`.
   - Do not claim hosted availability until a public URL opens and the five-page workflow is verified.

4. **Activate one keyed fallback provider, FMP first**
   - Configure `FMP_API_KEY` outside Git.
   - Run one reviewed smoke only: `make fmp-smoke TICKER=<ticker>`.
   - Continue only through validate and preview unless validation passes, preview scope is narrow, rejected rows are zero, and source provenance exists.
   - Do not run broad provider batches from setup alone.

5. **Run a 25-50 company trusted-peer pilot**
   - Use `docs/TRUSTED_PEER_PILOT_SOURCE_TEMPLATE.csv` outside Git as a collection aid.
   - Keep generated/candidate peers as `candidate_context_only`.
   - Promote only source-backed relationships that pass guard, validation, preview, rebuilt readiness, and proof recording.

6. **Open optional earnings / estimates only with trusted fields**
   - Use `make optional-context-source-ladder-queue TOP_N=10`.
   - Date-only or target-only rows stay `candidate_context_only`.
   - Optional lanes remain locked until supported fields, period/as-of metadata, provenance, validation, preview, apply, and readiness rebuild pass.

7. **Add scheduling only after provider proof**
   - Use `make scheduler-activation-checklist`.
   - Start with read-only monitoring.
   - Keep auto-apply gated by validation, intended preview scope, zero rejected rows, provenance, no-fabrication checks, rebuilt readiness, and proof history.

## Do Not Repeat

Do not reopen broad fundamentals, share-count, or price-history loops just because a source is reachable. Current source-proof queues are already reviewed or non-actionable unless one of these changes:

- a keyed provider is configured outside Git,
- reviewed manual source rows are added,
- a provider starts returning new source-backed rows,
- a hosted/manual reviewer finds a reproducible product issue,
- `make project-status-check` shows a new executable company candidate.

If none of those changed, use `make project-status-check` and `make provider-setup-checklist`, then move to the next product/share item.

## Safe Command Ladder

```bash
git status --short --branch --untracked-files=no
make diff-hygiene-summary
make project-status-check
make pilot-readiness-check TOP_N=10
make next-stage
```

For public/share validation:

```bash
make public-check
make browser-qa-evidence
make linkedin-share-check
```

For provider activation:

```bash
make provider-setup-checklist
make fmp-smoke TICKER=<ticker>
make imports-validate IMPORT_TICKERS=<ticker>
make imports-preview IMPORT_TICKERS=<ticker>
```

Stop before `make imports-apply` unless the source-backed gate passes.

## Completion Boundary

The product can be shared now as a controlled portfolio/demo. The next milestone is not "all tickers fully analyzed." The next milestone is:

- reviewers can understand the workflow without operator coaching,
- a hosted URL exists and is verified, or GitHub remains the public link,
- one keyed provider smoke proves whether fallback coverage can expand,
- trusted peer rows unlock a meaningful 25-50 company relative-analysis pilot,
- optional context remains locked until supported source rows exist.

Anything missing stays visible as `partial`, `blocked`, `still_blocked`, `candidate_context_only`, `skipped`, or `excluded`.
