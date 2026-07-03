# Pilot Runbook

This runbook is the shortest controlled-pilot path for the Stock Research Command Center.

Product principle:

1. Data readiness first.
2. Analysis second.
3. Research decision last.

Research-only boundary: the app does not connect to brokers, place orders, route trades, auto-trade, provide direct buy/sell instructions, fabricate missing inputs, or turn readiness queues into recommendations.

## 1. Setup

Run from the repository root:

```bash
cd "<repo-root>"
pip install -e '.[dev]'
```

Optional research provider dependency:

```bash
pip install -e '.[research]'
```

Optional SEC staging environment variable:

```bash
export SEC_USER_AGENT="Your Name your.email@example.com"
```

If SEC or Yahoo access fails in a session, do not keep retrying the same unavailable path. Use reviewed local rows when present; otherwise mark the affected ticker/lane `still_blocked`, `skipped`, or `excluded` and continue to another executable lane.

## 2. Required Local Data Files

Core tracked/sample data:

- `data/prices.csv`
- `data/fundamentals.csv`
- `data/peers.csv`
- `data/earnings.csv`
- `data/analyst_estimates.csv`
- `data/holdings.csv` as a zero-position sample only

Import/review files:

- `data/imports/fundamentals.csv`
- `data/imports/peers.csv`
- `data/imports/earnings.csv`
- `data/imports/analyst_estimates.csv`
- `data/rejected/*_import_rejected.csv`
- `data/reviewed_batch_proofs.csv`

Do not commit real personal holdings, account exports, private notes, credentials, caches, or broad generated CSV/report churn unless the exact artifact is intentionally reviewed pilot evidence.

## 3. Pilot Entry Check

Run:

```bash
git status --short --branch
make diff-hygiene
make pilot-readiness-check TOP_N=10
make status-check TOP_N=5
make readiness-ops-center
make browser-qa-evidence
make public-wording-check
```

Entry criteria:

- Git branch is synced or intentionally ahead with reviewed commits.
- `make diff-hygiene` shows no unreviewed product files, and any generated CSV/report churn is classified and excluded unless an exact artifact was intentionally reviewed.
- `make pilot-readiness-check TOP_N=10` says `pilot-ready with manual gates` or better.
- Browser QA evidence is ready.
- Public wording check passes.
- Blocked data lanes remain visible.

## 4. Run The Pilot Workflow

Start with the product page:

```bash
make dashboard
```

Open:

```text
http://localhost:8501/?mode=public
```

Visitor path:

```text
Home readiness snapshot -> Stock Selector -> Single-Stock Report -> Data Health lane answer -> Proof History evidence
```

Operator path:

```bash
make project-status
make provider-setup-checklist  # use when project-status says source-proof queues are exhausted
make trusted-data-pilot-candidates TOP_N=10  # only when project-status shows executable company candidates
make trusted-data-pilot-packet TICKER=<ticker>
make stock-report-md TICKER=<ticker>
```

Coverage gate: No broad coverage batch should run from setup alone. Provider setup only makes a source executable; readiness changes still require validate, preview, rejected-row review, source provenance, apply/skip decision, rebuilt readiness, and proof ledger evidence. Do not retry exhausted proof queues until new source-backed rows, keyed provider data, reviewed manual rows, or changed blockers exist.

Use 5 to 10 operating companies for the controlled pilot. ETF/index examples such as QQQ and SMH are useful monitor-context demos, but they are not operating-company DCF targets.

## 5. Refresh Data Safely

Prices:

```bash
make price-history-proof-queue TOP_N=25
make price-refresh-loop DRY_RUN=1
make readiness-snapshot
make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto SLEEP_SECONDS=30
make readiness
make status-check TOP_N=5
make diff-hygiene
```

Run the real capped refresh only after reviewing the dry-run plan.

Universe / source scope:

```bash
make universe-preview-summary
```

Use this compact summary before any full universe row review. It shows source row counts, source warnings, fallback source use, and membership counts without dumping raw rows.

If the compact summary is source-backed and intended:

```bash
make universe-preview
```

Use the full preview only for intentionally reviewed row inspection. To stage reviewed source-driven rows:

```bash
make universe-stage
```

Apply only after reviewing the staged universe rows and source warnings:

```bash
make universe-apply
```

Universe membership is source metadata. It can improve coverage scope, active-vs-master universe routing, and SMH/S&P/Nasdaq source visibility, but it does not unlock fundamentals, share count, DCF, peer valuation, earnings, analyst estimates, or recommendations.

Fundamentals / DCF:

```bash
make dcf-input-proof-queue TOP_N=25
make focus-fundamentals TICKER=<ticker>
make imports-validate IMPORT_TICKERS=<ticker>
make imports-preview IMPORT_TICKERS=<ticker>
```

Apply only after source proof, validation, preview, and rejected-row review:

```bash
make imports-apply IMPORT_TICKERS=<ticker>
make dcf-readiness
make readiness
make stock-report-md TICKER=<ticker>
```

Peers:

