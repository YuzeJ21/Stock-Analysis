# Scheduler Activation Checklist

Use this checklist before turning any refresh command into a recurring job.

The default scheduler posture is read-only monitoring. Automatic application is disabled for every refresh lane. Do not schedule unattended imports, applies, commits, pushes, hosted deployment changes, broker access, or recommendation workflows.

## Refresh Operations Contract

Every scheduled review follows the same read-only lifecycle:

`fetch -> normalize -> validate -> quarantine -> preview -> publish snapshot -> rebuild readiness -> detect changes`

- A job plan records provider order, batch limit, freshness policy, schema identity, attempt history, state, and failure reason before any provider call.
- A failed provider path is not retried again in the same session. Retry caps apply across prior attempts; if every provider is unavailable, already attempted, or capped, record the blocked result and pivot.
- Missing or changed schema identity, missing provenance, duplicate rows, and stale rows are quarantined. Partial batches are withheld from preview, snapshot publication, readiness rebuild, and change detection. A batch that is both partial and invalid remains explicitly `partial_invalid`; neither condition is flattened away.
- A clean batch can become `ready_for_preview`, but it never publishes or applies automatically. Snapshot publication, readiness rebuild, and any later apply remain separate reviewed actions.
- The plan and status commands are descriptive only. They do not fetch, normalize, validate, quarantine, publish, rebuild, detect changes, or write data.

## 1. Start With Status-Only Monitoring

These commands are safe scheduler candidates because they do not refresh, import, apply, stage, commit, push, deploy, or expose secrets:

```bash
make project-status-check
make provider-setup-checklist
make auto-refresh-status SCHEDULE=daily
make auto-refresh-runbook SCHEDULE=daily
make refresh-operations-status SCHEDULE=daily
make refresh-operations-runbook SCHEDULE=daily
make diff-hygiene-summary
```

Use this mode while provider keys, hosted URL setup, trusted peer rows, or optional context rows are still missing.

## 2. Manual Review Preconditions

Do not schedule a mutating refresh or apply path. Automatic application remains disabled even when every gate below is satisfied. These checks define the evidence needed for a separately reviewed, manual action:

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

The default refresh-operations status and runbook never print stage, apply, or publication commands. They stop at source preflight and read-only scope preview. A mutating command belongs in a separate, human-reviewed handoff and is never part of the scheduler plan while `auto_apply=false`.

Provider availability and attempt history are session inputs. An unavailable provider fails closed. A failed provider is skipped for the rest of that session, and the bounded retry cap prevents older failures from being retried indefinitely. The CLI accepts `--available-providers`, `--session-id`, `--retry-cap`, and repeated `--provider-attempt provider:session:outcome` arguments for already-reviewed scheduler state.

## 3. Allowed Recurring Jobs

| Schedule | Allowed now | Boundary |
| --- | --- | --- |
| Daily | Status checks, source preflight, hosted/demo readiness checks, public wording checks, dry-run price plans. | Do not auto-apply imports. |
| Daily after source smoke | Capped price refresh or SEC filing/share-count review for a reviewed scope. | Produce a manual-review handoff only; automatic apply remains disabled. |
| Weekly | Peer candidate review and candidate-context reporting. | Candidate peers stay `candidate_context_only` until source-backed relationships are reviewed. |
| Optional | Earnings and analyst-estimate source ladder checks. | Date-only or target-price-only rows stay `candidate_context_only`. |

## 4. Stop Rules

- Stop if `make project-status-check` says source-proof queues are exhausted.
- Stop if FMP, Alpha Vantage, or Finnhub keys are missing and the selected provider requires a key.
- Stop if the hosted URL is not configured or cannot be opened.
- Stop if validation fails, preview widens unexpectedly, rejected rows are present, provenance is missing, schema identity changes, duplicate/stale rows are present, a batch is partial, or fabricated values are detected.
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

Scheduling is operational monitoring. It does not change the research-only boundary, unlock blocked data, create recommendations, turn the project into a hosted public data platform, or enable automatic data application.
