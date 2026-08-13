# Proof-Readiness Reconciliation Design

## Problem

The reviewed batch proof ledger is append-only historical evidence, while the readiness reports describe the current saved product state. Those two sources can diverge legitimately when generated canonical data is retained only locally, later replaced, or excluded from a commit. The product currently shows latest proof outcomes without explicitly reconciling them to current readiness, so a historical `supported`, `auto_supported`, or `human_reviewed_supported` outcome can be mistaken for current support.

The current repository demonstrates the risk directly. Batch `RB-20260626-FUND-SOURCE-LADDER-002` says ARCT fundamentals were applied and auto-supported, but ARCT is absent from both the committed canonical fundamentals file at that proof commit and the current canonical fundamentals file. Current readiness correctly keeps ARCT blocked. A read-only audit of valid current-universe tickers found 3,486 ticker/lane pairs whose latest mapped proof outcome is supporting while the corresponding current readiness state is blocked: 2,615 fundamentals, 862 share count, 6 price coverage, and 3 peers. These counts are audit findings from the current local snapshot, not permanent product constants.

This is a proof-interpretation defect, not permission to restore old data, rewrite history, or promote readiness.

## Decision

Add one pure proof-readiness reconciliation contract that compares the latest applicable proof outcome for each valid ticker and lane with the corresponding current saved readiness state.

The contract will expose these explicit states:

- `current_supported_with_matching_proof`: current readiness is true and the latest applicable proof outcome is explicitly supporting;
- `historical_supported_currently_blocked`: the latest applicable proof outcome is explicitly supporting but current readiness is false;
- `current_ready_proof_not_supporting`: current readiness is true but the latest applicable proof is absent, non-supporting, malformed, or unknown;
- `currently_blocked_with_non_supporting_history`: current readiness is false and the latest applicable proof is explicitly non-supporting;
- `no_proof_record`: the ticker/lane has a current readiness state but no applicable proof row;
- `not_applicable`: no authoritative current readiness mapping exists for the lane or ticker.

Only literal `supported`, `auto_supported`, and `human_reviewed_supported` outcomes count as supporting historical proof. Unknown outcomes fail closed. A supporting historical outcome never changes current readiness, source rights, field scope, provenance, or product availability.

## Alternatives Considered

### Reconcile only the DCF source-review queue

Rejected as too narrow. The current audit found the same interpretation risk in fundamentals, share count, price coverage, and peer lanes, and Proof History is the shared evidence surface.

### Rewrite or delete contradictory proof rows

Rejected because the ledger is append-only audit history. Historical claims must remain inspectable even when later evidence contradicts or supersedes them.

### Treat every historical supporting outcome as current support

Rejected because generated data can remain local or disappear from the committed canonical state. Current saved readiness remains authoritative for current availability.

### Shared read-only reconciliation contract

Selected because one deterministic comparison can protect CLI and Advanced Proof History surfaces without mutating either input source.

## Architecture

Create `src/proof_readiness_reconciliation.py` as a focused, read-only module.

It will:

1. load or accept the reviewed proof ledger, ticker readiness report, DCF readiness report, and peer readiness report;
2. normalize column names without changing input frames;
3. accept only ticker tokens that exist in the current readiness universe, preventing descriptive ledger text from becoming a fabricated ticker;
4. map each supported proof lane to exactly one authoritative current state;
5. choose the latest applicable proof deterministically by valid review date and append order;
6. emit immutable reconciliation rows and aggregate counts;
7. render a bounded human-readable table and optional JSON without writing files.

Lane mappings remain explicit:

| Proof lane | Authoritative current field |
| --- | --- |
| `fundamentals` | ticker readiness `fundamentals_ready` |
| `fundamentals_dcf` | ticker readiness `dcf_ready` |
| `share_count` | DCF readiness `has_shares_outstanding` |
| `prices`, `price`, `price_coverage`, `price_history` | ticker readiness `price_ready` |
| `peers`, `peer_mapping` | ticker readiness `peer_ready` |
| `peer_valuation_inputs` | peer readiness `peer_valuation_ready` |

Every other lane is `not_applicable`; it is never coerced into one of these states. Earnings, analyst estimates, consensus, Revenue, EPS, valuation history, catalysts, outcomes, backtesting, and calibration remain independent.

Add `make proof-readiness-reconciliation TOP_N=20` as the read-only operator entry point. Optional `TICKERS=<comma-separated-tickers>` filtering must narrow output only and must never change the aggregate or underlying data.