```bash
make peer-mapping-queue TOP_N=25
DRY_RUN=1 make peer-mapping-source-review TOP_N=10
make peer-mapping-writeback-guard TICKER=<ticker> PEER_TICKER=<peer> PEER_GROUP=<group> SOURCE=<source> AS_OF_DATE=<yyyy-mm-dd> REVIEWER=<name> REVIEW_DATE=<yyyy-mm-dd>
make imports-validate IMPORT_TICKERS=<ticker>
make imports-preview IMPORT_TICKERS=<ticker>
```

Earnings and analyst estimates:

```bash
make optional-context-worklist TOP_N=25
make optional-context-source-ladder-queue TOP_N=10
make templates
make imports-validate IMPORT_TICKERS=<ticker>
make imports-preview IMPORT_TICKERS=<ticker>
```

Keep optional context locked until trusted local or reviewed provider-assisted rows exist and pass validate, preview, apply, and optional-context readiness.

## 6. Interpret Readiness States

| State | Meaning | Pilot action |
| --- | --- | --- |
| `ready` | Required source-backed inputs exist for that lane. | Review the supported analysis and source context. |
| `partial` | Some useful context exists, but deeper analysis is still gated. | Use only the supported layer; route missing inputs to Data Health. |
| `blocked` | Required source-backed inputs are missing. | Do not interpret withheld analysis; run the lane proof command. |
| `excluded` | The method does not apply, such as company DCF for ETF/index/fund rows. | Use monitor context only. |
| `supported` | A reviewed proof row and rebuilt readiness show the lane changed. | Treat as available within the documented boundary. |
| `candidate_context_only` | Candidate/generated context can route research, but it is not source-backed proof. | Use it for navigation only; keep trusted lanes blocked until source proof exists. |
| `still_blocked` | Review occurred, but the lane remains gated. | Keep the blocker visible and move to the next candidate/lane. |
| `skipped` | Source proof was unavailable or not reviewable. | Do not apply placeholder data; continue elsewhere. |

## 7. Validate Evidence / Provenance

Before calling any lane supported, confirm:

```bash
make readiness-snapshot
make imports-validate
make imports-preview
make readiness
make reviewed-batch-compare LANE=<lane> BATCH_ID=<id> REVIEW_DATE=<yyyy-mm-dd>
DRY_RUN=1 make reviewed-batch-proof-record BATCH_ID=<id> LANE=<lane> REVIEW_DATE=<yyyy-mm-dd> FINAL_OUTCOME=<supported|candidate_context_only|still_blocked|skipped|excluded>
```

Only record a real proof row after source proof, validation, preview, rejected-row review, apply/skip decision, rebuilt readiness, comparison, and generated-artifact review are complete.

## 8. Generate Reports

Use Markdown reports for pilot review:

```bash
make stock-report-md TICKER=NVDA
make stock-report-md TICKER=META
make stock-report-md TICKER=QQQ
make stock-report-md TICKER=MU
make stock-report-md TICKER=CRDO
```

Read in this order:

1. Visitor scan cue.
2. At A Glance.
3. Reader Guide.
4. Evaluation Snapshot.
5. Proof Checklist.
6. Best Review Path.
7. Methodology and detailed sections.

## 9. What To Do When A Stock Is Blocked

1. Do not invent missing inputs.
2. Open the matching proof lane:
   - Fundamentals / DCF: `make dcf-input-proof-queue TOP_N=25`
   - Share count: `make share-count-proof-queue TOP_N=10`
   - Peers: `make peer-mapping-queue TOP_N=25`
   - Optional context: `make optional-context-worklist TOP_N=25`
3. Inspect the ticker packet:
   - `make trusted-data-pilot-packet TICKER=<ticker>`
4. If source proof is available, validate, preview, apply if reviewed, rebuild readiness, regenerate report, and record proof.
5. If source proof is unavailable, record or report `still_blocked` or `skipped` and move to the next executable candidate.

## 10. Pre-Share Checks

Run:

```bash
python3 -m pytest tests -q
make public-check
make pilot-readiness-check TOP_N=10
make browser-qa-evidence
make public-wording-check
make diff-hygiene
git diff --check
```

If `make dashboard-smoke` cannot bind a local socket in a restricted environment, rerun it in a normal local shell before external pilot sharing.

## 11. Known Limitations

- Broad DCF coverage is intentionally limited by trusted fundamentals and share-count proof.
- Peer mapping and peer valuation require reviewed source-backed relationships and mapped-peer inputs.
- Earnings and analyst estimates are locked until trusted local rows exist.
- Optional provider access can fail because of network, DNS, rate limits, credentials, or provider terms.
- Screenshots are product evidence only; they are not data freshness proof.
- The root license is controlled portfolio/demo only, so the repository should not be described as open source or reusable software unless the owner intentionally changes the license.

## 12. Pilot Exit Criteria

Exit the controlled pilot when:

- 5 to 10 selected operating-company packets have outcome states recorded as `supported`, `candidate_context_only`, `still_blocked`, `skipped`, or `excluded`.
- Every supported lane has source proof, validation, preview, rejected-row review, rebuilt readiness, regenerated report, and proof-ledger evidence.
- Operators can complete the workflow from dashboard, runbook, and CLI commands without guessing the next gate.
- Public/release checks pass in the target environment.
- Remaining blockers are external/manual source-coverage items, not product-code or documentation gaps.
