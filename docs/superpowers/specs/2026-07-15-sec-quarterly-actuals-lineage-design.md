# SEC Quarterly Actuals Lineage Design

## Status

Approved direction: **Option 2, versioned fiscal-quarter lineage plus explicit Q4 earnings-release ingestion**.

This design extends the Earnings Nowcast evidence workflow. It does not make a forecast, create consensus data, apply imports, or change readiness by itself.

## Problem

SEC Companyfacts contains useful Revenue and diluted-EPS facts, but a naive `fy` / `fp` extraction is not safe for quarterly history:

- A 10-Q contains current and prior-year comparative facts carrying the filing's current `fy` and `fp` labels.
- Q2 and Q3 filings contain both single-quarter and cumulative year-to-date facts.
- Companyfacts frequently omits `frame` on older valid quarter facts.
- 10-Q filings do not provide a standalone Q4 result.
- Later filings can restate or split-adjust prior-period EPS.
- Missing Q4 rows make a Q3-to-next-Q1 pair look sequential when it is not.

The five-company pilot must therefore build period identity from source lineage, preserve revisions, reject cumulative facts, and fail closed when quarter continuity or EPS comparability cannot be proven.

## Goals

1. Stage source-backed quarterly Revenue and diluted GAAP EPS actuals for NVDA, AMD, AVGO, MU, and QCOM.
2. Assign each fact to the correct company fiscal quarter without using SEC calendar frames as the fiscal-period label.
3. Preserve source-visible revisions and split-adjusted presentations as append-only evidence.
4. Ingest Q4 only from an explicit result table in an SEC-filed earnings release or equivalent primary filing exhibit.
5. Prevent sequential calculations across a missing fiscal quarter.
6. Produce deterministic validate/preview evidence with no automatic apply path.

## Non-Goals

- Historical or current analyst consensus acquisition.
- Company guidance extraction beyond preserving an explicit source record for a later reviewed lane.
- Numerical Beat/Miss probability.
- Post-earnings price prediction.
- Annual-minus-nine-month Q4 derivation.
- Text-derived or inferred Revenue, EPS, peers, adjustments, or recommendations.
- Broad-universe SEC extraction in the pilot.

## Source Hierarchy

### Q1-Q3

Use SEC Companyfacts records from `10-Q` or `10-Q/A` filings.

Accepted Revenue concepts, in deterministic priority order:

1. `RevenueFromContractWithCustomerExcludingAssessedTax`
2. `Revenues`
3. `SalesRevenueNet`

Accepted EPS concept:

- `EarningsPerShareDiluted`

A candidate metric pair must share the same accession, filing date, start date, end date, fiscal year, fiscal period, and duration class.

### Q4

Use an explicit quarterly Revenue and diluted GAAP EPS result table in a primary SEC-filed exhibit, normally an `8-K` exhibit for domestic issuers or an equivalent filed result document for a foreign issuer.

The source must state the quarter or quarter-ended date and the reported Revenue/EPS values. If the source table, metric basis, or fiscal-period alignment is ambiguous, Q4 remains unavailable. The system never derives Q4 by subtracting nine-month values from annual values.

## Architecture

Add one focused module, `src/earnings_nowcast_sec_actuals.py`, with four boundaries:

1. **Raw fact normalization**
   - Retain taxonomy, concept, unit, value, start, end, filed date, form, accession, SEC `fy` / `fp`, and optional frame.
   - Preserve the raw metadata needed for audit; do not reduce a fact to value and filing year prematurely.

2. **Fiscal-quarter lineage**
   - Identify the current-quarter fact in each 10-Q accession.
   - Establish the canonical `YYYY-QN` identity from that current-quarter filing and period end.
   - Map later comparative presentations back to the canonical period by period end, never by the later filing's `fy` / `fp` alone.

3. **Revision and comparability handling**
   - Emit the first valid presentation as the initial evidence row.
   - Emit a later changed presentation as an append-only revision with `supersedes_source_ref`.
   - Keep Revenue and EPS readiness independent when only one metric changes or remains comparable.
   - Label split adjustment only when the filing explicitly supports that label.

