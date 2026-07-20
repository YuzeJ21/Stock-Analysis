# SEC Quarterly Cash-Generation Pilot Design

## Decision

Add one read-only, in-memory SEC pilot that can assemble and assess a single
company's exact filed quarter for quarterly operating income, cash from
operations, and capital expenditures. The first evidence target is NVIDIA Q1
FY2027, period ended 2026-04-26, accession `0001045810-26-000052`.

The pilot may return `accepted_for_review` through the existing quarterly
adapter acceptance contract. It cannot persist observations, activate product
output, promote readiness, or create or modify CSV, JSON, report,
sample-report, screenshot, timing, or canonical-data artifacts.

## Why This Resolves The Executable Block

The calculation and acceptance contracts already exist, but the checked-in SEC
field scope omits the three required cash-generation components and no real
source adapter supplies them. The SEC Companyfacts API and the issuer's exact
filed 10-Q now provide a narrow real-company evidence path that does not depend
on consensus, a paid provider, a hosted account, Q4 derivation, or synthetic
fixtures.

The NVIDIA filing reports, for the quarter ended 2026-04-26:

- operating income of USD 53.536 billion;
- net cash provided by operating activities of USD 50.344 billion; and
- purchases related to property and equipment and intangible assets of USD
  1.757 billion, displayed in parentheses in the filed cash-flow table.

The filing-table presentation is the explicit evidence that capital
expenditures are a cash outflow. The pilot must not infer the negative sign from
the Companyfacts concept name, taxonomy balance, historical convention, or an
unsigned API magnitude.

## Alternatives Considered

### Exact Companyfacts plus filing-table evidence — selected

Use Companyfacts for structured fact and accession selection, then require the
exact filed table to confirm the capital-expenditure line and its displayed
outflow sign. This preserves the existing reported-sign rule and produces a
durable filing reference.

### Normalize Companyfacts payment concepts automatically — rejected

Turning a positive `PaymentsToAcquireProductiveAssets` magnitude into a
negative outflow based only on concept semantics would be simpler, but it would
weaken the contract that prohibits inferred capex signs.

### Wait for a commercial fundamentals or consensus provider — rejected for
this slice

That path remains valid for broader coverage, but it is externally blocked and
is unnecessary for proving one official-source quarterly adapter path.

## Source And Rights Boundary

The exact source ID remains `sec_companyfacts`. The existing registry already
records approved commercial use for source-backed company facts, derived-data
redistribution only, SEC attribution, fair-access limits, and identified
requests. This slice may extend only that exact record's `supported_fields` to:

- `operating_income`;
- `cash_from_operations`; and
- `capital_expenditures`.

This is a field-scope decision under the existing SEC rights record, not a new
legal or market-data entitlement claim. No other source record changes. The
adapter must pass the explicit registry to the existing acceptance function;
unknown, composite, or scope-incomplete sources continue to fail closed.

Every accepted observation must retain the exact SEC accession and a durable
filing URL. Capital expenditures must additionally retain the exact filed-table
fact or row reference used to prove the displayed sign. The pilot must identify
requests with `SEC_USER_AGENT` and respect SEC fair-access behavior.

## Pilot Interface

Add a focused SEC quarterly pilot module with two pure layers:

1. A parser accepts already-retrieved Companyfacts, submissions, and filing
   HTML payloads, exact company and fiscal-quarter identity, retrieval time,
   and a cutoff. It returns immutable `QuarterlyBusinessObservation` and
   compatible Revenue actual objects or deterministic blockers. The
   submissions payload supplies the exact UTC `acceptanceDateTime`; filing date
   midnight and retrieval time are not substitutes for publication time.
2. A preview function composes the parsed evidence with
   `assess_quarterly_cash_generation_adapter` and returns an immutable result
   containing the pilot identity, source references, extraction blockers, and
   the existing acceptance result.

Network retrieval stays in a thin injectable client boundary. Tests call the
parser with minimal in-memory payloads and never contact the network. A manual
preview may retrieve the exact SEC endpoints and print a concise human-readable
summary to stdout, but it must not write a file or print a persistence-ready
JSON payload.

The preview result always exposes:

- `production_activation=False`;
- `readiness_promotions=()`;
- the exact ticker, CIK, fiscal period, period end, accession, filing date, and
  source URL;
- component facts and the capex-sign evidence state;
- stable blockers; and
- the nested adapter acceptance decision.

## Exact-Quarter Extraction Rules

The parser must require all of the following:

1. One exact accession shared by Revenue, operating income, cash from
   operations, and capital expenditures.
2. One exact start and end date representing the requested three-month fiscal
   quarter. YTD facts cannot be differenced to create a quarter.
3. A filing date and publication timestamp no later than the requested cutoff.
   The publication timestamp must equal the matching accession's SEC
   submissions `acceptanceDateTime` and must be timezone-aware.
4. Supported concepts selected through an explicit ordered concept map rather
   than fuzzy text matching.
5. Matching USD currency, unit scale, period end, accounting basis, and duration
   basis across components and Revenue.