Advanced Proof History will consume the pure reconciliation summary. It will show the answer before ledger detail:

- whether historical support conflicts with current readiness;
- bounded counts by lane;
- the selected ticker's conflicts when a ticker is present;
- the exact read-only command for further inspection;
- a boundary stating that reconciliation neither restores data nor unlocks a lane.

The four primary Personal Research pages remain unchanged. Proof reconciliation stays under Advanced Evidence and cannot become a competing research recommendation or next task.

## Data Flow

```text
reviewed_batch_proofs.csv ----+
ticker_readiness_report.csv --+--> pure reconciliation --> CLI / Advanced Proof History
dcf_readiness_report.csv ------+
peer_readiness_report.csv -----+
```

No output flows back into canonical data, readiness reports, the proof ledger, research decisions, forecasts, or UI routing.

## Error Handling

- Missing or empty proof ledger returns `no_proof_record` for mapped current states.
- Missing required readiness input fails closed with an explicit unavailable-input summary; it does not infer false readiness.
- Malformed review dates cannot outrank valid dated rows. If only malformed dated rows exist, the latest append-order row remains historical evidence but its reconciliation is non-supporting and visibly malformed.
- Descriptive strings, dashes, counts, and unknown tokens in a ledger `tickers` field are ignored unless they exactly match a current-universe ticker.
- Duplicate ticker tokens in one proof row are deduplicated.
- Unknown lanes and outcomes remain visible as `not_applicable` or non-supporting evidence; prefix matching is forbidden.
- Boolean parsing accepts only explicit true/false representations used by current reports. Missing or malformed values produce an unavailable current state, never `true`.

## Testing

Use strict red-green development.

1. Prove a historical supporting fundamentals row plus current blocked fundamentals yields `historical_supported_currently_blocked`.
2. Prove current readiness plus matching supporting proof yields `current_supported_with_matching_proof`.
3. Prove current readiness with no or non-supporting proof yields `current_ready_proof_not_supporting`.
4. Prove a current blocked lane with a later `still_blocked` outcome does not reuse an earlier supporting outcome.
5. Prove fundamentals, DCF, share count, price, peer mapping, and peer valuation inputs use independent authoritative fields.
6. Prove unknown lanes, outcomes, malformed dates, malformed booleans, duplicate tickers, and descriptive ticker text fail closed.
7. Prove ticker filtering and `TOP_N` only bound presentation.
8. Prove the CLI writes no files and prints the research-only and non-promotion boundaries.
9. Prove Advanced Proof History shows aggregate and selected-ticker conflicts before raw ledger detail while primary research routes remain unchanged.
10. Run focused tests, the full repository suite, dashboard and research render smoke, public wording/public checks, commercial-beta and release checks, pilot readiness, diff hygiene, whitespace checks, and staged hygiene.

## Documentation

Update:

- `ROADMAP.md` with the verified reconciliation behavior and its evidence limits;
- `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md` so future runs inspect reconciliation before reusing supporting proof;
- relevant Proof History/operator documentation with the read-only command and state definitions.

Historical audit counts must be described as current-snapshot findings, never durable coverage totals.

## Acceptance Criteria

1. Current readiness remains the only authority for current lane availability.
2. Historical supporting proof that conflicts with current readiness is labeled `historical_supported_currently_blocked`.
3. Current readiness without matching supporting proof is not silently described as proof-backed.
4. Lane mappings remain explicit and independent.
5. Advanced Proof History exposes the conflict before raw proof detail and keeps it under Advanced Evidence.
6. No proof row, canonical data row, readiness row, research output, or generated artifact is written or modified by reconciliation.
7. The existing 18 generated readiness files remain unstaged and excluded.
8. Focused and complete verification pass.
9. Only exact intentional code, test, Makefile, and documentation files are staged.
10. PR #113 remains open and draft.

## Non-Goals

- No restoration of omitted canonical data.
- No mutation, deletion, correction, or supersession of historical proof rows.
- No source fetch, provider probe, import, preview, apply, readiness rebuild, or generated report.
- No inference of source rights, field scope, provenance, payload truth, freshness, reviewer intent, or current support from a proof label.
- No broad provider, coverage, consensus, peer-sourcing, or calibration loop.
- No investment advice, ranking, recommendation, broker integration, order routing, or auto-trading.