4. **Staging and audit output**
   - Write the existing `quarterly_actuals.csv` schema to an explicitly supplied output directory.
   - Write a generated audit JSON and rejected-row CSV beside it.
   - Create header-only consensus/signals templates so the existing onboarding preview can truthfully report `point_in_time_consensus_missing`.
   - Never write to the canonical data files or call an apply command.

## Q1-Q3 Selection Rules

For every accession and metric concept:

1. Keep only `10-Q` / `10-Q/A` records with numeric values and complete start/end/filed/accession metadata.
2. Calculate duration from start and end dates.
3. A single-quarter candidate must have a duration from 60 through 120 days.
4. Reject duration records outside that range as instant, cumulative, annual, or ambiguous.
5. Within an accession and SEC `fp`, use the latest period end as the current-quarter candidate. This prevents the prior-year comparative quarter from inheriting the current filing's fiscal label.
6. Revenue and EPS must align on accession, start, end, filed date, SEC `fy`, and SEC `fp` before they form a combined row.
7. A non-empty SEC frame is supporting evidence only. Missing frame does not invalidate an otherwise uniquely aligned quarter; a conflicting frame does.
8. If multiple accepted Revenue concepts produce different values for the same lineage, reject the Revenue metric as ambiguous instead of choosing the larger or newer value.
9. If Revenue and EPS cannot be paired, retain only the individually proven metric and keep the other metric empty.

## Fiscal-Period Identity

The canonical period key is anchored by the current-quarter record from its original filing:

- `fiscal_year = current filing fy`
- `fiscal_quarter = current filing fp`
- `period_end = current-quarter end date`

Later filings may present the same `period_end` with different SEC `fy` / `fp` values because it is a comparative period. Those later records inherit the canonical identity already established for that end date.

If two original current-quarter filings assign incompatible fiscal identities to the same period end, the period is rejected and reported as `fiscal_period_conflict`.

## Revision Lineage

Evidence remains point-in-time and append-only:

- `source_ref` identifies the exact SEC accession/document presentation.
- `reported_at` is the filing publication date, not the quarter end.
- `retrieved_at` records collection time.
- A later changed presentation references the prior `source_ref` through `supersedes_source_ref`.
- Preview retains both rows and lets cutoff-aware canonicalization select only evidence published by the forecast cutoff.

No later presentation overwrites an earlier snapshot. A revision published after a historical forecast cutoff is unavailable to that backtest event.

## EPS Split Safety

EPS is separate from Revenue readiness.

1. Original SEC EPS facts are labeled `as_reported` unless the source explicitly states retrospective split adjustment.
2. A source-supported retrospective presentation is labeled `split_adjusted_<effective-date>`.
3. Actual history and consensus must share the same EPS, share, operations, and split-adjustment definitions.
4. If the five-quarter model window crosses incompatible split bases, EPS is withheld while Revenue may remain ready.
5. Provider-assisted split history may route review, but it cannot establish the trusted split basis without a primary source reference.

## Q4 Ingestion

Q4 ingestion is a separate parser boundary because Companyfacts 10-Q duration facts cannot supply it.

The Q4 parser must:

1. Resolve a primary SEC filing and exact earnings-release exhibit.
2. Require an explicit quarter-ended label or an unambiguous fiscal Q4 label.
3. Require explicit Revenue and/or diluted GAAP EPS labels in a structured table.
4. Preserve the filing URL, accession, filed timestamp, period end, metric labels, units, and split note.
5. Reject non-GAAP-only EPS, annual-only totals, guidance tables, prose estimates, and arithmetic derivations.
6. Emit a partial row when only one metric is explicit and source-backed.

Issuer-specific table aliases may be configured for the five-company pilot, but numeric values and periods must still come from the filing itself. The parser must not contain hard-coded company results.

## Quarter Continuity Gate

The model must not treat sorted rows as consecutive by default.

For every forecast metric:

- Require at least five source-backed prior quarters.
- Require fiscal-quarter adjacency across the model window, including Q4-to-next-Q1.
- Require the prior-year target quarter.
- If any intervening quarter is absent, mark the metric `quarter_history_gap` and withhold its forecast.
- Revenue and EPS continuity are evaluated independently.

This gate applies to direct pilot forecasts and walk-forward backtests.

