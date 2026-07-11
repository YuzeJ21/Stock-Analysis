# Scheduler Activation Checklist

Use this checklist before turning any refresh command into a recurring job.

The default scheduler posture is read-only monitoring. Do not schedule unattended imports, applies, commits, pushes, hosted deployment changes, broker access, or recommendation workflows.

## 1. Start With Status-Only Monitoring

These commands are safe scheduler candidates because they do not refresh, import, apply, stage, commit, push, deploy, or expose secrets:

```bash
make project-status-check
make provider-setup-checklist
make auto-refresh-status SCHEDULE=daily
make auto-refresh-runbook SCHEDULE=daily
make diff-hygiene-summary
```

Use this mode while provider keys, hosted URL setup, trusted peer rows, or optional context rows are still missing.

## 2. Activation Preconditions

Do not schedule a mutating refresh or apply path until all of these are true:

| Gate | Required evidence |
| --- | --- |
| Source is executable | `make session-source-preflight` or `make provider-setup-checklist` shows the source path is available. |
| Scope is narrow | A one-ticker provider smoke or reviewed source slice has already passed. |
| Validation passes | `make imports-validate IMPORT_TICKERS=<ticker>` is valid. |
| Preview is intended | `make imports-preview IMPORT_TICKERS=<ticker>` shows the expected ticker and row scope only. |
| Rejected rows are zero | Rejected-row reports are empty or explicitly reviewed. |
| Provenance exists | Source fields identify the provider, filing, document, or reviewed source row. |
| No fabrication | Missing prices, fundamentals, shares, peers, earnings, estimates, valuation inputs, metrics, and recommendations remain missing. |
| Proof is recorded | A reviewed proof row records `auto_supported`, `human_reviewed_supported`, `candidate_context_only`, `still_blocked`, `skipped`, or `excluded`. |

Provider setup alone is never activation proof.
The compact activation shortcut is: source available, narrow scope, validation, preview, zero rejected rows, provenance, no fabrication, and proof recorded.

## 3. Allowed Recurring Jobs

| Schedule | Allowed now | Boundary |
| --- | --- | --- |
| Daily | Status checks, source preflight, hosted/demo readiness checks, public wording checks, dry-run price plans. | Do not auto-apply imports. |
| Daily after source smoke | Capped price refresh or SEC filing/share-count review for a reviewed scope. | Apply only through `make auto-apply-gate` plus validate/preview/proof gates. |
| Weekly | Peer candidate review and candidate-context reporting. | Candidate peers stay `candidate_context_only` until source-backed relationships are reviewed. |
| Optional | Earnings and analyst-estimate source ladder checks. | Date-only or target-price-only rows stay `candidate_context_only`. |

## 4. Stop Rules

- Stop if `make project-status-check` says source-proof queues are exhausted.
- Stop if FMP, Alpha Vantage, or Finnhub keys are missing and the selected provider requires a key.
- Stop if the hosted URL is not configured or cannot be opened.
- Stop if validation fails, preview widens unexpectedly, rejected rows are present, provenance is missing, or fabricated values are detected.
- Stop if generated CSV/JSON/report churn would be staged by default.

When a stop rule triggers, record the outcome as `still_blocked`, `skipped`, `excluded`, or `candidate_context_only`, then pivot to the next executable product or source-review item.

## 5. Verification Before Scheduling

Before adding or changing a recurring job, run:

```bash
make auto-refresh-status SCHEDULE=daily
make auto-refresh-runbook SCHEDULE=daily
make public-wording-check
make public-check
make diff-hygiene-summary
git diff --check
```

Scheduling is operational monitoring. It does not change the research-only boundary, unlock blocked data, create recommendations, or turn the project into a hosted public data platform.