6. An exact filing-table row whose inline XBRL concept, context, and magnitude
   match the selected capex Companyfacts fact and whose displayed presentation
   explicitly marks the value as an outflow.
7. For Q4, an explicit SEC-filed three-month Q4 table. The NVIDIA Q1 pilot does
   not exercise or relax this boundary.

The initial supported concept map is intentionally narrow:

- operating income: `OperatingIncomeLoss`;
- cash from operations:
  `NetCashProvidedByUsedInOperatingActivities`;
- capital expenditures: `PaymentsToAcquireProductiveAssets`, with
  `PaymentsToAcquirePropertyPlantAndEquipment` allowed only when it satisfies
  the same exact-quarter and sign-evidence rules; and
- Revenue: reuse the existing SEC Revenue concept selection and
  `QuarterlyActual` contract.

Multiple conflicting facts, missing context identity, amended filings without
explicit supersession, missing filed-table sign evidence, mismatched
magnitudes, post-cutoff facts, or unsupported concepts block the affected
preview. The parser never guesses a fact or silently chooses among ambiguous
leaves.

## Value And Sign Representation

Values use USD with `unit_scale=1.0`, `duration_basis=three_months`, and one
explicit accounting-basis identifier shared by the compatible components and
Revenue.

Operating income and cash from operations preserve their filed numeric values.
Capital expenditures enter `QuarterlyBusinessObservation` as a negative value
only after the exact filed table proves the matching outflow presentation. Free
cash flow remains the existing formula:

`cash_from_operations + capital_expenditures`

No issuer-defined adjusted FCF, annual-minus-nine-month calculation, taxonomy
balance inference, or post-processing sign convention is permitted.

## Product And Readiness Boundary

This slice establishes real-company source-adapter review evidence, not broad
coverage or product activation. It does not alter Research Desk, Discover,
Company Workbench, or Monitor output. It does not change actuals, consensus,
Revenue, EPS, valuation, catalyst, outcome, backtest, calibration, or hosted
readiness.

Even a successful NVIDIA preview remains `accepted_for_review`. A separate,
explicit activation design and review would be required before Company
Workbench can consume live observations or saved readiness can change.

Real-company Earnings Nowcast remains blocked without permitted point-in-time
consensus. Numerical Beat/Miss probability remains withheld without calibration
evidence.

## Failure And Safety Behavior

- Missing `SEC_USER_AGENT`: block before requesting SEC data.
- SEC error, timeout, or malformed payload: return a stable external-source
  blocker; do not fall back to another provider.
- Missing exact accession or exact-quarter context: block.
- Capex magnitude present without explicit filed-table outflow evidence: block.
- Any Q4 derived from annual or nine-month facts: reject.
- Any post-cutoff filing or retrieval substituted for publication time: reject.
- Any requested persistence or production activation: unsupported by the pilot
  interface.
- Empty or rejected evidence: show blockers and no fabricated values.

## Test-First Coverage

Implementation begins with failing tests for:

1. the exact NVIDIA-shaped Q1 payload producing three compatible component
   observations and a Revenue actual;
2. the matching filed-table parentheses producing a negative capex observation;
3. unsigned Companyfacts capex without table sign evidence blocking;
4. mismatched accession, context, magnitude, period, currency, or concept
   blocking;
5. YTD-only and derived-Q4 candidates blocking;
6. cutoff and amended-filing ambiguity blocking;
7. missing, malformed, mismatched, or post-cutoff submissions acceptance time
   blocking without substituting filing date or retrieval time;
8. missing `SEC_USER_AGENT` and retrieval failures blocking without fallback;
9. exact SEC field scope accepted and incomplete/unknown scope rejected;
10. successful composition returning `accepted_for_review` while keeping
   activation false and readiness promotions empty;
11. no filesystem writes, generated artifacts, broad refreshes, or network calls
    in unit tests.

Focused tests cover the new parser/client boundary, quarterly adapter
acceptance, source rights, SEC provider regressions, and the quarterly business
metric contract.

## Verification And Delivery

After implementation, run focused tests followed by:

- `python3 -m pytest tests -q`;
- `make dashboard-smoke`;
- all applicable Research route render smoke checks;
- `make public-wording-check`;
- `make public-check`;
- commercial-beta and package/release checks required by the repository;
- `make pilot-readiness-check TOP_N=10` without rebuilding readiness;
- `make diff-hygiene-summary`;
- `make pr-range-hygiene-check`;
- `git diff --check`; and
- `make staged-hygiene-check` after exact staging.

Stage only intentional source, test, config, methodology, roadmap, continuation
prompt, and design files. Keep draft PR #113 draft, push only to
`codex/personal-research-mode-mvp`, and do not merge or deploy.

## Completion Boundary

The slice is complete when the exact NVIDIA Q1 evidence can pass a read-only
preview from official SEC payloads, all failure paths remain fail closed, the
field-scope review is explicit, all required verification passes, and no
generated artifact is created or staged.

This does not complete broad source coverage, readiness activation, consensus,
calibration, hosted validation, reviewer validation, or market validation.