## Command Contract

Add a read-only staging command:

```text
make earnings-nowcast-sec-actuals-stage \
  TICKERS=NVDA,AMD,AVGO,MU,QCOM \
  OUTPUT_DIR=/tmp/stock-nowcast-five-company/sec-actuals \
  AS_OF=<cutoff>
```

The command:

- requires an identifying `SEC_USER_AGENT`;
- uses existing SEC cache/network boundaries;
- accepts a narrow ticker scope;
- performs no import or apply;
- never writes credentials;
- returns nonzero only for command/schema failure, not for a truthfully withheld ticker;
- reports per-ticker accepted rows, rejected rows, missing Q4, metric gaps, and source references.

Follow it with the existing commands:

```text
make earnings-nowcast-validate INPUT_DIR=<output> AS_OF=<cutoff>
make earnings-nowcast-preview INPUT_DIR=<output> AS_OF=<cutoff>
make earnings-nowcast-readiness INPUT_DIR=<output> TICKER=<ticker> AS_OF=<cutoff>
```

Absent historical consensus must continue to yield `point_in_time_consensus_missing` and `ready_for_packet=false`.

## Failure States

The audit output uses explicit states:

- `accepted_explicit_quarter`
- `accepted_revision`
- `accepted_explicit_q4`
- `metric_partial`
- `cumulative_fact_rejected`
- `comparative_period_relabelled`
- `ambiguous_concept`
- `fiscal_period_conflict`
- `quarter_history_gap`
- `split_basis_unverified`
- `q4_source_unavailable`
- `post_cutoff_rejected`
- `source_unavailable`

A withheld state is a valid extraction result and does not stop other tickers.

## Testing Strategy

Tests use local fixtures and mocked SEC responses. No test depends on live SEC availability.

Required cases:

1. Current and prior-year comparative quarters in one 10-Q.
2. Single-quarter and cumulative Q2/Q3 facts in one accession.
3. Missing frame with uniquely aligned 90-day facts.
4. Conflicting frames or Revenue concepts.
5. Revenue-only and EPS-only partial rows.
6. Amended filing and append-only revision lineage.
7. Later split-adjusted comparative EPS with explicit split source.
8. Post-cutoff revision exclusion.
9. Explicit Q4 earnings-release table.
10. Annual-only, guidance, non-GAAP-only, and derived-Q4 rejection.
11. Missing Q4 causing `quarter_history_gap`.
12. Revenue-ready/EPS-withheld split-basis behavior.
13. ETF/fund exclusion remains unchanged.
14. Staging writes only the explicit output directory and never applies data.

After fixture tests pass, run one live, read-only five-company smoke and inspect every accepted/rejected summary. Live output remains generated and unstaged.

## Acceptance Criteria

1. Every accepted Q1-Q3 fact is a uniquely aligned 60-120-day SEC filing fact.
2. Comparative facts never inherit the later filing's fiscal identity.
3. Cumulative values never appear as single-quarter actuals.
4. Q4 is explicit and source-backed or remains unavailable; it is never derived.
5. Historical revisions remain append-only and cutoff-safe.
6. Sequential model inputs are quarter-contiguous.
7. EPS is withheld across an unverified split basis while Revenue remains independently eligible.
8. The five-company staging command produces valid onboarding rows with zero fabricated values.
9. Missing consensus still blocks packet generation and numerical probability.
10. Full tests, public checks, diff hygiene, and staged hygiene pass before commit.

## Rollout

1. Implement raw fact normalization and Q1-Q3 lineage with fixtures.
2. Add quarter-continuity and EPS split-basis gates.
3. Add explicit Q4 filing-exhibit ingestion for the five-company cohort.
4. Run the live read-only staging smoke.
5. Validate and preview the generated evidence.
6. Keep real-company Nowcast output blocked until historical point-in-time consensus is separately sourced and validated.

## Boundaries

- Research-only; no investment advice or trade instruction.
- Candidate data never becomes trusted merely because parsing succeeds.
- Generated extraction artifacts remain outside default staging.
- No broker, account, order, recommendation, or auto-trading behavior.
- Numerical Beat/Miss probability remains unavailable until at least 100 valid events pass calibration gates.
